#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call
import time
import argparse

RTU_COUNT = 2

def smartGridSimNetwork():

    net = Mininet( topo=None,
                   build=False,
                   ipBase='1.0.0.0/8')

    info( '\n*** ************************************* *** \n' )
    info( '*** Starting Smart Grid Simulation Model *** \n' )
    info( '*** Topology: 1xDPS + %dxDSS + Control Center \n' % RTU_COUNT )
    info( '*** Version: 250904 \n' )
    info( '*** Author: filip.holik@ntnu.no  \n' )
    info( '*** ************************************* *** \n' )
    info( '*** Adding controller\n' )
    c0=net.addController(name='c0',
                      controller=RemoteController,
                      ip='127.0.0.1',
                      protocol='tcp',
                      port=6633)

    switchType = OVSKernelSwitch; 

    info( '*** Starting networking devices\n')
    DSS1GW = net.addSwitch('DSS1GW', cls=switchType, dpid='1',failMode='standalone')    
    DSS2GW = net.addSwitch('DSS2GW', cls=switchType, dpid='2',failMode='standalone')    
    WANR1 = net.addSwitch('WANR1', cls=switchType, dpid='3',failMode='standalone')
    WANR2 = net.addSwitch('WANR2', cls=switchType, dpid='4',failMode='standalone') 
    CONTROLSW = net.addSwitch('CONTROLSW', cls=switchType, dpid='5',failMode='standalone') 
    DPSGW = net.addSwitch('DPSGW', cls=switchType, dpid='6',failMode='standalone') 
    DPSRS = net.addSwitch('DPSRS', cls=switchType, dpid='7',failMode='standalone') 
    DPSHV = net.addSwitch('DPSHV', cls=switchType, dpid='8',failMode='standalone') 
    DPSMV = net.addSwitch('DPSMV', cls=switchType, dpid='9',failMode='standalone') 

    info( '*** Starting external connection\n')
    DSS1ASW = net.addSwitch('DSS1ASW', cls=switchType, dpid='10',failMode='standalone') 
    DSS2ASW = net.addSwitch('DSS2ASW', cls=switchType, dpid='11',failMode='standalone') 
    Intf( 'enp0s3', node=DSS1ASW )
    Intf( 'enp0s8', node=DSS2ASW )
    Intf( 'enp0s9', node=DPSHV )
    Intf( 'enp0s10', node=DPSGW )

    if RTU_COUNT >= 4:
        DSS3GW = net.addSwitch('DSS3GW', cls=switchType, dpid='12',failMode='standalone')
        DSS3ASW = net.addSwitch('DSS3ASW', cls=switchType, dpid='13',failMode='standalone')
        DSS4GW = net.addSwitch('DSS4GW', cls=switchType, dpid='14',failMode='standalone')
        DSS4ASW = net.addSwitch('DSS4ASW', cls=switchType, dpid='15',failMode='standalone')
        WANR3 = net.addSwitch('WANR3', cls=switchType, dpid='16',failMode='standalone')

    info( '*** Starting hosts \n')
    DSS1RTU = net.addHost('DSS1RTU', cls=Host, ip='1.1.1.1', defaultRoute='1.1.10.10',mac='b4:b1:5a:00:00:06')
    DSS2RTU = net.addHost('DSS2RTU', cls=Host, ip='1.1.2.1', defaultRoute='1.1.10.10',mac='b4:b1:5a:00:00:07')
    CONTROL = net.addHost('CONTROL', cls=Host, ip='1.1.10.10', defaultRoute='1.1.1.1',mac='00:02:B3:00:00:08')
    IED1 = net.addHost('IED1', cls=Host, ip='1.1.30.1', defaultRoute='1.1.10.10',mac='b4:b1:5a:0a:b4:01')
    IED2 = net.addHost('IED2', cls=Host, ip='1.1.30.2', defaultRoute='1.1.10.10',mac='b4:b1:5a:00:00:02')
    IED3 = net.addHost('IED3', cls=Host, ip='1.1.30.3', defaultRoute='1.1.10.10',mac='00:30:A7:00:00:03')
    IED4 = net.addHost('IED4', cls=Host, ip='1.1.30.4', defaultRoute='1.1.10.10',mac='00:30:A7:00:00:04')
    DPSHMI = net.addHost('DPSHMI', cls=Host, ip='1.1.30.10', defaultRoute='1.1.10.10',mac='00:80:BC:00:00:05')
    ATTACKER = net.addHost('ATTACKER', cls=Host, ip='1.1.30.66', defaultRoute='1.1.10.10',mac='00:06:5B:00:00:66')

    if RTU_COUNT >= 4:
        DSS3RTU = net.addHost('DSS3RTU', cls=Host, ip='1.1.3.1', defaultRoute='1.1.10.10',mac='b4:b1:5a:00:00:08')
        DSS4RTU = net.addHost('DSS4RTU', cls=Host, ip='1.1.4.1', defaultRoute='1.1.10.10',mac='b4:b1:5a:00:00:09')

    info( '*** Setting link parameters\n')
    #WAN1 = {'bw':1000,'delay':'20ms','loss':1,'jitter':'10ms'} 
    #GBPS = {'delay':'18ms'} 
    MBPS = {'bw':10} 

    info( '*** Adding links\n')
    net.addLink(WANR2, CONTROLSW)
    net.addLink(WANR1, CONTROLSW)
    net.addLink(CONTROLSW, CONTROL)
    net.addLink(WANR1, DSS1GW, cls=TCLink , **MBPS)
    net.addLink(WANR2, DSS2GW, cls=TCLink , **MBPS)

    if RTU_COUNT >= 4:
        net.addLink(WANR3, CONTROLSW)

    net.addLink(DPSGW, CONTROLSW)
    net.addLink(DPSGW, DPSRS)
    net.addLink(DPSRS, DPSHV)
    net.addLink(DPSRS, DPSMV)
    net.addLink(IED1, DPSHV)
    net.addLink(IED2, DPSHV)
    net.addLink(IED3, DPSMV)
    net.addLink(IED4, DPSMV)
    net.addLink(DPSHMI, DPSRS)

    net.addLink(DPSRS, ATTACKER)

    info( '*** Adding redundant links\n')
    #net.addLink(WANR2, DSS1GW, cls=TCLink , **GBPS)
    #net.addLink(WANR1, DSS2GW, cls=TCLink , **GBPS)
    #net.addLink(DSS1GW, DSS1RTU)
    #net.addLink(DSS2GW, DSS2RTU)

    info( '*** Adding links for external connections \n')
    net.addLink(DSS1RTU, DSS1ASW)
    net.addLink(DSS1ASW, DSS1GW)
    net.addLink(DSS2RTU, DSS2ASW)
    net.addLink(DSS2ASW, DSS2GW)

    if RTU_COUNT >= 4:
        net.addLink(WANR3, DSS3GW, cls=TCLink , **MBPS)
        net.addLink(WANR3, DSS4GW, cls=TCLink , **MBPS)
        net.addLink(DSS3RTU, DSS3ASW)
        net.addLink(DSS3ASW, DSS3GW)
        net.addLink(DSS4RTU, DSS4ASW)
        net.addLink(DSS4ASW, DSS4GW)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting networking devices\n')
    net.get('DSS1GW').start([c0])
    net.get('DSS2GW').start([c0])
    net.get('WANR1').start([c0])
    net.get('WANR2').start([c0])
    net.get('CONTROLSW').start([c0])
    net.get('DSS1ASW').start([c0])
    net.get('DSS2ASW').start([c0])
    net.get('DPSGW').start([c0])
    net.get('DPSRS').start([c0])
    net.get('DPSHV').start([c0])
    net.get('DPSMV').start([c0])

    if RTU_COUNT >= 4:
        net.get('DSS3GW').start([c0])
        net.get('DSS3ASW').start([c0])
        net.get('DSS4GW').start([c0])
        net.get('DSS4ASW').start([c0])
        net.get('WANR3').start([c0])

    info( '*** Preparing custom scripts \n')
    CLI.do_sgsim_startcom_104 = sgsim_startcom_104
    CLI.do_sgsim_startcom_goose = sgsim_startcom_goose
    CLI.do_sgsim_startcom_sglab_goose = sgsim_startcom_sglab_goose
    CLI.do_sgsim_startcom_sv = sgsim_startcom_sv
    CLI.do_sgsim_startperfmon = sgsim_startperfmon
    CLI.do_sgsim_attackmirror = sgsim_attackmirror
    CLI.do_sgsim_attack_goose_fdi = sgsim_attack_goose_fdi
    CLI.do_sgsim_attack_dos = sgsim_attack_dos
    CLI.do_sgsim_attack_iec104_misuse = sgsim_attack_iec104_misuse
    CLI.do_sgsim_attack_iec104_help = sgsim_help_attack_iec104
    info( '*** Smart Grid Simulation Model Started *** \n' )
    CLI(net)

    net.stop()

