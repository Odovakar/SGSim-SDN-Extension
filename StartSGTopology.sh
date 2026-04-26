#!/usr/bin/env bash
# Unified Smart Grid topology launcher.
#
# Usage:
#   ./StartSGTopology.sh              # 2 RTUs, OVSController (legacy)
#   ./StartSGTopology.sh ryu          # 2 RTUs, Ryu remote controller
#   ./StartSGTopology.sh rtu=4        # 4 RTUs, OVSController
#   ./StartSGTopology.sh ryu rtu=4    # 4 RTUs, Ryu remote controller
#
# Arguments can be provided in any order.
# Ensure Ryu is already running (./StartRyuController.sh) when using the ryu option.

USE_RYU=false
RTU_COUNT=2

for arg in "$@"; do
    case "$arg" in
        ryu)
            USE_RYU=true
            ;;
        rtu=*)
            RTU_COUNT="${arg#rtu=}"
            ;;
    esac
done

cd topologies
sudo mn --clean
if [ "$USE_RYU" = true ]; then
    sudo python3 ./SmartGridTopology_ryu.py --switch ovsk,protocols=OpenFlow13 --rtu-count "$RTU_COUNT"
else
    sudo python3 ./SmartGridTopology.py --rtu-count "$RTU_COUNT"
fi
cd ../GUI
./initDatabase.sh

