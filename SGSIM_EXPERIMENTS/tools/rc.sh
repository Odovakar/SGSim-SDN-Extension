#!/usr/bin/env bash
# run_capture.sh — parallel tshark captures + OVS snapshots + run_meta.json

set -euo pipefail

COND="${1:-}"
RUNNO="${2:-}"
DUR="${3:-}"

if [[ -z "$COND" || -z "$RUNNO" || -z "$DUR" ]]; then
  echo "Usage: sudo $0 <condition> <run_number> <duration_seconds>"
  exit 1
fi

if ! [[ "$RUNNO" =~ ^[0-9]+$ ]]; then
  echo "ERROR: run_number must be an integer (got: $RUNNO)"
  exit 1
fi

if ! [[ "$DUR" =~ ^[0-9]+$ ]]; then
  echo "ERROR: duration_seconds must be an integer (got: $DUR)"
  exit 1
fi

RUNNO_PAD="$(printf "%03d" "$RUNNO")"
RUN_ID_BASE="${COND}_${RUNNO_PAD}"
TS_ISO="$(date -Iseconds)"
TS_TAG="$(date +%Y%m%d_%H%M%S)"

ROOT_TMP="/tmp/SGSIM_EXPERIMENTS_TMP"
OUTDIR="${ROOT_TMP}/${RUN_ID_BASE}"
PCAPDIR="${OUTDIR}/pcaps"
OVSDIR="${OUTDIR}/ovs"
LOGDIR="${OUTDIR}/logs"

DEST_ROOT="/home/ubuntu/SGS/SGSIM_EXPERIMENTS/runs"

ATTACK_TYPE="${ATTACK_TYPE:-$COND}"
ATTACKER_PLACEMENT="${ATTACKER_PLACEMENT:-}"
RULESET_FILE="${RULESET_FILE:-}"
DEVIATIONS="${DEVIATIONS:-}"
SIM_REPO_DIR="${SIM_REPO_DIR:-.}"
IEC104_PORT="${IEC104_PORT:-2404}"
CAPTURE_PRESET="${CAPTURE_PRESET:-iec104}"



if [[ -d "$OUTDIR" ]]; then
  if [[ "${ALLOW_OVERWRITE:-0}" == "1" ]]; then
    rm -rf "$OUTDIR"
  elif [[ "$ALLOW_PRECREATED_RUN_DIR" == "1" ]]; then
    echo "INFO: using pre-created run folder: $OUTDIR"
  else
    echo "ERROR: ${OUTDIR} already exists."
    echo "Choose another run_number or delete the folder, or set ALLOW_OVERWRITE=1."
    exit 1
  fi
fi

mkdir -p "$PCAPDIR" "$OVSDIR" "$LOGDIR"

echo "Temp run folder: $OUTDIR"
echo "Condition: $COND"
echo "Run number: $RUNNO_PAD"
echo "Duration: ${DUR}s"
echo "Timestamp: ${TS_ISO}"

for cmd in ovs-ofctl ovs-vsctl tshark capinfos sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing command: $cmd"; exit 1; }
done

if [[ "$CAPTURE_PRESET" == "iec104" ]]; then
  IFACES=(
    CONTROLSW-eth3
    DSS1GW-eth1 DSS1GW-eth2 DSS1ASW-eth2 DSS1ASW-eth3
    DSS2GW-eth1 DSS2GW-eth2 DSS2ASW-eth2 DSS2ASW-eth3
    DSS3GW-eth1 DSS3GW-eth2 DSS3ASW-eth1 DSS3ASW-eth2
    DSS4GW-eth1 DSS4GW-eth2 DSS4ASW-eth1 DSS4ASW-eth2
  )
elif [[ "$CAPTURE_PRESET" == "iec104_full" ]]; then
  IFACES=("CONTROLSW-eth3" "WANR1-eth2" "WANR2-eth2" "DSS1GW-eth1" "DSS2GW-eth1")
elif [[ "$CAPTURE_PRESET" == "attacker" ]]; then
  IFACES=("CONTROLSW-eth3" "DPSRS-eth5" "DSS1GW-eth1" "DSS2GW-eth1")