def sgsim_startcom_goose(self, line):
    "Starts the GOOSE communication in the primary substation." 
    net = self.mn  
    info('Inserting rules for DPSGW switch... \n')
    net.get('DPSGW').cmdPrint('ovs-ofctl add-flow DPSGW dl_type=0x88b8,action=DROP')     # Simulation of GOOSE multicast 
    info('Starting GOOSE communication... \n')    
    net.get('IED1').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "IED1-GOOSE" -e "cd ../comlib_dps/sgdevices/IED_GOOSE/;./ied_goose IED1-eth0;bash"&') 
    time.sleep(0.5)
    net.get('IED4').cmdPrint('xterm -geometry 90x30+30+30 -fa "Monospace" -fs 12 -T "IED4-GOOSE" -e "cd ../comlib_dps/sgdevices/IED_GOOSE/;./ied_goose IED4-eth0;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "DPSHMI-GOOSE-1" -e "cd ../comlib_dps/sgdevices/DPSHMI_GOOSE/;./dpshmi 1;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+70+70 -fa "Monospace" -fs 12 -T "DPSHMI-GOOSE-4" -e "cd ../comlib_dps/sgdevices/DPSHMI_GOOSE/;./dpshmi 4;bash"&') 

def sgsim_startcom_sglab_goose(self, line):
    "Starts the GOOSE communication according to the SG LAB data." 
    net = self.mn  
    info('Inserting rules for DPSGW switch... \n')
    net.get('DPSGW').cmdPrint('ovs-ofctl add-flow DPSGW dl_type=0x88b8,action=DROP')     # Simulation of GOOSE multicast 
    info('Starting GOOSE communication... \n')    
    net.get('IED1').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "IED1-GOOSE" -e "cd ../comlib_dps/sgdevices/IED_GOOSE/;./ied_goose_sglab IED1-eth0;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "DPSHMI-GOOSE-1" -e "cd ../comlib_dps/sgdevices/DPSHMI_GOOSE/;./dpshmi;bash"&') 

