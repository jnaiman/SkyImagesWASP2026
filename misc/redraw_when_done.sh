#!/usr/bin/env bash
# Wait for the test5_big generation to finish, then rebuild its diagnostics.
#
# The diagnostic overlays written during the run used the pre-fix
# add_annotations, whose visible-region filter had nx/ny swapped -- which only
# mattered once sky images stopped being square.  jsons/ and imgs/ are unaffected,
# so the overlays just need redrawing from the jsons afterwards.
set -u
OUT=${OUT:-$HOME/Downloads/tmp/test5_big}
PY=/opt/anaconda3/envs/FullProcess/bin/python
LOG="$OUT/redraw_diagnostics.log"

cd /Users/jnaiman/SkyImagesWASP2026

echo "[$(date '+%F %T')] waiting for generation to finish..." | tee -a "$LOG"
while pgrep -f run_test5_big.sh > /dev/null; do sleep 60; done
# let any in-flight mpirun children drain
while pgrep -f create_figures_batch > /dev/null; do sleep 30; done

echo "[$(date '+%F %T')] generation finished; rebuilding diagnostics" | tee -a "$LOG"
"$PY" misc/redraw_diagnostics.py "$OUT" --procs 6 >> "$LOG" 2>&1
echo "[$(date '+%F %T')] diagnostics rebuilt (exit $?)" | tee -a "$LOG"