elif [[ "$CAPTURE_PRESET" == "dps" ]]; then
  IFACES=("DPSGW-eth2" "DPSRS-eth2" "DPSRS-eth3" "DPSRS-eth4" "DPSRS-eth5")
else
  echo "ERROR: Unknown CAPTURE_PRESET: '$CAPTURE_PRESET'"
  exit 1
fi

if [[ -n "${IFACES_CSV:-}" ]]; then
  IFS=',' read -r -a IFACES <<< "$IFACES_CSV"
fi

{
  echo "timestamp_iso=${TS_ISO}"
  echo "uname=$(uname -a)"
  echo "tshark=$((tshark -v 2>/dev/null || true) | head -n 1)"
  echo "ovs-vsctl=$((ovs-vsctl --version 2>/dev/null || true) | head -n 1)"
  echo "ovs-ofctl=$((ovs-ofctl -V 2>/dev/null || true) | head -n 1)"
  command -v lscpu >/dev/null 2>&1 && lscpu || true
  command -v free  >/dev/null 2>&1 && free -h || true
} > "${LOGDIR}/host_versions.txt"

SIM_GIT_COMMIT=""
if command -v git >/dev/null 2>&1 && git -C "$SIM_REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SIM_GIT_COMMIT="$(git -C "$SIM_REPO_DIR" rev-parse HEAD 2>/dev/null || true)"
fi

SWS=("CONTROLSW" "WANR1" "WANR2" "WANR3" "DSS1GW" "DSS2GW" "DSS3GW" "DSS4GW" "DSS1ASW" "DSS2ASW" "DSS3ASW" "DSS4ASW" "DPSGW" "DPSRS" "DPSHV" "DPSMV")

echo "Taking OVS snapshots (PRE)..."
for SW in "${SWS[@]}"; do
  if ovs-vsctl br-exists "$SW" >/dev/null 2>&1; then
    ovs-ofctl -O OpenFlow13 dump-ports-desc "$SW" > "${OVSDIR}/${SW}_ports_desc_pre.txt" || true
    ovs-ofctl -O OpenFlow13 dump-ports      "$SW" > "${OVSDIR}/${SW}_ports_pre.txt"      || true
    ovs-ofctl -O OpenFlow13 dump-flows      "$SW" > "${OVSDIR}/${SW}_flows_pre.txt"      || true
  else
    echo "WARN: bridge not found: $SW"
  fi
done

{
  echo "== ovs-vsctl show (pre) =="
  ovs-vsctl show || true
  echo
  echo "== controller/fail-mode (pre) =="
  for SW in "${SWS[@]}"; do
    if ovs-vsctl br-exists "$SW" >/dev/null 2>&1; then
      echo "-- ${SW}"
      echo -n "controller: " ; ovs-vsctl get-controller "$SW" 2>/dev/null || true
      echo -n "fail-mode:  " ; ovs-vsctl get-fail-mode  "$SW" 2>/dev/null || true
      echo
    fi
  done
} > "${OVSDIR}/ovs_state_pre.txt"

echo "Writing runtime ruleset dump..."
{
  echo "# runtime_ruleset.txt"
  echo "# run_id: ${RUN_ID_BASE}"
  echo "# timestamp_iso: ${TS_ISO}"
  echo "# openflow_version: OpenFlow13"
  echo
  for SW in "${SWS[@]}"; do
    echo "===== SWITCH ${SW} ====="
    if ovs-vsctl br-exists "$SW" >/dev/null 2>&1; then
      ovs-ofctl -O OpenFlow13 dump-flows "$SW" || true
    else
      echo "BRIDGE_NOT_FOUND"
    fi
    echo
  done
} > "${OUTDIR}/runtime_ruleset.txt"

