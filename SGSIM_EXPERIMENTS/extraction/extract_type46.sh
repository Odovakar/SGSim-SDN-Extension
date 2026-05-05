#!/usr/bin/env bash

RUNS_DIR="${1:-.}"
OUT="type46_events.csv"

echo "run_id,condition,interface,frame_no,timestamp,src,dst,sport,dport,typeid,cot,ioa" > "$OUT"

for stats in "$RUNS_DIR"/attack_*/pcaps/interface_statistics.txt; do
    run_dir="$(dirname "$(dirname "$stats")")"
    run_id="$(basename "$run_dir")"
    condition="$(echo "$run_id" | sed 's/_[0-9]*$//')"
    iface=""
    while IFS= read -r line; do
        if [[ "$line" =~ ^=====\ (.+)\.pcapng\ ===== ]]; then
            fname="${BASH_REMATCH[1]}"
            iface="$(echo "$fname" | sed "s/${run_id}_//")"
        elif [[ -n "$line" && -n "$iface" ]]; then
            echo "$run_id,$condition,$iface,$line" | tr '\t' ','
        fi
    done < "$stats"
done >> "$OUT"

echo "Done: $OUT"