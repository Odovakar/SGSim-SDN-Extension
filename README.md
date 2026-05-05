# SGSim-SDN-Extension

**Protocol-Aware SDN Enforcement for Trusted-Path IEC-104 Command Abuse in Smart Grid Control Networks**
Stian Lillevik, Livinus Obiora Nweke
Noroff University College / NTNU

This repository extends the SGSim smart grid emulator originally developed by Filip Holik
([SGSim-Original](https://github.com/filipholik/SmartGridSim)) with a four-RTU topology,
a Ryu/OpenFlow 1.3 SDN controller that performs semantic IEC-104 command inspection,
and a full experiment framework for evaluating trusted-path command abuse and containment.

The controller parses IEC-104 ASDU fields inline and selectively drops Type 46
double-command activation frames when sustained single-RTU or multi-RTU pivot
predicates are satisfied. The experiment results reported in the paper and the
accompanying bachelor's thesis are reproducible from the data in this repository.

---

## Repository Structure

```text
SGSim-SDN-Extension/
├── controller.py                    # Ryu SDN controller with IEC-104 semantic inspection
├── StartRyuController.sh            # Start the Ryu controller
├── StartSGTopology.sh               # Start baseline or SDN topology
├── GUI/                             # Optional GUI
└── SGSIM_EXPERIMENTS/
    ├── tools/
    │   ├── rc.sh                    # Single run capture script
    │   └── rcwrap.sh                # Attack wrapper (launches attack at T+delay)
    ├── runs/                        # All experimental run folders (one per run)
    │   └── &lt;condition&gt;_&lt;NNN&gt;/
    │       ├── run_meta.json        # Condition, timestamp, interfaces, switches
    │       ├── kpi_summary.txt      # Per-interface IEC-104 packet rate
    │       ├── runtime_ruleset.txt  # OVS flow table snapshot
    │       ├── manifest.sha256      # Integrity hashes
    │       ├── pcaps/               # Per-interface pcapng + capinfos + iostat
    │       └── logs/                # Ryu log, attack output, timing protocol
    └── extraction/                  # Extraction scripts, derived CSVs and aggregates
```

---

## Dependencies

```bash
sudo apt update -y
sudo apt install -y mininet openvswitch-switch python3 python3-pip sqlite3 xterm php-cli
```

**Python environment for Ryu** — Ryu requires Python 3.9. On ARM (Apple Silicon) use pyenv:

```bash
curl https://pyenv.run | bash
pyenv install 3.9.18
pyenv virtualenv 3.9.18 ryu-env
pyenv activate ryu-env
pip install ryu eventlet
```

Note: On x86 machines pyenv is not required, system Python 3.9 should work.

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

| Condition               | n  | Description                                         |
| ----------------------- | -- | --------------------------------------------------- |
| `baseline`              | 15 | No attack, no SDN                                   |
| `baseline_fw`           | 15 | No attack, static OpenFlow allowlist active         |
| `attack_no_mitigation`  | 15 | Attack, no enforcement                              |
| `attack_fw_only`        | 15 | Attack, static allowlist only                       |
| `attack_ryu_fw`         | 15 | Attack, SDN multi-RTU multi-IOA detection (250 ms) |
| `attack_ryu_fw_low_IOA` | 15 | Attack, SDN multi-RTU single-IOA pivot detection (250 ms) |

Rate sensitivity runs at 50, 100, 500, 1500, 3000 ms intervals are included for both
SDN conditions (5 runs each).

---

## Reproducing the Results

The `SGSIM_EXPERIMENTS/extraction/` directory contains the scripts and filtered files
used to produce all tables and figures in the paper. There's also a .md page with all 
commands used to extract and/or aggregate the data for every table.

**Step 1 — run the three extraction scripts from `SGSIM_EXPERIMENTS/runs/`:**

```bash
bash ../extraction/extract_type46.sh . > ../extraction/type46_events.csv
bash ../extraction/extract_blocks.sh . > ../extraction/block_events.csv
bash ../extraction/extract_type36.sh . > ../extraction/type36_frames.csv
```

The Type 36 extraction hits all pcaps and takes a while.

**Step 2 — compute TTB from type46_events.csv:**

For multi-RTU multi-IOA (block fires on 3rd command):

```bash
awk -F',' 'NR==1{next} $3=="CONTROLSW-eth3" && $10==46 {count[$1]++; if(count[$1]==1) first[$1]=$5; if(count[$1]==3) third[$1]=$5} END {for(r in first) printf "%s %.9f %.9f %.9f\n", r, first[r], third[r], third[r]-first[r]}' type46_events.csv | sort > ttb_raw.txt
```

For multi-RTU single-IOA pivot (block fires on 2nd command):

```bash
awk -F',' 'NR==1{next} $3=="CONTROLSW-eth3" && $10==46 {count[$1]++; if(count[$1]==1) first[$1]=$5; if(count[$1]==2) second[$1]=$5} END {for(r in first) if(r in second) printf "%s %.9f %.9f %.9f\n", r, first[r], second[r], second[r]-first[r]}' type46_events.csv | sort > ttb_raw_low_IOA.txt
```

**Step 3 — all further statistics** are computed from these files using awk and grep.
See the extraction scripts for the specific commands used for each table.

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