IFACES_JSON="$(printf '"%s",' "${IFACES[@]}" | sed 's/,$//')"
SWS_JSON="$(printf '"%s",' "${SWS[@]}" | sed 's/,$//')"
cat > "${OUTDIR}/run_meta.json" <<EOF
{
  "run_id": "${RUN_ID_BASE}",
  "timestamp_iso": "${TS_ISO}",
  "timestamp_tag": "${TS_TAG}",
  "simulator_git_commit": "${SIM_GIT_COMMIT}",
  "attack_type": "${ATTACK_TYPE}",
  "attacker_placement": "${ATTACKER_PLACEMENT}",
  "ruleset_file": "runtime_ruleset.txt",
  "capture_duration_seconds": ${DUR},
  "capture_preset": "${CAPTURE_PRESET}",
  "interfaces": [${IFACES_JSON}],
  "switches": [${SWS_JSON}],
  "openflow_version": "OpenFlow13",
  "known_deviations": "${DEVIATIONS}"
}
EOF

echo "Starting parallel captures"
PIDS=()

for IF in "${IFACES[@]}"; do
  PCAP_OUT="${PCAPDIR}/${RUN_ID_BASE}_${IF}.pcapng"
  LOG_OUT="${LOGDIR}/tshark_${IF}.log"
  echo "Capturing on ${IF} -> ${PCAP_OUT}"
  tshark -n -q -i "${IF}" -a "duration:${DUR}" -w "${PCAP_OUT}" > "${LOG_OUT}" 2>&1 &
  PIDS+=("$!")
done

FAIL=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    FAIL=1
  fi
done

if [[ "$FAIL" -ne 0 ]]; then
  echo "ERROR: One or more tshark captures failed. Check ${LOGDIR}/tshark_*.log"
  exit 1
fi

echo "Capture finished."

echo "Generating per-capture statistics..."
for IF in "${IFACES[@]}"; do
  PCAP_OUT="${PCAPDIR}/${RUN_ID_BASE}_${IF}.pcapng"
  echo "  Processing ${IF} ..."

  tshark -r "$PCAP_OUT" -q -z io,stat,1 \
    > "${PCAP_OUT%.pcapng}_iostat.txt" 2>&1 || true

  tshark -r "$PCAP_OUT" -q -z io,stat,1,"tcp.port==${IEC104_PORT}" \
    > "${PCAP_OUT%.pcapng}_iec104_iostat.txt" 2>&1 || true

  capinfos "$PCAP_OUT" \
    > "${PCAP_OUT%.pcapng}_capinfos.txt" 2>&1 || true

  sha256sum "$PCAP_OUT" > "${PCAP_OUT%.pcapng}.sha256" 2>&1 || true
done

