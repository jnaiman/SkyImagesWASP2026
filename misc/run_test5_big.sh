#!/usr/bin/env bash
# Long-running generation for test5_big.
#
#   Phase 1: reach TARGET (default 500) figures of each of the three kinds.
#   Phase 2: keep going, adding CHUNK (default 50) more of each kind per round,
#            until MAX_PER_TYPE (default 1000, i.e. 3000 total) is reached.
#
# Types are interleaved in rounds rather than run back to back, so the three
# counts stay level -- stop it at any point and you have a balanced set.
#
# Each type owns a disjoint index block, so a figure that gives up leaves a gap
# only in its own block and is retried on the next round; the composition can
# never drift between types.
#
#   contour    Picture_000001 +     (start_index 0)
#   sky / GMM  Picture_100001 +     (start_index 100000)
#   sky / real Picture_200001 +     (start_index 200000)
#
# Resumable: re-running picks up exactly where it left off.
# Stop with:  pkill -f run_test5_big.sh ; pkill -f create_figures_batch
set -u

cd /Users/jnaiman/SkyImagesWASP2026
OUT=${OUT:-$HOME/Downloads/tmp/test5_big}
PY=/opt/anaconda3/envs/FullProcess/bin/python
MPI=/opt/anaconda3/envs/FullProcess/bin/mpirun

TARGET=${TARGET:-500}          # phase 1 goal, per type
CHUNK=${CHUNK:-50}             # added per type per round
MAX_PER_TYPE=${MAX_PER_TYPE:-1000}   # hard stop: 1000/type = 3000 total
BLOCK=100000              # index slots reserved per type
NP_CPU=${NP_CPU:-6}       # ranks for the cpu-bound types
NP_NET=${NP_NET:-8}       # ranks for real sky: network-latency bound, so more
                          # concurrency helps and costs little cpu

mkdir -p "$OUT" "$OUT/logs"
LOG="$OUT/run_progress.log"

stamp () { date '+%Y-%m-%d %H:%M:%S'; }
say ()   { echo "[$(stamp)] $*" | tee -a "$LOG"; }

# how many figures are finished inside one type's index block
count_done () {
  "$PY" - "$OUT" "$1" "$BLOCK" <<'EOF'
import sys, os, glob
out, start, block = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
n = 0
for f in glob.glob(os.path.join(out, 'jsons', 'Picture_*.json')):
    try:
        i = int(os.path.basename(f)[8:-5])      # Picture_NNNNNN.json
    except ValueError:
        continue
    if start < i <= start + block:              # start_index S -> Picture_(S+1)..
        n += 1
print(n)
EOF
}

# run one type up to `done + CHUNK` (capped at the current target)
run_type () {
  local label=$1 start=$2 np=$3; shift 3
  local done n rc
  done=$(count_done "$start")
  if [ "$done" -ge "$TARGET" ]; then return 0; fi
  n=$(( done + CHUNK ))
  [ "$n" -gt "$TARGET" ] && n=$TARGET

  for attempt in 1 2 3; do
    "$MPI" -np "$np" "$PY" -u single/create_figures_batch.py \
        -save_dir "$OUT/" -start_index "$start" -number_of_figures "$n" \
        -nProcs "$np" -max_resets 5 "$@" >> "$OUT/logs/$label.log" 2>&1
    rc=$?
    [ $rc -eq 0 ] && break
    # a matplotlib segfault kills the process outright; finished figures are
    # kept, so just resume
    say "  $label exited $rc (attempt $attempt) - resuming"
  done
  say "  $label: $(count_done "$start")/$TARGET"
}

say "=== start: target ${TARGET}/type, chunks of ${CHUNK}, out=$OUT ==="

while true; do
  run_type contour    0      "$NP_CPU" -plot_types "contour"
  run_type sky_gmm    100000 "$NP_CPU" -plot_types "image of the sky" -sky_source gmm
  run_type sky_real   200000 "$NP_NET" -plot_types "image of the sky" -sky_source astroquery

  c=$(count_done 0); g=$(count_done 100000); r=$(count_done 200000)
  say "ROUND DONE  contour=$c  sky_gmm=$g  sky_real=$r  total=$((c+g+r))  (target $TARGET/type)"

  # everyone reached the target -> phase 2, ask for CHUNK more of each
  if [ "$c" -ge "$TARGET" ] && [ "$g" -ge "$TARGET" ] && [ "$r" -ge "$TARGET" ]; then
    if [ "$TARGET" -ge "$MAX_PER_TYPE" ]; then
      say "=== ALL DONE: ${c}+${g}+${r} = $((c+g+r)) figures (${MAX_PER_TYPE}/type) ==="
      exit 0
    fi
    TARGET=$(( TARGET + CHUNK ))
    [ "$TARGET" -gt "$MAX_PER_TYPE" ] && TARGET=$MAX_PER_TYPE
    say "*** all types reached target; continuing to ${TARGET}/type ***"
  fi
done
