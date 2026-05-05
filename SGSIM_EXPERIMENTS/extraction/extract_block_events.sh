#!/usr/bin/env bash

RUNS_DIR="${1:-.}"
OUT="block_events.csv"

echo "run_id,condition,block_timestamp,src,reason" > "$OUT"

for log in "$RUNS_DIR"/attack_ryu_*/logs/ryu_controller.log; do
    run_dir="$(dirname "$(dirname "$log")")"
    run_id="$(basename "$run_dir")"
    condition="$(echo "$run_id" | sed 's/_[0-9]*$//')"
    grep "INLINE-BLOCK" "$log" | while IFS= read -r line; do
        ts="$(echo "$line" | grep -oP '\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]' | tr -d '[]')"
        src="$(echo "$line" | grep -oP 'src=\S+' | cut -d= -f2)"
        reason="$(echo "$line" | grep -oP 'reason=.+?(?= block)' | cut -d= -f2)"
        echo "$run_id,$condition,$ts,$src,$reason"
    done
done >> "$OUT"

echo "Done: $OUT"