def sgsim_attack_goose_fdi(self, line):
    "Starts the False Data Injection attack on GOOSE communication." 
    net = self.mn  
    info('Starting FDI attack... \n')    
    net.get('ATTACKER').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "ATTACKER-FDI" -e "cd ../comlib_dps/sgdevices/ATTACKER/;./fdi_goose ATTACKER-eth0;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "DPSHMI-GOOSE" -e "cd ../comlib_dps/sgdevices/DPSHMI_GOOSE/;./dpshmi;bash"&') 

def sgsim_attack_dos(self, line):
    "Starts the DoS attack from DSS1RTU on the control center." 
    net = self.mn  
    info('Starting DoS attack... \n')    
    net.get('DSS1RTU').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "ATTACKER-DOS" -e "sudo hping3 -S --flood 1.1.10.10;bash"&') 

def sgsim_startcom_sv(self, line):
    "Starts the SV communication in the primary substation." 
    net = self.mn  
    info('Inserting rules for DPSGW switch... \n')
    net.get('DPSGW').cmdPrint('ovs-ofctl add-flow DPSGW dl_type=0x88ba,action=DROP')     # Simulation of SV multicast 
    info('Starting SV communication... \n')    
    net.get('IED2').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "IED2-SV" -e "cd ../comlib_dps/sgdevices/IED_SV/;./ied_sv IED2-eth0;bash"&') 
    time.sleep(0.5)
    net.get('IED3').cmdPrint('xterm -geometry 90x30+30+30 -fa "Monospace" -fs 12 -T "IED3-SV" -e "cd ../comlib_dps/sgdevices/IED_SV/;./ied_sv IED3-eth0;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "DPSHMI-SV-2" -e "cd ../comlib_dps/sgdevices/DPSHMI_SV/;./dpshmi_sv 2;bash"&') 
    time.sleep(0.5)
    net.get('DPSHMI').cmdPrint('xterm -geometry 90x30+70+70 -fa "Monospace" -fs 12 -T "DPSHMI-SV-3" -e "cd ../comlib_dps/sgdevices/DPSHMI_SV/;./dpshmi_sv 3;bash"&') 
    time.sleep(0.5)

