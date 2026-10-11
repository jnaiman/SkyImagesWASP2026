"""Rebuild WWT ShowImage links from parsed AVM metadata and predict each image's sky footprint.

Usage: /opt/anaconda3/bin/python3 -I wwt_check.py <real_data_dir> <id> [<id> ...]
WWT convention (wwt-api-client docs): scale = arcsec/pixel, (x, y) = pixel of (ra, dec)
measured from the image's BOTTOM-left corner, rotation = east-of-north + 180.
"""
import json, os, sys, urllib.parse
import numpy as np
from astropy.wcs import WCS
from PIL import Image

root, ids = sys.argv[1], sys.argv[2:]


def fmt_ra(d):
    h = d / 15; return f"{int(h):02d}h{int(h % 1 * 60):02d}m{(h * 60 % 1) * 60:04.1f}s"


def fmt_dec(d):
    s = "-" if d < 0 else "+"; d = abs(d); return f"{s}{int(d):02d}d{int(d % 1 * 60):02d}m{(d * 60 % 1) * 60:02.0f}s"


for iid in ids:
    m = json.load(open(os.path.join(root, "metadata", f"{iid}.json")))
    a = m["avm"]
    ra, dec = map(float, a["Spatial.ReferenceValue"])
    x, y = map(float, a["Spatial.ReferencePixel"])
    scale = float(a["Spatial.Scale"][0])          # arcsec/pixel (matches WWT 'scale')
    rot = float(a["Spatial.Rotation"])
    W, H = Image.open(os.path.join(root, m["image_file"])).size

    url = "http://www.worldwidetelescope.org/wwtweb/ShowImage.aspx?" + urllib.parse.urlencode({
        "scale": scale, "rotation": rot, "ra": ra, "dec": dec, "y": y, "x": x,
        "imageurl": m["hr_url"], "name": m["title"].replace(",", "")[:60]})

    # TAN WCS, FITS pixels (1-based, origin bottom-left), north up / east left, then east-of-north rotation
    pa = np.deg2rad(rot - 180.0)
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [x + 0.5, y + 0.5]
    s = scale / 3600
    w.wcs.cd = [[-s * np.cos(pa), s * np.sin(pa)], [s * np.sin(pa), s * np.cos(pa)]]
    corners = {"top-left": (0.5, H + 0.5), "top-right": (W + 0.5, H + 0.5),
               "bottom-left": (0.5, 0.5), "bottom-right": (W + 0.5, 0.5), "center": (W / 2 + 0.5, H / 2 + 0.5)}

    print(f"### {m['title']}\n- {m['citation']} (doi:{m['doi']})  details: {m['details_url']}")
    print(f"- image {W}x{H} px, scale {scale:.4g}\"/px -> field {W * scale / 60:.3g}' x {H * scale / 60:.3g}'; ref pixel ({x:.0f},{y:.0f}) from bottom-left")
    print(f"- rebuilt link: {url}")
    print(f"- original link identical (params): {all(abs(float(m['wwt'][k]) - v) < 1e-9 for k, v in dict(ra=ra, dec=dec, x=x, y=y, scale=scale, rotation=rot).items())}")
    for k, (px, py) in corners.items():
        r, d = w.all_pix2world([[px, py]], 1)[0]
        print(f"    {k:12s} RA {r:9.4f} ({fmt_ra(r)})  Dec {d:+8.4f} ({fmt_dec(d)})")
    print()