echo "Extracting IEC-104 control command statistics"
{
  for f in "${PCAPDIR}"/*.pcapng; do
    [[ -f "$f" ]] || continue
    echo
    echo "===== $(basename "$f") ====="
    tshark -r "$f" \
      -Y "ip.src==1.1.10.10 && tcp.dstport==${IEC104_PORT} && (iec60870_asdu.typeid==45 || iec60870_asdu.typeid==46)" \
      -T fields \
      -e frame.number \
      -e frame.time_relative \
      -e ip.src \
      -e ip.dst \
      -e tcp.srcport \
      -e tcp.dstport \
      -e iec60870_asdu.typeid \
      -e iec60870_asdu.causetx \
      -e iec60870_asdu.ioa \
      2>/dev/null || echo "(no matching IEC-104 control commands)"
  done
} > "${PCAPDIR}/interface_statistics.txt"

echo "Taking OVS snapshots (POST)..."
for SW in "${SWS[@]}"; do
  if ovs-vsctl br-exists "$SW" >/dev/null 2>&1; then
    ovs-ofctl -O OpenFlow13 dump-ports-desc "$SW" > "${OVSDIR}/${SW}_ports_desc_post.txt" || true
    ovs-ofctl -O OpenFlow13 dump-ports      "$SW" > "${OVSDIR}/${SW}_ports_post.txt"      || true
    ovs-ofctl -O OpenFlow13 dump-flows      "$SW" > "${OVSDIR}/${SW}_flows_post.txt"      || true
  fi
done

ovs-vsctl show > "${OVSDIR}/ovs_vsctl_show_post.txt" 2>/dev/null || true

echo "Writing KPI summary..."
{
  echo "=== KPI Summary: ${RUN_ID_BASE} ==="
  echo "Condition:  ${COND}"
  echo "Timestamp:  ${TS_ISO}"
  echo "Duration:   ${DUR}s"
  echo "Preset:     ${CAPTURE_PRESET}"
  echo "Interfaces: ${IFACES[*]}"
  echo
  echo "--- IEC-104 Packet Rate (tcp.port==${IEC104_PORT}) ---"
  for IF in "${IFACES[@]}"; do
    IEC_STAT="${PCAPDIR}/${RUN_ID_BASE}_${IF}_iec104_iostat.txt"
    CINFO_F="${PCAPDIR}/${RUN_ID_BASE}_${IF}_capinfos.txt"
    if [[ -f "$IEC_STAT" ]]; then
      PEAK_MEAN="$(awk '/^[|][[:space:]]*[0-9]/ { n=split($0, f, "|"); v=f[3]+0; if (v > mx) mx=v; sm+=v; ct++ } END { printf "%d %s", mx, (ct>0 ? sprintf("%.1f", sm/ct) : "0.0") }' "$IEC_STAT")"
      PEAK="${PEAK_MEAN%% *}"
      MEAN="${PEAK_MEAN##* }"
      TOTAL_PKTS="n/a"
      [[ -f "$CINFO_F" ]] && TOTAL_PKTS="$(grep "Number of packets" "$CINFO_F" | grep -oE '[0-9]+' | tail -1)"
      printf "  %-30s  peak=%4s pps  mean=%5s pps  total_pkts=%s\n" \
        "${IF}" "${PEAK:-0}" "${MEAN:-0.0}" "${TOTAL_PKTS:-n/a}"
    else
      echo "  ${IF}: iostat file not found"
    fi
  done
  echo
  echo "--- OVS Flow Table Changes (pre -> post) ---"
  any_delta=0
  for SW in "${SWS[@]}"; do
    PRE_F="${OVSDIR}/${SW}_flows_pre.txt"
    POST_F="${OVSDIR}/${SW}_flows_post.txt"
    if [[ -f "$PRE_F" && -f "$POST_F" ]]; then
      PRE_N="$(grep -c "cookie=" "$PRE_F" 2>/dev/null || echo 0)"
      POST_N="$(grep -c "cookie=" "$POST_F" 2>/dev/null || echo 0)"
      DELTA=$(( POST_N - PRE_N ))
      if [[ "$DELTA" -ne 0 ]]; then
        printf "  %-12s  pre=%d  post=%d  delta=%+d\n" "${SW}" "$PRE_N" "$POST_N" "$DELTA"
        any_delta=1
      fi
    fi
  done
  [[ "$any_delta" -eq 0 ]] && echo "  (no flow table changes)"
  echo
  echo "--- OVS Port Drop Counters (pre -> post) ---"
  any_drops=0
  for SW in "${SWS[@]}"; do
    PRE_F="${OVSDIR}/${SW}_ports_pre.txt"
    POST_F="${OVSDIR}/${SW}_ports_post.txt"
    if [[ -f "$PRE_F" && -f "$POST_F" ]]; then
      PRE_D="$(grep -oE 'drop=[0-9]+' "$PRE_F" 2>/dev/null | awk -F= '{s+=$2} END{print s+0}')"
      POST_D="$(grep -oE 'drop=[0-9]+' "$POST_F" 2>/dev/null | awk -F= '{s+=$2} END{print s+0}')"
      DELTA=$(( POST_D - PRE_D ))
      if [[ "$DELTA" -gt 0 ]]; then
        printf "  %-12s  drops delta=%d\n" "${SW}" "$DELTA"
        any_drops=1
      fi
    fi
  done
  [[ "$any_drops" -eq 0 ]] && echo "  (no port drops detected)"
} > "${OUTDIR}/kpi_summary.txt"

echo "Writing manifest.sha256..."
(
  cd "$OUTDIR"
  find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
) > "${OUTDIR}/manifest.sha256" || true

mkdir -p "$DEST_ROOT"
cp -a "$OUTDIR" "$DEST_ROOT/"
chown -R ubuntu:ubuntu "$DEST_ROOT/$(basename "$OUTDIR")"

echo "Copied to: $DEST_ROOT/$(basename "$OUTDIR")"
echo "Done."
