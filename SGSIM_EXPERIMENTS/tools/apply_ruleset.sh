#!/usr/bin/env bash
set -euo pipefail

OFV="OpenFlow13"

echo "Applying IEC-104 allowlist..."

# CONTROLSW
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=3,nw_src=1.1.10.10,nw_dst=1.1.1.1,tp_dst=2404,actions=output:2"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=2,nw_src=1.1.1.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:3"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=3,nw_src=1.1.10.10,nw_dst=1.1.2.1,tp_dst=2404,actions=output:1"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=1,nw_src=1.1.2.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:3"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=3,nw_src=1.1.10.10,nw_dst=1.1.3.1,tp_dst=2404,actions=output:4"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=4,nw_src=1.1.3.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:3"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=3,nw_src=1.1.10.10,nw_dst=1.1.4.1,tp_dst=2404,actions=output:4"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=300,tcp,in_port=4,nw_src=1.1.4.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:3"
sudo ovs-ofctl -O $OFV add-flow CONTROLSW "priority=0,actions=drop"

# WANR1
sudo ovs-ofctl -O $OFV add-flow WANR1 "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow WANR1 "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.1.1,tp_dst=2404,actions=output:2"
sudo ovs-ofctl -O $OFV add-flow WANR1 "priority=300,tcp,in_port=2,nw_src=1.1.1.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:1"
sudo ovs-ofctl -O $OFV add-flow WANR1 "priority=0,actions=drop"

# WANR2
sudo ovs-ofctl -O $OFV add-flow WANR2 "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow WANR2 "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.2.1,tp_dst=2404,actions=output:2"
sudo ovs-ofctl -O $OFV add-flow WANR2 "priority=300,tcp,in_port=2,nw_src=1.1.2.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:1"
sudo ovs-ofctl -O $OFV add-flow WANR2 "priority=0,actions=drop"

# WANR3
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.3.1,tp_dst=2404,actions=output:2"
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=300,tcp,in_port=2,nw_src=1.1.3.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:1"
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.4.1,tp_dst=2404,actions=output:3"
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=300,tcp,in_port=3,nw_src=1.1.4.1,nw_dst=1.1.10.10,tp_src=2404,actions=output:1"
sudo ovs-ofctl -O $OFV add-flow WANR3 "priority=0,actions=drop"

# DSS1GW
sudo ovs-ofctl -O $OFV add-flow DSS1GW "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS1GW "priority=350,tcp,nw_src=1.1.30.66,nw_dst=1.1.1.1,tp_dst=2404,actions=drop"
sudo ovs-ofctl -O $OFV add-flow DSS1GW "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.1.1,tp_dst=2404,actions=CONTROLLER:65535"
sudo ovs-ofctl -O $OFV add-flow DSS1GW "priority=300,tcp,in_port=2,nw_src=1.1.1.1,nw_dst=1.1.10.10,tp_src=2404,actions=CONTROLLER:256,output:1"
sudo ovs-ofctl -O $OFV add-flow DSS1GW "priority=0,actions=drop"

# DSS2GW
sudo ovs-ofctl -O $OFV add-flow DSS2GW "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS2GW "priority=350,tcp,nw_src=1.1.30.66,nw_dst=1.1.2.1,tp_dst=2404,actions=drop"
sudo ovs-ofctl -O $OFV add-flow DSS2GW "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.2.1,tp_dst=2404,actions=CONTROLLER:65535"
sudo ovs-ofctl -O $OFV add-flow DSS2GW "priority=300,tcp,in_port=2,nw_src=1.1.2.1,nw_dst=1.1.10.10,tp_src=2404,actions=CONTROLLER:256,output:1"
sudo ovs-ofctl -O $OFV add-flow DSS2GW "priority=0,actions=drop"

# DSS3GW
sudo ovs-ofctl -O $OFV add-flow DSS3GW "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS3GW "priority=350,tcp,nw_src=1.1.30.66,nw_dst=1.1.3.1,tp_dst=2404,actions=drop"
sudo ovs-ofctl -O $OFV add-flow DSS3GW "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.3.1,tp_dst=2404,actions=CONTROLLER:65535"
sudo ovs-ofctl -O $OFV add-flow DSS3GW "priority=300,tcp,in_port=2,nw_src=1.1.3.1,nw_dst=1.1.10.10,tp_src=2404,actions=CONTROLLER:256,output:1"
sudo ovs-ofctl -O $OFV add-flow DSS3GW "priority=0,actions=drop"

# DSS4GW
sudo ovs-ofctl -O $OFV add-flow DSS4GW "priority=400,arp,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS4GW "priority=350,tcp,nw_src=1.1.30.66,nw_dst=1.1.4.1,tp_dst=2404,actions=drop"
sudo ovs-ofctl -O $OFV add-flow DSS4GW "priority=300,tcp,in_port=1,nw_src=1.1.10.10,nw_dst=1.1.4.1,tp_dst=2404,actions=CONTROLLER:65535"
sudo ovs-ofctl -O $OFV add-flow DSS4GW "priority=300,tcp,in_port=2,nw_src=1.1.4.1,nw_dst=1.1.10.10,tp_src=2404,actions=CONTROLLER:256,output:1"
sudo ovs-ofctl -O $OFV add-flow DSS4GW "priority=0,actions=drop"

# Access switches — transparent L2
sudo ovs-ofctl -O $OFV add-flow DSS1ASW "priority=1,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS2ASW "priority=1,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS3ASW "priority=1,actions=NORMAL"
sudo ovs-ofctl -O $OFV add-flow DSS4ASW "priority=1,actions=NORMAL"

echo "Done."