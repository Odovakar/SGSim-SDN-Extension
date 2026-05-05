#!/usr/bin/env bash

RUNS_DIR="${1:-.}"
OUT="type36_frames.csv"

echo "run_id,condition,interface,frame_no,timestamp,src,dst" > "$OUT"

IFACES="DSS1GW-eth2 DSS2GW-eth2 DSS3GW-eth2 DSS4GW-eth2"

for run_dir in "$RUNS_DIR"/*/; do
    run_id="$(basename "$run_dir")"
    condition="$(echo "$run_id" | sed 's/_[0-9]*$//')"
    for iface in $IFACES; do
        pcap="${run_dir}pcaps/${run_id}_${iface}.pcapng"
        [[ -f "$pcap" ]] || continue
        tshark -r "$pcap" -Y "iec60870_asdu.typeid==36" -T fields -e frame.number -e frame.time_relative -e ip.src -e ip.dst 2>/dev/null \
        |awk -v r="$run_id" -v c="$condition" -v i="$iface" 'NF {print r","c","i","$1","$2","$3","$4}'
    done
done >> "$OUT"

echo "Done: $OUT"