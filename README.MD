# SGSim-SDN-EXTENSION
This repository contains a Smart Grid Simulation simulator called SGSim, initially created and scripted by Filip Holik, and the original simulator can be found at this repository: [SGSim-Original](https://github.com/filipholik/SmartGridSim)

The simulator emulates IEC-61850/IEC-60870 substations inside a Mininet network, running C-based HMI and RTU processes through Open vSwitch switches. The SDN extension adds a Ryu OpenFlow 1.3 controller (controller.py) that performs semantic packet inspection in order to detect and block malicious IEC-104 command patterns.

# Dependencies
```bash
sudo apt update -y
sudo apt install -y mininet openvswitch-switch python3 python3-pip sqlite3 xterm php-cli
```

## Python environment for Ryu
Ryu is specific regarding which Python version it uses. In the case of running the host VM and simulator on an ARM CPU, you must install Python 3.9 through pyenv

```bash
curl https://pyenv.run | bash

pyenv install 3.9.18

pyenv virtualenv 3.9.18 ryu-env
pyenv activate ryu-env
pip install ryu eventlet
```

## Note:
Most development work was done on a macbook with Apple silicon, meaning all x86 architectures must recompile the binaries to work for x86. In this case, installing pyenv to run python 3.9.x is not necessary.

# Running the Simulation.
## Stock Topology (no SDN/no Ryu)
This is the baseline mode using OVS's built-in learning switch (OVSController). No Ryu required.

```bash
# 2 RTUs (default)
./StartSGTopology.sh

# 4 RTUs
./StartSGTopology.sh rtu=4
````

## SDN Topology with Ryu (attack detection & mitigation)
Run in two separate terminals.

Terminal 1 - Start Ryu controller first:
```bash
./StartRyuController.sh
```

Terminal 2 - Start the topology:
```bash
./StartSGTopology_ryu.sh
./StartSGTopology.sh ryu rtu=4
```

## GUI
In the parent directory, either cd into the GUI directory or start it from the parent directory as described:
```bash
./GUI/StartGUI.sh
```

# SGSIM_EXPERIMENTS Directory
Each run folder contains 

|File|Contents|
|run_meta.json|Metadata:condition, timestamp, duration, git commit(void), topology interfaces, OVS switches|
|kpi_summary.txt|Per-interface IEC-104 packet rate|
|runtime_ruleset.txt|OVS flow table snapshot at capture time|
|`pcaps/`|Per-interface `.pcap` files captured by tshark|
|`logs/`|Ryu controller log, attack output log, timing logs|
|`manifeset.sha256`|Integrity hashes of all captured files|

## Running an Experiment
```bash
# Basic: condition name, run number, duration in seconds
sudo ./SGSIM_EXPERIMENTS/tools/rc.sh baseline 1 60

# With attack (starts attack 10s into capture):
sudo ./SGSIM_EXPERIMENTS/tools/rcwrap.sh attack_ryu_fw 1 60 10
```