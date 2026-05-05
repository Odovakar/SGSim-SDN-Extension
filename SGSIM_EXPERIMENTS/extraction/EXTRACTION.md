# Result Extraction and Commands per Table

All commands run from `SGSIM_EXPERIMENTS/runs/` unless stated otherwise, the scripts must be moved into the runs folder. They have been moved after extraction/filtering to improve the overview.

---

## Prerequisites: Three Base CSVs

Everything is extracted from these three files. The files are readily available in the repo, and the commands used to extract data from the CSVs can be found below. Run once before extracting anything else.

```bash
bash ../extraction/extract_type46.sh . > ../extraction/type46_events.csv
bash ../extraction/extract_blocks.sh . > ../extraction/block_events.csv
bash ../extraction/extract_type36.sh . > ../extraction/type36_frames.csv
```

> `type36_frames.csv` must process every pcap and takes a while.

---

## Table 5.1: Baseline Traffic Statistics

Source: `kpi_summary.txt` in each run folder.
Replace `baseline_0*` with `baseline_fw_0*` to get the firewalled baseline columns.

```bash
for iface in CONTROLSW-eth3 DSS1GW-eth1 DSS1ASW-eth2 DSS2GW-eth1 DSS2ASW-eth2 DSS3GW-eth1 DSS3ASW-eth2 DSS4GW-eth1 DSS4ASW-eth2; do
    grep "$iface" baseline_0*/kpi_summary.txt | grep "peak=" | \
    awk -v iface="$iface" '{sm+=$7; sq+=$7^2; pm+=$4; pq+=$4^2; n++}
    END {mmean=sm/n; mstd=sqrt(sq/n-mmean^2); pmean=pm/n; pstd=sqrt(pq/n-pmean^2);
    printf "%s  mean=%.2f±%.2f  peak=%.1f±%.1f\n", iface, mmean, mstd, pmean, pstd}'
done
```

---

## Table 5.2: Type ID 46 Delivery Under Unmitigated Conditions

Source: `type46_events.csv`
Replace `attack_no_mitigation` with `attack_fw_only` for the second condition.

```bash
grep "attack_no_mitigation" type46_events.csv | awk -F',' '$3~/DSS[0-9]GW-eth2/ {print $1,$7}' | sort | uniq -c
```

---

## Table 5.3: Polling Gap Under Unmitigated Conditions

Source: `type36_frames.csv` → `no_mit_gaps.txt`, `fw_only_gaps.txt`
Replace `attack_no_mitigation` with `attack_fw_only` and output file name accordingly for the second condition.

```bash
awk -F',' '$2=="attack_no_mitigation" && $3=="DSS1GW-eth2" {run=$1; t=$5+0; if(!(run in last)||t<15) last[run]=t; if(t>15&&!(run in first)) first[run]=t} END {for(r in first) print first[r]-last[r]}' type36_frames.csv | sort > no_mit_gaps.txt

awk '{sum+=$1; sumsq+=$1^2; n++; if($1<mn||NR==1)mn=$1; if($1>mx)mx=$1} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "mean=%.2f std=%.2f min=%.1f max=%.1f\n", mean,std,mn,mx}' no_mit_gaps.txt
```

---

## Tables 5.4 and 5.6: SDN Detection and Block Timing (TTB)

Source: `type46_events.csv` -> `ttb_raw.txt` (Table 5.4), `ttb_raw_low_IOA.txt` (Table 5.6)

**Table 5.4**: block fires on 3rd command (multi-RTU multi-IOA):

```bash
awk -F',' 'NR==1{next} $3=="CONTROLSW-eth3" && $10==46 {count[$1]++; if(count[$1]==1) first[$1]=$5; if(count[$1]==3) third[$1]=$5} END {for(r in first) printf "%s %.9f %.9f %.9f\n", r, first[r], third[r], third[r]-first[r]}' type46_events.csv | sort > ttb_raw.txt
```

