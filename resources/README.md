# resources/

Static lookup tables read by the figure generator.  They are corpus-derived
artefacts of the ArXiv mining pipeline, not code, so they are **not tracked in
git** — populate this directory with `../fetch_resources.sh`.

| file | size | used by | what it is |
|---|---|---|---|
| `fonts.csv` | 5 KB | every run | system fonts to draw titles/labels with; rows whose `font location` does not exist on this machine are dropped |
| `data/words_cleaned.pickle` | 15 MB | every run | word counts from the historical corpus; `get_popular_nouns` turns them into the pool of nouns used for titles and axis labels |
| `inlines.csv`, `inlines_unique.csv`, `inlines_uniques_ignore.csv` | 3.4 MB | every run | inline-math fragments mined from TeX sources, used when a label is drawn as an equation |
| `object_wavelength_pairs.pickle` | 21 MB | `image of the sky`, `-sky_source astroquery\|both` | (object, wavelength, pdf) triples from the historical corpus — the pool of real targets to query SkyView for |
| `obj_survey_missing_files/` | grows | `image of the sky`, `-sky_source astroquery\|both` | running cache of (object, survey) pairs SkyView has no image for, so they are not re-queried. Written to as runs proceed; under MPI each rank writes its own timestamped csv shard and all shards are read back together |

Resolution order for this directory:

1. `-resources_dir` on the command line
2. `$SKYFIGS_RESOURCES`
3. this directory

See `skyfigs/paths.py`.

Downloaded SkyView `.fits` cutouts are cached separately, under
`-astroquery_img_dir` (`$SKYFIGS_ASTROQUERY_IMAGES`), not here.
