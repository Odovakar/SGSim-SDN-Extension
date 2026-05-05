# SGSim-SDN-Extension

## Protocol-Aware SDN Enforcement for Trusted-Path IEC-104 Command Abuse in Smart Grid Control Networks

> Stian Lillevik and Livinus Obiora Nweke
> - Submitted for review at Elsevier Computer Networks

---

This repository extends the SGSim smart grid emulator originally developed by Filip Holik
([SGSim-Original](https://github.com/filipholik/SmartGridSim)) with a four-RTU topology,
a Ryu/OpenFlow 1.3 SDN controller that performs semantic IEC-104 command inspection,
and a full experiment framework for evaluating trusted-path command abuse and containment.

The controller parses IEC-104 ASDU fields inline and selectively drops Type 46
double-command activation frames when sustained single-RTU or multi-RTU pivot
predicates are satisfied. The experiment results reported in the paper are
reproducible from the data in this repository.

---

## Repository Structure

```text
SGSim-SDN-Extension/
├── controller.py                    # Ryu SDN controller with IEC-104 semantic inspection
├── StartRyuController.sh            # Start the Ryu controller
├── StartSGTopology.sh               # Start baseline or SDN topology
├── GUI/                             # Optional GUI
└── SGSIM_EXPERIMENTS/
    ├── runs.zip                     # Archive of all experimental run folders
    ├── runs.zip.sha256              # SHA-256 checksum for archive verification
    ├── tools/
    │   ├── rc.sh                    # Single run capture script
    │   └── rcwrap.sh                # Attack wrapper (launches attack at T+delay)
    ├── runs/                        # All experimental run folders (one per run)
    │   └── <condition>_<number>/
    │       ├── run_meta.json        # Condition, timestamp, interfaces, switches
    │       ├── kpi_summary.txt      # Per-interface IEC-104 packet rate
    │       ├── runtime_ruleset.txt  # OVS flow table snapshot
    │       ├── manifest.sha256      # Integrity hashes
    │       ├── pcaps/               # Per-interface pcapng + capinfos + iostat
    │       └── logs/                # Ryu log, attack output, timing protocol
    └── extraction/                  # Extraction scripts, derived CSVs, aggregates, and README
```

---

## Data Integrity

All experimental runs are archived in `SGSIM_EXPERIMENTS/runs.zip`. The corresponding
checksum file `SGSIM_EXPERIMENTS/runs.zip.sha256` can be used to verify the archive
before extraction:

```bash
sha256sum -c SGSIM_EXPERIMENTS/runs.zip.sha256
```

---

## Dependencies

```bash
sudo apt update -y
sudo apt install -y mininet openvswitch-switch python3 python3-pip sqlite3 xterm php-cli
```

**Python environment for Ryu** — Ryu requires Python 3.9:

```bash
pip install ryu eventlet
```

> **Note (ARM / Apple Silicon):** Use [pyenv](https://github.com/pyenv/pyenv) to install
> Python 3.9.18 and create a dedicated virtualenv (`pyenv install 3.9.18 && pyenv virtualenv 3.9.18 ryu-env`).
> On x86 machines, system Python 3.9 is sufficient.

As of now the simulator binaries are compiled for ARM architectures and must be recompiled to run on x86 architectures.
A recompilation guide is described below:

**1. Rebuild the IEC-60870/IEC-104 static library**
```bash
cd comlib_dss
make clean && make
```
**2. Rebuild the IEC-61850/GOOSE/SV static library**
```bash
cd ../comlib_dps
make clean && make
```

**3. Rebuild comlib_dss device binaries**
```bash
for dir in sgdevices/RTU sgdevices/ATTACKER sgdevices/CONTROL sgdevices/CAPTUREPACKET; do
    (cd "$dir" && make clean && make)
done
```

**4. Rebuild comlib_dps device binaries**
```bash
for dir in sgdevices/IED_GOOSE sgdevices/DPSHMI_GOOSE sgdevices/DPSHMI_SV sgdevices/IED_SV; do
    (cd "$dir" && make clean && make)
done
```

**5. Rebuild the GUI**
```bash
cd ../GUI/Application && make clean && make
```

**6. Remove pyenv from StartRyuController.sh **
Edit `StartRyuController.sh` comment out line 4, scroll to the end of the script and comment out line 19, and uncomment line 21.

---

## Running the Simulation

**Baseline (no SDN):**

```bash
./StartSGTopology.sh rtu=4
```

**SDN topology — two terminals:**

```bash
# Terminal 1
./StartRyuController.sh

# Terminal 2
./StartSGTopology.sh ryu rtu=4
```

---

## Running an Experiment

```bash
# Baseline capture, 60 seconds
sudo ./SGSIM_EXPERIMENTS/tools/rc.sh baseline 1 60

# Attack with SDN active, attack launches at T+10s
sudo ./SGSIM_EXPERIMENTS/tools/rcwrap.sh attack_ryu_fw 1 60 10
```

---

## Experimental Conditions

| Condition               | n  | Description                                                   |
| ----------------------- | -- | ------------------------------------------------------------- |
| `baseline`              | 15 | No attack, no SDN                                             |
| `baseline_fw`           | 15 | No attack, static OpenFlow allowlist active                   |
| `attack_no_mitigation`  | 15 | Attack, no enforcement                                        |
| `attack_fw_only`        | 15 | Attack, static allowlist only                                 |
| `attack_ryu_fw`         | 15 | Attack, SDN multi-RTU multi-IOA detection (250 ms)            |
| `attack_ryu_fw_low_IOA` | 15 | Attack, SDN multi-RTU single-IOA pivot detection (250 ms)     |

Rate sensitivity runs at 50, 100, 500, 1500, and 3000 ms intervals are included for both
SDN conditions (5 runs each).

---

## Reproducing the Results

See `SGSIM_EXPERIMENTS/extraction/README.md` for all extraction and aggregation commands
used to reproduce each table and figure in the paper.

---

## Controller Parameters

| Parameter               | Value | Description                                  |
| ----------------------- | ----- | -------------------------------------------- |
| Command window          | 10 s  | Sliding window for per-source state          |
| Single-RTU threshold    | 3     | Type 46 commands to one RTU before block     |
| Pivot command threshold | 2     | Minimum Type 46 commands for pivot detection |
| Pivot RTU threshold     | 2     | Minimum distinct RTU destinations            |
| Block duration          | 90 s  | Offender state timeout                       |
| IEC-104 port            | 2404  | TCP service monitored                        |
