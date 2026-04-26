#!/usr/bin/env bash
set -euo pipefail

PYENV_RYU_PYTHON="/home/ubuntu/.pyenv/versions/3.9.18/envs/ryu-env/bin/python"
RYU_APP="/home/ubuntu/SGS/controller.py"

RYU_LOG="/home/ubuntu/Desktop/ryu_live.log"

echo "*** Starting Ryu IEC-104 Burst Mitigator on 0.0.0.0:6633 ***"
echo "*** Live log: $RYU_LOG ***"
echo "*** Keep this terminal open while running SGSim ***"

mkdir -p "$(dirname "$RYU_LOG")"

echo "Creating live log file..."
: > "$RYU_LOG"
ls -l "$RYU_LOG"

exec stdbuf -oL "$PYENV_RYU_PYTHON" -m ryu.cmd.manager "$RYU_APP" 2>&1 | stdbuf -oL tee -a "$RYU_LOG"