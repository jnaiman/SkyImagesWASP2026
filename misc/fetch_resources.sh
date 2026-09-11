#!/usr/bin/env bash
# Populate resources/ with the static lookup tables the figure generator reads.
#
# The tables ARE tracked in git, so a fresh clone already has them and does not
# need to run this.  Use it to re-sync when the upstream tables are regenerated.
# By default they are copied from a local checkout of ArXiv_figure_injection;
# point SRC elsewhere (or rsync from the cluster) if yours lives somewhere else.
#
#   misc/fetch_resources.sh                      # copy from ~/ArXiv_figure_injection/resources
#   misc/fetch_resources.sh /path/to/resources   # copy from somewhere else
#   misc/fetch_resources.sh /path/to/resources link   # symlink instead of copy
set -euo pipefail

SRC="${1:-$HOME/ArXiv_figure_injection/resources}"
MODE="${2:-copy}"
# repo root is one level up from misc/, wherever this script is called from
DST="$(cd "$(dirname "$0")/.." && pwd)/resources"

if [ ! -d "$SRC" ]; then
    echo "source resources dir not found: $SRC" >&2
    exit 1
fi
mkdir -p "$DST" "$DST/data"

# required by every run
FILES=(
    "fonts.csv"                        # fonts to draw labels with
    "data/words_cleaned.pickle"        # word counts -> "popular nouns"
    "inlines.csv"                      # inline-math fragments
    "inlines_unique.csv"
    "inlines_uniques_ignore.csv"
)
# required only by "image of the sky" with -sky_source astroquery|both
SKY_FILES=(
    "object_wavelength_pairs.pickle"   # (object, wavelength, pdf) from the corpus
)

place () {
    local rel="$1"
    if [ ! -e "$SRC/$rel" ]; then
        echo "  MISSING in source: $rel" >&2
        return
    fi
    if [ "$MODE" = "link" ]; then
        ln -sf "$SRC/$rel" "$DST/$rel"
        echo "  linked  $rel"
    else
        cp "$SRC/$rel" "$DST/$rel"
        echo "  copied  $rel"
    fi
}

echo "resources: $SRC -> $DST ($MODE)"
for f in "${FILES[@]}" "${SKY_FILES[@]}"; do place "$f"; done

# Cache of (object, survey) pairs SkyView has no image for: tens of thousands of
# per-rank csv shards, appended to as runs proceed.  This repo keeps its own
# copy so it is self-contained; MODE=link shares one cache between checkouts
# instead.
# drop a symlink left by an older run (but never an existing real directory)
if [ -L "$DST/obj_survey_missing_files" ]; then
    rm -f "$DST/obj_survey_missing_files"
fi
if [ -d "$SRC/obj_survey_missing_files" ]; then
    if [ "$MODE" = "link" ]; then
        ln -sfn "$SRC/obj_survey_missing_files" "$DST/obj_survey_missing_files"
        echo "  linked  obj_survey_missing_files/"
    else
        mkdir -p "$DST/obj_survey_missing_files"
        # -a so a re-run only moves shards that are new or changed
        rsync -a --delete "$SRC/obj_survey_missing_files/" "$DST/obj_survey_missing_files/"
        echo "  copied  obj_survey_missing_files/ ($(ls -1 "$DST/obj_survey_missing_files" | wc -l | tr -d ' ') files)"
    fi
else
    mkdir -p "$DST/obj_survey_missing_files"
    echo "  created empty obj_survey_missing_files/ (will be filled as you run)"
fi

echo "done."