**Table 5.6**:block fires on 2nd command (multi-RTU single-IOA pivot):

```bash
awk -F',' 'NR==1{next} $3=="CONTROLSW-eth3" && $10==46 {count[$1]++; if(count[$1]==1) first[$1]=$5; if(count[$1]==2) second[$1]=$5} END {for(r in first) if(r in second) printf "%s %.9f %.9f %.9f\n", r, first[r], second[r], second[r]-first[r]}' type46_events.csv | sort > ttb_raw_low_IOA.txt
```

**Stats for Table 5.4** (core 15 runs):
note: The commands are verbose due to filtering, too easy to include runs that weren't supposed to be processed, therefore a simpler deterministic extraction command was used.

```bash
grep "attack_ryu_fw_001\|attack_ryu_fw_002\|attack_ryu_fw_003\|attack_ryu_fw_004\|attack_ryu_fw_005\|attack_ryu_fw_006\|attack_ryu_fw_007\|attack_ryu_fw_008\|attack_ryu_fw_009\|attack_ryu_fw_010\|attack_ryu_fw_011\|attack_ryu_fw_012\|attack_ryu_fw_013\|attack_ryu_fw_014\|attack_ryu_fw_015" ttb_raw.txt | awk '{print $4}' > ttb_core_fw.txt

awk '{sum+=$1; sumsq+=$1^2; n++; if($1<mn||NR==1)mn=$1; if($1>mx)mx=$1} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "mean=%.3f std=%.3f min=%.3f max=%.3f n=%d\n", mean,std,mn,mx,n}' ttb_core_fw.txt
```

Runs at theoretical minimum (0.500s):

```bash
awk '$1~/^attack_ryu_fw_[0-9]{3}$/ && $4<=0.5009 {n++} END {print n}' ttb_raw.txt
```

**Stats for Table 5.6** (core 15 runs):

```bash
grep -E "^attack_ryu_fw_low_IOA_[0-9]{3} " ttb_raw_low_IOA.txt | awk '{print $4}' > low_IOA_ttb_values.txt

awk '{sum+=$1; sumsq+=$1^2; n++; if($1<min||NR==1)min=$1; if($1>max)max=$1} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "mean=%.3f std=%.3f min=%.3f max=%.3f n=%d\n", mean,std,min,max,n}' low_IOA_ttb_values.txt
```

---

## Tables 5.5 and 5.7: Type ID 46 Gateway Ingress/Egress Counts

Source: `type46_events.csv`

**Table 5.5** — attack_ryu_fw:

```bash
grep "attack_ryu_fw_0" type46_events.csv | awk -F',' '$3~/DSS[0-9]GW-eth/ {print $1,$3}' | sort | uniq -c
```

**Table 5.7** — attack_ryu_fw_low_IOA:

```bash
grep "attack_ryu_fw_low_IOA_0" type46_events.csv | awk -F',' '$3~/DSS[0-9]GW-eth/ {print $1,$3}' | sort | uniq -c
```

---

## Tables 5.8 and 5.9: Polling Gaps and Standby Delays

Source: `type36_frames.csv` and pcaps.

### Polling gaps

Replace `attack_ryu_fw` with `attack_ryu_fw_low_IOA` and output filenames with `low_ioa_gaps_dssN.txt` for Table 5.9. Repeat for DSS2, DSS3, DSS4 by changing the interface name.

```bash
awk -F',' '$2=="attack_ryu_fw" && $3=="DSS1GW-eth2" {run=$1; t=$5+0; if(run in prev) {gap=t-prev[run]; if(!(run in maxgap)||gap>maxgap[run]) maxgap[run]=gap} prev[run]=t} END {for(r in maxgap) print maxgap[r]}' type36_frames.csv | sort > ryu_fw_gaps_dss1.txt

awk '{sum+=$1; sumsq+=$1^2; n++; if($1<mn||NR==1)mn=$1; if($1>mx)mx=$1} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "mean=%.2f std=%.2f min=%.1f max=%.1f\n", mean,std,mn,mx}' ryu_fw_gaps_dss1.txt
```

