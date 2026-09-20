#!/bin/bash
# Regenerate the three families of the WASP2026 dataset.
#
#   nohup bash misc/run_triplets.sh > /tmp/triplets.log 2>&1 &
#
# Order matters: real must finish before gmm, because the gmm fields are sized
# from the angular sizes the real family actually realised.  Contours are
# independent and go last.
#
# WHY EACH STAGE RETRIES
# ----------------------
# mpirun aborts the entire job when any single rank dies, and a rank does
# occasionally segfault inside the plotting stack (twice in the contour stage
# of the 2026-09-20 run, zero times in real and gmm).  The stage then exits 0
# having produced fewer figures than asked for, and a driver that treats "the
# command returned" as "the stage finished" silently moves on -- which is how
# that run ended up at 622/667 contours and went on to gmm regardless.
#
# There is no way to catch SIGSEGV inside the worker, so resilience lives here:
# each stage is re-run until it reaches the target.  That is safe because
# already_have() skips completed figures, so a re-run only fills the gaps.
# A stage that makes NO progress in an attempt is abandoned rather than spun
# on, since that indicates a real failure rather than a crash mid-stride.
set -u

REPO=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-/opt/anaconda3/envs/FullProcess/bin/python}
MPI=${MPI:-/opt/anaconda3/envs/FullProcess/bin/mpirun}

SAVE_DIR=${SAVE_DIR:-~/Downloads/tmp/waspPaper/data/full_dataset/}
SAVE_DIR=$(eval echo "$SAVE_DIR")
N=${N:-667}                 # per family, matching the published dataset
NP=${NP:-6}                 # ranks; memory-bound, 6 was the sweet spot
MAX_ATTEMPTS=${MAX_ATTEMPTS:-8}
# Run at the lowest scheduling priority.  The generator is CPU-bound and will
# happily saturate every core, which makes the machine unpleasant to use; at
# nice 19 it soaks up idle capacity but yields immediately to anything
# interactive, so a long run can share the machine with normal work.
# NICE= (empty) to disable.
NICE=${NICE-19}
NICECMD=""
[ -n "$NICE" ] && NICECMD="nice -n $NICE"
LOG_DIR=${LOG_DIR:-$SAVE_DIR/logs}
mkdir -p "$LOG_DIR"

stamp() { date '+%Y-%m-%d %H:%M:%S'; }

# A figure counts as done only when BOTH its image and its json exist -- that
# is what already_have() tests.  Counting imgs/ alone also counts the jpegs
# written by in-flight layout retries, which reads high by a figure or two.
done_count() { ls "$SAVE_DIR/jsons" 2>/dev/null | grep -c "^Picture_$1"; }

run_family() {   # $1=family  $2=index-block digit  $3...=extra args
    local fam=$1 block=$2; shift 2
    local attempt=1 before after rc
    while :; do
        local have; have=$(done_count "$block")
        if [ "$have" -ge "$N" ]; then
            echo "[$(stamp)] $fam complete: $have/$N"; return 0
        fi
        if [ "$attempt" -gt "$MAX_ATTEMPTS" ]; then
            echo "[$(stamp)] $fam GIVING UP after $MAX_ATTEMPTS attempts at $have/$N"
            return 1
        fi
        echo "[$(stamp)] $fam attempt $attempt: have $have/$N"
        before=$have
        $NICECMD $MPI -np "$NP" "$PY" "$REPO/create_figures_triplets_batch.py" \
            -family "$fam" "$@" \
            -save_dir "$SAVE_DIR" -number_of_figures "$N" \
            -nProcs "$NP" -verbose 1 \
            >> "$LOG_DIR/$fam.log" 2>&1
        rc=$?; after=$(done_count "$block")
        echo "[$(stamp)] $fam attempt $attempt ended rc=$rc: $before -> $after"
        if [ "$after" -le "$before" ]; then
            echo "[$(stamp)] $fam made NO progress -- stopping rather than spinning"
            return 1
        fi
        attempt=$((attempt+1))
    done
}

echo "[$(stamp)] === triplet regeneration ==="
echo "  save_dir  : $SAVE_DIR"
echo "  per family: $N   ranks: $NP   max attempts/stage: $MAX_ATTEMPTS"
echo "  start     : contour $(done_count 0) | gmm $(done_count 1) | real $(done_count 2)"
echo ""

run_family real    2                                   || true
echo ""
run_family gmm     1                                   || true
echo ""
# Contours: only the GMM ones are regenerated, and -contour_dist keeps the
# refilled slots on the distribution they had (all three options carry prob 1,
# so a plain re-run would return only ~1/3 gmm and drift the composition).
# Drop -do_contour/-contour_dist to leave contours copied from a previous run.
run_family contour 0 -do_contour 1 -contour_dist gmm   || true

echo ""
echo "[$(stamp)] === DONE: contour $(done_count 0) | gmm $(done_count 1) | real $(done_count 2) ==="
