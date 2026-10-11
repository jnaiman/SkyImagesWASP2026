"""Download AstroExplorer 'Images with astrometry' (163) hi-res JPEGs + metadata.

Usage: python3 -I ae_download.py <ids.txt> <out_dir>
"""
import csv, html, json, os, re, sys, time, urllib.parse, urllib.request

BASE = "https://www.astroexplorer.org"
ids_file, out = sys.argv[1], sys.argv[2]
img_dir, meta_dir, raw_dir = (os.path.join(out, d) for d in ("images", "metadata", "details_html"))
for d in (img_dir, meta_dir, raw_dir):
    os.makedirs(d, exist_ok=True)


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def text(pattern, s):
    m = re.search(pattern, s, re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", m.group(1)))).strip() if m else None


def parse_avm(jpeg):
    """Pull avm:* fields out of the embedded XMP packet (Seq/Bag values become lists)."""
    m = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", jpeg, re.S)
    if not m:
        return None, None
    xmp = m.group(0).decode("utf-8", "replace")
    avm = {}
    for tag, body in re.findall(r"<avm:([\w.]+)>(.*?)</avm:\1>", xmp, re.S):
        items = re.findall(r"<rdf:li[^>]*>(.*?)</rdf:li>", body, re.S)
        avm[tag] = [html.unescape(i.strip()) for i in items] if items else html.unescape(body.strip())
    return avm, xmp


ids = [l.strip() for l in open(ids_file) if l.strip()]
rows, failures = [], []
for n, iid in enumerate(ids, 1):
    try:
        page = get(f"{BASE}/rest/details/{iid}").decode("utf-8", "replace")
        open(os.path.join(raw_dir, f"{iid}.html"), "w").write(page)

        hr = re.search(r'id="hi-resolution-link"', page) and re.search(r'href="([^"]+_hr\.[a-z]+)"', page).group(1)
        wwt = re.search(r'href="(http://www\.worldwidetelescope\.org/[^"]+)"', page)
        wwt_params = {}
        if wwt:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(html.unescape(wwt.group(1))).query)
            wwt_params = {k: v[0] for k, v in q.items() if k != "imageurl"}
        doi = re.search(r'id="article-link"[^>]*href="[^"]*?doi:([^"]+)"|href="[^"]*?doi:([^"]+)"[^>]*id="article-link"', page)
        ads = re.search(r'href="(https?://articles\.adsabs\.harvard\.edu/[^"]+)"', page)

        img_name = os.path.basename(urllib.parse.urlparse(hr).path)
        img_path = os.path.join(img_dir, img_name)
        if not os.path.exists(img_path):
            data = get(hr)
            open(img_path, "wb").write(data)
        data = open(img_path, "rb").read()
        avm, xmp = parse_avm(data)
        if xmp:
            open(os.path.join(meta_dir, f"{iid}.xmp"), "w").write(xmp)

        meta = {
            "id": iid,
            "details_url": f"{BASE}/details/{iid}",
            "image_file": f"images/{img_name}",
            "hr_url": hr,
            "title": text(r'id="imageTitle">(.*?)</div>', page),
            "authors": text(r'id="image-authors">(.*?)</li>', page),
            "citation": text(r'id="image-citation">(.*?)</p>', page),
            "figure": text(r'id="image-figure">(.*?)</div>', page),
            "caption": text(r'id="image-caption">(.*?)</div>\s*</div>', page),
            "copyright": text(r'id="image_copyright">(.*?)</p>', page),
            "doi": (doi.group(1) or doi.group(2)) if doi else None,
            "ads_url": ads.group(1) if ads else None,
            "wwt": wwt_params,
            "avm": avm,
        }
        json.dump(meta, open(os.path.join(meta_dir, f"{iid}.json"), "w"), indent=1)
        a = avm or {}
        rows.append({
            "id": iid, "image_file": meta["image_file"], "title": meta["title"], "citation": meta["citation"],
            "doi": meta["doi"], "has_avm": bool(avm),
            "coord_frame": a.get("Spatial.CoordinateFrame"), "equinox": a.get("Spatial.Equinox"),
            "projection": a.get("Spatial.CoordsystemProjection"), "quality": a.get("Spatial.Quality"),
            "ref_value": json.dumps(a.get("Spatial.ReferenceValue")), "ref_pixel": json.dumps(a.get("Spatial.ReferencePixel")),
            "ref_dimension": json.dumps(a.get("Spatial.ReferenceDimension")), "scale": json.dumps(a.get("Spatial.Scale")),
            "rotation": a.get("Spatial.Rotation"),
            "wwt_ra": wwt_params.get("ra"), "wwt_dec": wwt_params.get("dec"), "wwt_scale": wwt_params.get("scale"),
        })
        print(f"[{n}/{len(ids)}] ok {iid} avm={bool(avm)}", flush=True)
    except Exception as e:
        failures.append((iid, repr(e)))
        print(f"[{n}/{len(ids)}] FAIL {iid}: {e!r}", flush=True)
    time.sleep(0.3)

with open(os.path.join(out, "index.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
if failures:
    json.dump(failures, open(os.path.join(out, "failures.json"), "w"), indent=1)
print(f"done: {len(rows)} ok, {len(failures)} failed")