### Standby delays

Three steps per gateway. Replace `DSS2GW-eth2` → `DSS3GW-eth2` / `DSS4GW-eth2` and output filenames accordingly. For Table 5.9 replace run list and condition name with `attack_ryu_fw_low_IOA`.

**Step 1: SYN timestamps from pcaps:**

```bash
for run in attack_ryu_fw_001 attack_ryu_fw_002 attack_ryu_fw_003 attack_ryu_fw_004 attack_ryu_fw_005 attack_ryu_fw_006 attack_ryu_fw_007 attack_ryu_fw_008 attack_ryu_fw_009 attack_ryu_fw_010 attack_ryu_fw_011 attack_ryu_fw_012 attack_ryu_fw_013 attack_ryu_fw_014 attack_ryu_fw_015; do
    tshark -r ${run}/pcaps/${run}_DSS2GW-eth2.pcapng -Y "tcp.flags.syn==1 && tcp.flags.ack==0 && ip.src==1.1.10.10" -T fields -e frame.time_relative 2>/dev/null | head -1
done | grep -E "^[0-9]" > dss2_syn.txt
```

**Step 2: last Type 36 before gap:**

```bash
awk -F',' '$2=="attack_ryu_fw" && $3=="DSS2GW-eth2" {run=$1; t=$5+0; if(run in prev) {gap=t-prev[run]; if(!(run in maxgap)||gap>maxgap[run]) {maxgap[run]=gap; lastbefore[run]=prev[run]}} prev[run]=t} END {for(r in lastbefore) print r, lastbefore[r]}' type36_frames.csv | sort | awk '{print $2}' > dss2_last36.txt
```

**Step 3: subtract and compute stats:**

```bash
paste dss2_last36.txt dss2_syn.txt | awk '{print $1-$2}' > dss2_standby.txt

awk '{sum+=$1; sumsq+=$1^2; n++; if($1<mn||NR==1)mn=$1; if($1>mx)mx=$1} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "mean=%.2f std=%.2f min=%.2f max=%.2f\n", mean,std,mn,mx}' dss2_standby.txt
```

---

## Tables 5.10 and 5.11: TTB Rate Sensitivity

Source: `ttb_raw.txt` (Table 5.10), `ttb_raw_low_IOA.txt` (Table 5.11)

Same command for both tables —> change the grep pattern to match the interval and swap the input file. The pattern `attack_ryu_fw_500_` matches the 500ms rate sensitivity runs.

**Table 5.10** — multi-RTU multi-IOA, example for 500ms:

```bash
grep "attack_ryu_fw_500_" ttb_raw.txt | awk '{sum+=$4; sumsq+=$4^2; n++; if($4<mn||NR==1)mn=$4; if($4>mx)mx=$4} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "500ms n=%d mean=%.3f std=%.3f min=%.3f max=%.3f\n", n,mean,std,mn,mx}'
```

Intervals: `100`, `500`, `1500`, `3000`. Core 250ms condition uses the explicit run list from Table 5.4.

**Table 5.11**: multi-RTU single-IOA pivot, example for 500ms:

```bash
grep "attack_ryu_fw_low_IOA_500_" ttb_raw_low_IOA.txt | awk '{sum+=$4; sumsq+=$4^2; n++; if($4<mn||NR==1)mn=$4; if($4>mx)mx=$4} END {mean=sum/n; std=sqrt(sumsq/n-mean^2); printf "500ms n=%d mean=%.3f std=%.3f min=%.3f max=%.3f\n", n,mean,std,mn,mx}'
```

Intervals: `50`, `500`, `1500`, `3000`. Core 250ms condition uses the explicit run list from Table 5.6.