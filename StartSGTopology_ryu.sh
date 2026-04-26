#!/usr/bin/env bash
# Start the Smart Grid topology with Ryu remote controller.
# Ensure Ryu is already running (./StartRyuController.sh) before executing this.
# This script is a thin wrapper around StartSGTopology.sh with the ryu option.

./StartSGTopology.sh ryu "$@"