def sgsim_startcom_104(self, line):
    "Starts the IEC104 communication (periodical and read requests) for secondary substations." 
    net = self.mn   
    info('Starting IEC104 communication... \n')    
    info('Starting DSS1RTU communication... \n')    
    net.get('DSS1RTU').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "DSS1RTU" -e "cd ../comlib_dss/sgdevices/RTU/;./rtu 1.1.1.1;bash"&') 
    time.sleep(0.5)
    info('Starting DSS2RTU communication... \n')    
    net.get('DSS2RTU').cmdPrint('xterm -geometry 90x30+30+30 -fa "Monospace" -fs 12 -T "DSS2RTU" -e "cd ../comlib_dss/sgdevices/RTU/;./rtu 1.1.2.1;bash"&') 
    time.sleep(0.5)
    info('Starting CONTROL communication with DSS1... \n')    
    net.get('CONTROL').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "CONTROL - DSS1 Monitoring" -e "cd ../comlib_dss/sgdevices/CONTROL/;sleep 1;./control 1.1.1.1;bash"&') 
    time.sleep(0.5)
    info('Starting CONTROL communication with DSS2... \n')  
    net.get('CONTROL').cmdPrint('xterm -geometry 90x30+70+70 -fa "Monospace" -fs 12 -T "CONTROL - DSS2 Monitoring" -e "cd ../comlib_dss/sgdevices/CONTROL/;sleep 1;./control 1.1.2.1;bash"&')
    time.sleep(0.5)
    if RTU_COUNT >= 4:
        info('Starting DSS3RTU communication... \n')    
        net.get('DSS3RTU').cmdPrint('xterm -geometry 90x30+90+90 -fa "Monospace" -fs 12 -T "DSS3RTU" -e "cd ../comlib_dss/sgdevices/RTU/;./rtu 1.1.3.1;bash"&') 
        time.sleep(0.5)
        info('Starting DSS4RTU communication... \n')    
        net.get('DSS4RTU').cmdPrint('xterm -geometry 90x30+110+110 -fa "Monospace" -fs 12 -T "DSS4RTU" -e "cd ../comlib_dss/sgdevices/RTU/;./rtu 1.1.4.1;bash"&') 
        time.sleep(0.5)
        info('Starting CONTROL communication with DSS3... \n')  
        net.get('CONTROL').cmdPrint('xterm -geometry 90x30+130+130 -fa "Monospace" -fs 12 -T "CONTROL - DSS3 Monitoring" -e "cd ../comlib_dss/sgdevices/CONTROL/;sleep 1;./control 1.1.3.1;bash"&')
        time.sleep(0.5)
        info('Starting CONTROL communication with DSS4... \n')  
        net.get('CONTROL').cmdPrint('xterm -geometry 90x30+150+150 -fa "Monospace" -fs 12 -T "CONTROL - DSS4 Monitoring" -e "cd ../comlib_dss/sgdevices/CONTROL/;sleep 1;./control 1.1.4.1;bash"&')
    info('IEC104 communication started... \n(Please close all the opened windows before exiting the Mininet.)  \n')   

