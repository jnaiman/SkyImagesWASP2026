#!/bin/bash
# Regenerate the two SKY families of the WASP2026 dataset, in the order they
# have to run: real first, then gmm (whose field sizes are drawn from what the
# real family actually produced).  Contours are copied beforehand, not
# generated -- see misc/copy_contours_to_triplets.py.
#
#   nohup bash misc/run_triplets.sh > /tmp/triplets.log 2>&1 &
#
# Re-running is safe: figures already on disk are skipped, so an interrupted
# run resumes where it stopped.

set -u

REPO=$(cd "$(dirname "$0")/.." && pwd)
PY=/opt/anaconda3/envs/FullProcess/bin/python
MPI=/opt/anaconda3/envs/FullProcess/bin/mpirun

SAVE_DIR=${SAVE_DIR:-~/Downloads/tmp/waspPaper/data/full_dataset/}
SAVE_DIR=$(eval echo "$SAVE_DIR")
N=${N:-667}                 # per family, matching the published dataset
NP=${NP:-6}                 # ranks; memory-bound, 6 was the sweet spot before
LOG_DIR=${LOG_DIR:-$SAVE_DIR/logs}
mkdir -p "$LOG_DIR"

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
progress() {   # family-block prefix -> how many figures exist
  ls "$SAVE_DIR/imgs" 2>/dev/null | grep -c "^Picture_$1"
}

echo "[$(stamp)] === triplet regeneration ==="
echo "  save_dir : $SAVE_DIR"
echo "  per family: $N   ranks: $NP"
echo "  contours already present: $(progress 0)"
echo ""

for FAMILY in real gmm; do
    case $FAMILY in
        real) BLOCK=2 ;;
        gmm)  BLOCK=1 ;;
    esac
    echo "[$(stamp)] --- $FAMILY: have $(progress $BLOCK) of $N ---"
    $MPI -np "$NP" "$PY" "$REPO/create_figures_triplets_batch.py" \
        -family "$FAMILY" \
        -save_dir "$SAVE_DIR" \
        -number_of_figures "$N" \
        -nProcs "$NP" \
        -verbose 1 \
        >> "$LOG_DIR/$FAMILY.log" 2>&1
    echo "[$(stamp)] --- $FAMILY finished: $(progress $BLOCK) of $N (exit $?) ---"
    echo ""
done

echo "[$(stamp)] === DONE ==="
echo "  contour $(progress 0) | gmm $(progress 1) | real $(progress 2)"
