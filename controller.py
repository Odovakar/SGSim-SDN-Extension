import logging
import time
import threading
from collections import defaultdict, deque

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, tcp


class Controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    IEC104_PORT = 2404

    # Max bytes to capture from mirrored IEC-104 packets (non-gateway switches).
    # Gateway switches use OFPCML_NO_BUFFER (full packet to controller).
    MIRROR_MAX_LEN = 256

    # RTU-side gateway switches: RTU IP → dpid.
    # Only these switches act as inline gatekeepers for HMI→RTU traffic.
    FLOW_MONITOR = {
        "1.1.1.1": 1,   # DSS1GW
        "1.1.2.1": 2,   # DSS2GW
        "1.1.3.1": 18,  # DSS3GW
        "1.1.4.1": 20,  # DSS4GW
    }

    # ------------------------------------------------------------------
    # Command detection thresholds
    # ------------------------------------------------------------------
    CMD_WINDOW_SEC = 8.0              # keep tight window for fast attacks
    BLOCK_DURATION_SEC = 120.0        # longer block to cover pivots
    STAGE1_DOUBLE_THRESHOLD = 2
    STAGE1_CONTROL_THRESHOLD = 2
    # Block after 3 sequential double commands toward a single RTU (baseline)
    SUSTAINED_SINGLE_RTU_THRESHOLD = 3

    # Advisory rate limit (no enforcement action)
    PPM_WINDOW_SEC = 10.0
    PPM_THRESHOLD = 180

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        self._configure_timestamped_logging()

        self.mac_to_port = {}
        self.datapaths = {}

        self.flow_timestamps = defaultdict(list)
        self.alerted_flows = set()

        # command_events[src_ip] = deque of event dicts
        self.command_events = defaultdict(deque)

        # src_ip → detection stage: 0=normal, 1=suspicious, 2=blocked
        self.src_stage = defaultdict(int)

        # blocked_until[src_ip] = expiry timestamp (float)
        self.blocked_until = {}

        # Persistent strike counter that survives block expiry
        self.src_strikes = defaultdict(int)

        sweep = threading.Thread(target=self._background_sweep, daemon=True)
        sweep.start()

    # ------------------------------------------------------------------
    # Logging setup
    # ------------------------------------------------------------------
    def _configure_timestamped_logging(self):
        fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
        for handler in self.logger.handlers:
            handler.setFormatter(formatter)

        self.logger.propagate = True
        self.logger.setLevel(logging.DEBUG)

    # ------------------------------------------------------------------
    # Generic flow helper
    # ------------------------------------------------------------------
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        kwargs = dict(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        if buffer_id is not None:
            kwargs["buffer_id"] = buffer_id

        datapath.send_msg(parser.OFPFlowMod(**kwargs))

    # ------------------------------------------------------------------
    # Install IEC-104 flows on a switch
    # ------------------------------------------------------------------
    def add_gateway_iec104_flows(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match_to_rtu = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ip_proto=6,
            tcp_dst=self.IEC104_PORT,
        )
        match_from_rtu = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IP,
            ip_proto=6,
            tcp_src=self.IEC104_PORT,
        )

        # RTU→HMI responses are always mirror+forward — no blocking needed.
        mirror_fwd = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, self.MIRROR_MAX_LEN),
            parser.OFPActionOutput(ofproto.OFPP_NORMAL),
        ]

        if datapath.id in set(self.FLOW_MONITOR.values()):
            # Gateway switch: controller is the sole forwarder for HMI→RTU.
            to_rtu = [parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
            )]
        else:
            to_rtu = mirror_fwd

        self.add_flow(datapath, priority=10, match=match_to_rtu, actions=to_rtu)
        self.add_flow(datapath, priority=10, match=match_from_rtu, actions=mirror_fwd)

        self.logger.info(
            "IEC-104 flows installed on dpid=%s (gateway=%s)",
            datapath.id, datapath.id in set(self.FLOW_MONITOR.values())
        )

    # ------------------------------------------------------------------
    # Switch ready
    # ------------------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Table-miss: send everything to controller (lowest priority)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        self.datapaths[datapath.id] = datapath
        self.add_gateway_iec104_flows(datapath)

        self.logger.info("Switch ready: dpid=%s", datapath.id)

    # ------------------------------------------------------------------
    # Advisory PPM helper
    # ------------------------------------------------------------------
    def record_and_count_ppm(self, flow_key):
        now = time.time()
        timestamps = self.flow_timestamps[flow_key]
        timestamps.append(now)
        cutoff = now - self.PPM_WINDOW_SEC
        self.flow_timestamps[flow_key] = [t for t in timestamps if t >= cutoff]
        return len(self.flow_timestamps[flow_key]) * 6

    # ------------------------------------------------------------------
    # IEC-104 parsing helpers
    # ------------------------------------------------------------------
    def _extract_tcp_payload(self, raw_data, ip_pkt, tcp_pkt):
        start = 14 + ip_pkt.header_length * 4 + tcp_pkt.offset * 4
        if start >= len(raw_data):
            return b""
        return bytes(raw_data[start:])

    def _parse_iec104(self, payload):
        """Parse an IEC-104 I-format APDU.  Returns a dict or None."""
        if len(payload) < 16 or payload[0] != 0x68:
            return None
        if len(payload) < payload[1] + 2:
            return None
        # Bit 0 of ctrl0 set → S/U format (no ASDU)
        if payload[2] & 0x01:
            return None

        type_id = payload[6]
        cot = (payload[8] | (payload[9] << 8)) & 0x3F
        negative = bool(payload[8] & 0x40)
        ca = payload[10] | (payload[11] << 8)
        ioa = payload[12] | (payload[13] << 8) | (payload[14] << 16)
        cmd = payload[15] if len(payload) > 15 else None

        return {"type_id": type_id, "cot": cot, "negative": negative,
                "ca": ca, "ioa": ioa, "cmd": cmd}

    def _is_control_type(self, type_id):
        return type_id in (45, 46)

    def _is_double_command(self, type_id):
        return type_id == 46

    def _command_text(self, type_id, cmd):
        if type_id == 45:
            if cmd is None:
                return "single_cmd"
            return "single_cmd=ON" if (cmd & 0x01) else "single_cmd=OFF"
        if type_id == 46:
            if cmd is None:
                return "double_cmd"
            dco = cmd & 0x03
            if dco == 1:
                return "double_cmd=OPEN"
            if dco == 2:
                return "double_cmd=CLOSE"
            return "double_cmd=raw(%d)" % dco
        return "type_%d" % type_id

    # ------------------------------------------------------------------
    # Command state tracking
    # ------------------------------------------------------------------
    def _prune_command_state(self, src_ip, now):
        dq = self.command_events[src_ip]
        cutoff = now - self.CMD_WINDOW_SEC
        while dq and dq[0]["ts"] < cutoff:
            dq.popleft()
        if not dq and self.src_stage[src_ip] == 1:
            self.src_stage[src_ip] = 0
            self.logger.info("[CLEAR] src=%s suspicious window expired", src_ip)

    def _record_command_event(self, src_ip, dst_ip, type_id, cot, ioa, cmd):
        now = time.time()
        self.command_events[src_ip].append(
            {"ts": now, "dst_ip": dst_ip, "type_id": type_id,
             "cot": cot, "ioa": ioa, "cmd": cmd}
        )
        self._prune_command_state(src_ip, now)

    def _evaluate_command_state(self, src_ip):
        now = time.time()
        self._prune_command_state(src_ip, now)

        events = list(self.command_events[src_ip])
        if not events:
            return

        controls = [e for e in events
                    if self._is_control_type(e["type_id"]) and e["cot"] == 6]
        doubles = [e for e in controls if self._is_double_command(e["type_id"])]

        control_count = len(controls)
        double_count = len(doubles)
        distinct_rtus = len({e["dst_ip"] for e in controls})
        distinct_ioas = len({e["ioa"] for e in controls if e["ioa"] is not None})

        self.logger.warning(
            "[CMD-STATE] src=%s stage=%d controls=%d doubles=%d rtus=%d ioas=%d window=%.1fs",
            src_ip, self.src_stage[src_ip],
            control_count, double_count, distinct_rtus, distinct_ioas, self.CMD_WINDOW_SEC
        )

        stage = self.src_stage[src_ip]

        if stage == 0:
            if (double_count >= self.STAGE1_DOUBLE_THRESHOLD or
                    control_count >= self.STAGE1_CONTROL_THRESHOLD):
                self.src_stage[src_ip] = 1
                self.logger.warning(
                    "[SUSPICIOUS] src=%s controls=%d doubles=%d rtus=%d ioas=%d in %.1fs",
                    src_ip, control_count, double_count,
                    distinct_rtus, distinct_ioas, self.CMD_WINDOW_SEC
                )
                stage = 1

        if stage == 1:
            # Repeat offenders re-block faster (strike_factor lowers threshold)
            strike_factor = max(1, self.src_strikes[src_ip])
            sustained_single = double_count >= max(
                1, self.SUSTAINED_SINGLE_RTU_THRESHOLD // strike_factor
            )
            multi_rtu = double_count >= 2 and distinct_rtus >= 2

            if multi_rtu or sustained_single:
                reason = "multi-RTU pivot" if multi_rtu else "sustained single-RTU double-command abuse"
                self.logger.warning(
                    "[CONFIRMED] src=%s IEC-104 misuse: doubles=%d rtus=%d reason=%s in %.1fs",
                    src_ip, double_count, distinct_rtus, reason, self.CMD_WINDOW_SEC
                )
                self._activate_inline_block(src_ip, reason)

    # ------------------------------------------------------------------
    # Inline block management
    # ------------------------------------------------------------------
    def _is_currently_blocked(self, src_ip):
        expiry = self.blocked_until.get(src_ip)
        return expiry is not None and time.time() < expiry

    def _activate_inline_block(self, src_ip, reason):
        """Record a block for src_ip lasting BLOCK_DURATION_SEC seconds."""
        expiry = (time.time() + self.BLOCK_DURATION_SEC
                  if self.BLOCK_DURATION_SEC != float("inf")
                  else float("inf"))
        self.blocked_until[src_ip] = max(self.blocked_until.get(src_ip, 0), expiry)
        self.src_stage[src_ip] = 2
        self.src_strikes[src_ip] += 1
        self.logger.warning(
            "[INLINE-BLOCK] src=%s reason=%s block_duration=%s",
            src_ip, reason,
            "permanent" if expiry == float("inf") else f"{self.BLOCK_DURATION_SEC:.0f}s"
        )

    # ------------------------------------------------------------------
    # Explicit PacketOut forwarding helper
    # ------------------------------------------------------------------
    def _forward_packet(self, datapath, in_port, data):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=[parser.OFPActionOutput(ofproto.OFPP_NORMAL)],
            data=data,
        )
        datapath.send_msg(out)

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------
    def _background_sweep(self):
        while True:
            time.sleep(2)
            now = time.time()

            # Expire blocks and reset stage
            for src_ip in list(self.blocked_until.keys()):
                if self.blocked_until[src_ip] <= now:
                    del self.blocked_until[src_ip]
                    self.src_stage[src_ip] = 0
                    self.logger.info("[INLINE-EXPIRED] src=%s block expired", src_ip)

            # Prune PPM tracking
            ppm_cutoff = now - self.PPM_WINDOW_SEC
            for flow_key in list(self.alerted_flows):
                active = [t for t in self.flow_timestamps.get(flow_key, [])
                          if t >= ppm_cutoff]
                if not active:
                    self.alerted_flows.discard(flow_key)

            # Prune command state for inactive sources; keep history for strikers
            for src_ip in list(self.command_events.keys()):
                self._prune_command_state(src_ip, now)
                if (not self.command_events[src_ip]
                        and self.src_stage[src_ip] == 0
                        and self.src_strikes[src_ip] == 0):
                    del self.command_events[src_ip]

    # ------------------------------------------------------------------
    # Main PacketIn handler
    # ------------------------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth_list = pkt.get_protocols(ethernet.ethernet)
        if not eth_list:
            return

        eth = eth_list[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        src_mac = eth.src
        dst_mac = eth.dst
        self.mac_to_port[dpid][src_mac] = in_port

        # ------------------------------------------------------------------
        # IEC-104 inspection path
        # ------------------------------------------------------------------
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            tcp_pkt = pkt.get_protocol(tcp.tcp)

            if ip_pkt and tcp_pkt and ip_pkt.proto == 6:
                is_to_rtu   = tcp_pkt.dst_port == self.IEC104_PORT
                is_from_rtu = tcp_pkt.src_port == self.IEC104_PORT

                if is_to_rtu or is_from_rtu:
                    # Only process on the correct gateway for this RTU.
                    if is_to_rtu   and self.FLOW_MONITOR.get(ip_pkt.dst) != dpid:
                        return
                    if is_from_rtu and self.FLOW_MONITOR.get(ip_pkt.src) != dpid:
                        return

                    self.logger.debug(
                        "[IEC104-SEEN] dpid=%s %s:%s -> %s:%s flags=0x%02x len=%d",
                        dpid, ip_pkt.src, tcp_pkt.src_port,
                        ip_pkt.dst, tcp_pkt.dst_port, tcp_pkt.bits, len(msg.data)
                    )

                    payload = self._extract_tcp_payload(msg.data, ip_pkt, tcp_pkt)
                    iec = self._parse_iec104(payload)

                    # ==================================================
                    # HMI → RTU  (controller is the sole forwarder)
                    # ==================================================
                    if is_to_rtu:
                        # Advisory rate check
                        flow_key = (ip_pkt.src, tcp_pkt.src_port,
                                    ip_pkt.dst, tcp_pkt.dst_port)
                        ppm = self.record_and_count_ppm(flow_key)
                        if ppm > self.PPM_THRESHOLD and flow_key not in self.alerted_flows:
                            self.alerted_flows.add(flow_key)
                            self.logger.warning(
                                "[RATE-ADVISORY] dpid=%s %s:%s -> %s:%s ppm=%d threshold=%d",
                                dpid, ip_pkt.src, tcp_pkt.src_port,
                                ip_pkt.dst, tcp_pkt.dst_port, ppm, self.PPM_THRESHOLD
                            )

                        is_control_request = (
                            iec is not None and
                            iec["cot"] == 6 and
                            self._is_control_type(iec["type_id"])
                        )

                        # ── Step 1: already-blocked source ──────────────────
                        if self._is_currently_blocked(ip_pkt.src):
                            if is_control_request:
                                cmd_txt = self._command_text(iec["type_id"], iec["cmd"])
                                self.logger.warning(
                                    "[INLINE-DROP] src=%s dst=%s type=%d cot=%d ioa=%s cmd=%s",
                                    ip_pkt.src, ip_pkt.dst,
                                    iec["type_id"], iec["cot"], iec["ioa"], cmd_txt
                                )
                                return  # DROP

                            # Non-command from blocked source → keep TCP alive
                            self.logger.debug(
                                "[INLINE-FWD] src=%s dst=%s payload_len=%d",
                                ip_pkt.src, ip_pkt.dst, len(payload)
                            )
                            self._forward_packet(datapath, in_port, msg.data)
                            return

                        # ── Step 2: record and evaluate new command events ───
                        if is_control_request:
                            cmd_txt = self._command_text(iec["type_id"], iec["cmd"])
                            self.logger.warning(
                                "[IEC104-CMD] src=%s dst=%s type=%d cot=%d ioa=%s cmd=%s",
                                ip_pkt.src, ip_pkt.dst,
                                iec["type_id"], iec["cot"], iec["ioa"], cmd_txt
                            )
                            self._record_command_event(
                                src_ip=ip_pkt.src, dst_ip=ip_pkt.dst,
                                type_id=iec["type_id"], cot=iec["cot"],
                                ioa=iec["ioa"], cmd=iec["cmd"],
                            )
                            self._evaluate_command_state(ip_pkt.src)

                            # Drop the triggering packet if block just activated
                            if self._is_currently_blocked(ip_pkt.src):
                                self.logger.warning(
                                    "[INLINE-DROP] src=%s dst=%s type=%d cot=%d ioa=%s cmd=%s"
                                    " (triggering packet blocked)",
                                    ip_pkt.src, ip_pkt.dst,
                                    iec["type_id"], iec["cot"], iec["ioa"], cmd_txt
                                )
                                return  # DROP

                        # ── Step 3: forward benign / below-threshold traffic ─
                        self._forward_packet(datapath, in_port, msg.data)
                        return

                    # ==================================================
                    # RTU → HMI  (already forwarded by mirror rule, observe only)
                    # ==================================================
                    if is_from_rtu:
                        if (iec is not None and iec["cot"] == 7 and
                                self._is_control_type(iec["type_id"])):
                            cmd_txt = self._command_text(iec["type_id"], iec["cmd"])
                            result = "REJECTED" if iec["negative"] else "CONFIRMED"
                            self.logger.warning(
                                "[IEC104-ACT_CON] rtu=%s dst=%s type=%d ioa=%s result=%s cmd=%s",
                                ip_pkt.src, ip_pkt.dst,
                                iec["type_id"], iec["ioa"], result, cmd_txt
                            )
                        return

        # ------------------------------------------------------------------
        # Basic L2 learning switch for all other traffic
        # ------------------------------------------------------------------
        if dst_mac in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=src_mac)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)