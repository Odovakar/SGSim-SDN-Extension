#!/usr/bin/env bash
# Start the DSS topology with Ryu remote controller.
# Ensure Ryu is already running (./StartRyuController.sh) before executing this.

cd topologies
sudo mn --clean
sudo python3 ./DSSTopology_ryu.py --switch ovsk,protocols=OpenFlow13
sqlite3 ../dbHandler/SGData.db "UPDATE infos SET PortConnected = 1 WHERE id=1"
sqlite3 ../dbHandler/SGData.db "UPDATE infos SET PortConnected = 1 WHERE id=2"