def sgsim_startperfmon(self, line):
    "Starts the IEC104 communication (periodical and read requests) with performance monitoring." 
    net = self.mn   
    info('Starting IEC104 communication with performance monitoring... \n')    
    info('Starting DSS1RTU communication... \n')    
    net.get('DSS1RTU').cmdPrint('xterm -geometry 90x30+10+10 -fa "Monospace" -fs 12 -T "DSS1RTU" -e "cd ../comlib_dss/sgdevices/PERFSEND/;./perfsend;bash"&') 
    time.sleep(0.5)
    info('Starting DSS2RTU communication... \n')    
    net.get('DSS2RTU').cmdPrint('xterm -geometry 90x30+30+30 -fa "Monospace" -fs 12 -T "DSS2RTU" -e "cd ../comlib_dss/sgdevices/PERFSEND/;./perfsend;bash"&') 
    time.sleep(0.5)
    info('Starting CONTROL communication with DSS1... \n')    
    net.get('CONTROL').cmdPrint('xterm -geometry 90x30+50+50 -fa "Monospace" -fs 12 -T "CONTROL - DSS1 Monitoring" -e "cd ../comlib_dss/sgdevices/PERFMON/;sleep 1;./perfmon 1.1.1.1;bash"&') 
    time.sleep(0.5)
    info('Starting CONTROL communication with DSS2... \n')  
    net.get('CONTROL').cmdPrint('xterm -geometry 90x30+70+70 -fa "Monospace" -fs 12 -T "CONTROL - DSS2 Monitoring" -e "cd ../comlib_dss/sgdevices/PERFMON/;sleep 1;./perfmon 1.1.2.1;bash"&')
    info('IEC104 communication with performance monitoring started... \n(Please close all the opened windows before exiting the Mininet.)  \n')   

def sgsim_attackmirror(self, line):
    "Makes DSS ASW devices to mirror traffic to external connections. "
    net = self.mn   
    info('Inserting rules for DSS1 switch... \n')    
    net.get('DSS1ASW').cmdPrint('ovs-ofctl add-flow DSS1ASW in_port:2,action=1,3; ovs-ofctl add-flow DSS1ASW in_port:3,action=1,2') 
    info('Inserting rules for DSS2 switch... \n')    
    net.get('DSS2ASW').cmdPrint('ovs-ofctl add-flow DSS2ASW in_port:2,action=1,3; ovs-ofctl add-flow DSS2ASW in_port:3,action=1,2') 

