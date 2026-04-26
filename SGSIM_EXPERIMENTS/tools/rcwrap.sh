#!/usr/bin/env bash
set -euo pipefail

COND="${1:-}"
RUNNO="${2:-}"
DUR="${3:-60}"
ATTACK_DELAY="${4:-10}"

if [[ -z "$COND" || -z "$RUNNO" ]]; then
  echo "Usage: $0 <condition> <run_number> [duration_seconds] [attack_delay_seconds]"
  exit 1
fi

ROOT_TMP="/tmp/SGSIM_EXPERIMENTS_TMP"
CAPTURE_PRESET="iec104"
DEST_ROOT="/home/ubuntu/SGS/SGSIM_EXPERIMENTS/runs"
RYU_SOURCE_LOG="/home/ubuntu/Desktop/ryu_live.log"

TARGETS="1.1.1.1,1.1.2.1,1.1.3.1,1.1.4.1"
IEC104_PORT="2404"
ATTACK_MODE="industroyer2"
ATTACK_ARGS="500 5000 5004 1"
ATTACKER_DIR="/home/ubuntu/SGS/comlib_dss/sgdevices/ATTACKER"
ATTACKER_BIN="attack_iec104_misuse"

RUNNO_PAD="$(printf "%03d" "$RUNNO")"
RUN_ID_BASE="${COND}_${RUNNO_PAD}"
OUTDIR="${ROOT_TMP}/${RUN_ID_BASE}"
LOGDIR="${OUTDIR}/logs"
RYU_RUN_LOG="${LOGDIR}/ryu_controller.log"
WRAPPER_META="${LOGDIR}/timing_protocol.txt"
RUN_UUID="$(date +%Y%m%dT%H%M%S)_$$"

echo
echo "=================================================="
echo "Run: ${RUN_ID_BASE}  |  Duration: ${DUR}s  |  Attack at T+${ATTACK_DELAY}s"
echo "=================================================="
echo

if [[ ! -f "$RYU_SOURCE_LOG" ]]; then
  echo "ERROR: ${RYU_SOURCE_LOG} not found. Start Ryu first."
  exit 1
fi

if [[ -d "$OUTDIR" ]]; then
  if [[ "${ALLOW_OVERWRITE:-0}" == "1" ]]; then
    rm -rf "$OUTDIR"
  else
    echo "ERROR: ${OUTDIR} already exists. Delete it or pick another run number."
    exit 1
  fi
fi
mkdir -p "$OUTDIR" "$LOGDIR"

read -rp "Press Enter when Mininet and Ryu are ready..."

START_TS="$(date -Iseconds)"
echo "$START_TS" > "${LOGDIR}/capture_start_time.txt"

CAPTURE_PRESET="$CAPTURE_PRESET" ROOT_TMP="$ROOT_TMP" DEST_ROOT="$DEST_ROOT" ALLOW_PRECREATED_RUN_DIR=1 \
  ./run_capture.sh "$COND" "$RUNNO" "$DUR" &
CAP_PID=$!

(
  sleep "$ATTACK_DELAY"
  CUE_TS="$(date -Iseconds)"
  echo "$CUE_TS" > "${LOGDIR}/attack_cue_time.txt"
  printf '\a\a\a\n'
  echo "### LAUNCHING ATTACK — Mode: ${ATTACK_MODE} | Targets: ${TARGETS} ###"
  printf '\a\a\a\n'

  CONTROL_PID=$(pgrep -f "mininet:CONTROL$")
  mnexec -a "$CONTROL_PID" bash -c \
    "cd ${ATTACKER_DIR} && ./${ATTACKER_BIN} '${TARGETS}' ${IEC104_PORT} ${ATTACK_MODE} ${ATTACK_ARGS}" \
    2>&1 | tee "${LOGDIR}/attack_output.log"
) &
CUE_PID=$!

wait "$CAP_PID"
CAP_RC=$?
END_TS="$(date -Iseconds)"
echo "$END_TS" > "${LOGDIR}/capture_end_time.txt"

kill "$CUE_PID" 2>/dev/null || true
wait "$CUE_PID" 2>/dev/null || true

if [[ "$CAP_RC" -ne 0 ]]; then
  echo "ERROR: run_capture.sh failed with exit code ${CAP_RC}"
  exit "$CAP_RC"
fi

cp "$RYU_SOURCE_LOG" "$RYU_RUN_LOG"

{
  echo "run_id=${RUN_ID_BASE}"
  echo "run_uuid=${RUN_UUID}"
  echo "condition=${COND}"
  echo "run_number=${RUNNO_PAD}"
  echo "duration_seconds=${DUR}"
  echo "attack_delay_seconds=${ATTACK_DELAY}"
  echo "capture_preset=${CAPTURE_PRESET}"
  echo "capture_start=${START_TS}"
  echo "attack_cue=$(cat "${LOGDIR}/attack_cue_time.txt" 2>/dev/null || echo n/a)"
  echo "capture_end=${END_TS}"
  echo "wrapper_status=ok"
  echo "attack_launch_method=automated_mnexec_at_T+${ATTACK_DELAY}s"
  echo "attack_targets=${TARGETS}"
  echo "attack_mode=${ATTACK_MODE}"
  echo "attack_args=${ATTACK_ARGS}"
  echo "ryu_log_source=${RYU_SOURCE_LOG}"
  echo "ryu_log_per_run=${RYU_RUN_LOG}"
  echo "outdir=${OUTDIR}"
  echo "logdir=${LOGDIR}"
} > "$WRAPPER_META"

cp "$RYU_RUN_LOG" "${DEST_ROOT}/${RUN_ID_BASE}/logs/"
cp "$WRAPPER_META" "${DEST_ROOT}/${RUN_ID_BASE}/logs/"

echo "Run complete: ${RUN_ID_BASE}"
echo "Per-run Ryu log: ${RYU_RUN_LOG}"
echo "Timing metadata: ${WRAPPER_META}"