def sgsim_help_attack_iec104(self, line):
    "Show cheatsheet for the IEC-104 misuse tool."
    print("""
SYNOPSIS
  sgsim_attack_iec104_misuse <src_node> <ip> [port] [mode] [rate_ms] [ioa_min] [ioa_max] [ca]

ARGUMENTS
  src_node  CONTROL | ATTACKER                        (required)
  ip        Target IP address                         (required)
  port      Target TCP port                           (default: 2404)
  mode      Attack mode — see below                   (default: read_sweep)
  rate_ms   Delay between operations in milliseconds  (default: 250)
  ioa_min   Lowest IOA / target IOA for command modes (default: 1)
  ioa_max   Highest IOA for read_sweep                (default: 50)
  ca        Common Address of ASDU                    (default: 1)

MODES
  conn_churn    Open/STARTDT/STOPDT/close — new connection every cycle
  start_stop    One connection, rapid STARTDT/STOPDT toggling
  interrogate   One connection, repeated General Interrogation (GI)
  read_sweep    One connection, sequential IOA read commands
  single_cmd    Repeated C_SC_NA_1 ON/OFF toggle — IOA 5000 (Industroyer-style)
  breaker_trip  Repeated C_DC_NA_1 OPEN/CLOSE commands — IOA 5000 (Industroyer-2-style)
  industroyer2  Multi-RTU sequential breaker attack (Industroyer-2 realistic)
                Accepts comma-separated IPs. Pivots RTU-by-RTU sequentially.

EXAMPLES
  sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 conn_churn    200
  sgsim_attack_iec104_misuse CONTROL  1.1.1.1 2404 start_stop    500
  sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 interrogate   250
  sgsim_attack_iec104_misuse CONTROL  1.1.1.1 2404 read_sweep    200 1 100
  sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 single_cmd   1000 5000 5000 1
  sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 breaker_trip 1000 5000 5000 1
  sgsim_attack_iec104_misuse ATTACKER "1.1.1.1,1.1.2.1" 2404 industroyer2 3000 5000 5004 1
  sgsim_attack_iec104_misuse ATTACKER "1.1.1.1,1.1.2.1,1.1.3.1,1.1.4.1" 2404 industroyer2 200 5000 5004 1

STOP
  Ctrl+C in the xterm window

IEC-104 COMMAND TYPE REFERENCE
  C_SC_NA_1 (TypeID 45): Single Command  — binary ON/OFF, used for switches
  C_DC_NA_1 (TypeID 46): Double Command  — OPEN/CLOSE with transition state, used for breakers
  COT 6 (ACTIVATION):    Standard cause-of-transmission for control commands
  IOA 5000:              The control point registered in the SGSim RTU

RATE GUIDANCE
  rate_ms=50   aggressive / high-stress
  rate_ms=250  moderate (default)
  rate_ms=1000 slow / low-noise
""")

def sgsim_attack_iec104_misuse(self, line):
    """
    Run IEC-104 misuse tool from a chosen node (CONTROL or ATTACKER) in its own xterm.

    Usage:
      sgsim_attack_iec104_misuse <src_node> <ip> [port] [mode] [rate_ms] [ioa_min] [ioa_max] [ca]
    """
    net = self.mn
    args = line.strip().split()

    if len(args) < 2:
        print("Usage: sgsim_attack_iec104_misuse <src_node> <ip> [port] [mode] [rate_ms] [ioa_min] [ioa_max] [ca]")
        print("Tip:   sgsim_attack_iec104_help")
        return

    src = args[0].upper()
    target = args[1]
    port = args[2] if len(args) > 2 else "2404"
    mode = args[3] if len(args) > 3 else "read_sweep"
    rate = args[4] if len(args) > 4 else "250"
    ioa_min = args[5] if len(args) > 5 else "1"
    ioa_max = args[6] if len(args) > 6 else "50"
    ca = args[7] if len(args) > 7 else "1"

    if src not in ("CONTROL", "ATTACKER"):
        print("Error: src_node must be CONTROL or ATTACKER")
        return

    # Where your binary lives (relative to Mininet host's cwd in this repo layout)
    workdir = "../comlib_dss/sgdevices/ATTACKER"
    binary = "./attack_iec104_misuse"

    title = f"{src}-IEC104-MISUSE -> {target}:{port} {mode} {rate}ms"
    info(f"Starting IEC-104 misuse tool from {src} in xterm...\n")

    net.get(src).cmdPrint(
        'xterm -geometry 110x35+10+10 -fa "Monospace" -fs 12 '
        f'-T "{title}" -e '
        f'"cd {workdir} && {binary} {target} {port} {mode} {rate} {ioa_min} {ioa_max} {ca}; bash"&'
    )
    time.sleep(0.2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rtu-count', type=int, default=2)
    args, _ = parser.parse_known_args()
    RTU_COUNT = args.rtu_count
    setLogLevel( 'info' )
    smartGridSimNetwork()
