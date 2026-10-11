"""Flag AstroExplorer images whose embedded astrometry is probably wrong or not useful.

Usage: /opt/anaconda3/bin/python3 -I astrometry_check.py <real_data_dir>
Writes an "astrometry_check" block (incl. "marginal_correctness") into metadata/<id>.json,
adds columns to index.csv, and writes astrometry_check.csv.
"""
import csv, glob, json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
from PIL import Image

root = sys.argv[1]

# Target(s) named in each title (by title prefix) -> SIMBAD-resolvable names; None = no single target.
TARGETS = {
    "Properties of the Monoceros R2": ["Mon R2"],
    "Structural Components of NGC 5850": ["NGC 5850"],
    "NGC 5291": ["NGC 5291"],
    "E 0336-248": ["PKS 0336-248", "E 0336-248", "1ES 0336-248"],
    "The Interstellar Environment of Filled-Center Supernova II. G63.7+1.1": ["SNR G063.7+01.1"],
    "1420 MHz Continuum and Polarization Observations of the Cygnus Loop": ["Cygnus Loop"],
    "A comparison of high-resolution radio and optical data for the northeast region of the Cygnus Loop": ["Cygnus Loop"],
    "Kinematics and Evolution of the Giant HH34": ["HH 34"],
    "Evidence for a wind-swept cavity in HH 34": ["HH 34"],
    "LYNDS 1527": ["LDN 1527"],
    "Aperture Synthesis 13CO (J = 1-0) Observations of the Molecular Gas around DG Tauri": ["DG Tau"],
    "A study of the stellar population in the LYNDS 1641": ["LDN 1641"],
    "H I studies of the Sculptor group galaxies. VI - NGC 300": ["NGC 300"],
    "The distribution and kinematics of H I in the active elliptical galaxy NGC 1052": ["NGC 1052"],
    "Evidence for the interaction of the IRS 16 wind": ["Sgr A*"],
    "On the Distribution of Dust in the Large Magellanic Cloud": ["LMC"],
    "Observations of the Ocular Galaxy NGC 2535": ["NGC 2535", "NGC 2536"],
    "Star formation in the NGC 7129 region": ["NGC 7129"],
    "A High-Resolution ROSAT X-Ray Study of the Hercules Cluster": ["ACO 2151"],
    "Radio images of the bipolar H II region S106": ["Sh2-106"],
    "The distribution of molecular and neutral gas and magnetic fields near the bipolar H II region S106": ["Sh2-106"],
    ",Anatomy of a region of star formation - Infrared images of S106": ["Sh2-106"],
    "The Starburst Nuclear Region in M82": ["M82"],
    "H I streamers around M82": ["M82"],
    "Neutral Hydrogen in the Ringed Barred Galaxies NGC 1433 and NGC 6300": ["NGC 1433", "NGC 6300"],
    "A large area CO (J = 2 goes to 1) mapping of the giant molecular clouds in Orion": ["M42"],
    "Filamentary structure in the Orion molecular cloud": ["M42"],
    "NH3 observations of the AFGL 2591": ["AFGL 2591"],
    "The magnetic structure of the filaments in the supernova remnant IC 443": ["IC 443"],
    "A comprehensive study of the X-ray structure and spectrum of IC 443": ["IC 443"],
    "A multiwavelength investigation of the supernova remnant IC 443": ["IC 443"],
    "The nature of the compact X-ray source in the supernova remnant G27.4+0.0": ["Kes 73"],
    "Polarized radio emission from the edge-on spiral galaxies NGC 891 and NGC 4565": ["NGC 891", "NGC 4565"],
    "Near-Infrared and Very High Sensitivity VLA 2 Centimeter Continuum Observations of the H II Region G29.96-0.02": ["G29.96-0.02", "W43S"],
    "Radio continuum and radio recombination line observations of Sagittarius B1": ["Sgr B1"],
    "Radio continuum and radio recombination line observations of Sagittarius B2": ["Sgr B2"],
    "Radio continuum and radio recombination line observations of W51": ["W51"],
    "H I absorption measurements over the Galactic center Radio Arc": ["Sgr A*"],
    "H110 alpha observations of Sagittarius A West": ["Sgr A*"],
    "Velocity field of the Orion-KL": ["Orion KL"],
    "A Multiline Aperture Synthesis Study of Orion-KL": ["Orion KL"],
    "A Burst of Herbig-Haro Flows in NGC 1333": ["NGC 1333"],
    "At the low-mass end - Light and H I distribution of GR 8": ["DDO 155"],
    "Far-infrared line and continuum observations of G0.095 + 0.012": ["Sgr A*"],
    "Twin Herbig-Haro Jets and Molecular Outflows in L1228": ["LDN 1228"],
    "Neutral gas in the central 2 parsecs of the Galaxy": ["Sgr A*"],
    "Southern galaxies. VIII - Surface photometry of the SD spiral NGC 7793": ["NGC 7793"],
    "Unusual Radio Structures in the Cooling Flow Cluster 2A 0335+096": ["2A 0335+096"],
    "The Supernova Remnant RCW 103": ["RCW 103"],
    "Does the Crab Have a Shell?": ["M1"],
    "A ROSAT observation of the supernova remnant Kes 79": ["Kes 79"],
    "Ultraviolet-illuminated molecular cloud boundaries": ["LDN 1630"],
    "Observations of individual star-forming regions in the nucleus of M33": ["M33"],
    "The infrared structure of M33": ["M33"],
    "The near-infrared structure of M33": ["M33"],
    "The Central Star Cluster of the Star-forming Dwarf Galaxy NGC 5253": ["NGC 5253"],
    "Dust and Molecular Gas in the Barred Spiral Galaxy NGC 1530": ["NGC 1530"],
    "Infrared observations of dust cloud structure in young R associations": ["NGC 1333", "NGC 7129", "Sh2-68"],
    "Highly blueshifted H I gas toward the Galactic center": ["Sgr A*"],
    "NGC 6946": ["NGC 6946"],
    "Radio observations of M83": ["M83"],
    "A spectroscopic study of the DR 21": ["DR 21"],
    "Multifrequency VLA observations of the prototypical narrow-angle tail radio source NGC 1265": ["NGC 1265"],
    "The Arc and other structures in the Center of M81": ["M81"],
    "A far-infrared survey of the galactic center": ["Sgr A*"],
    "ROSAT PSPC Observation of the Supernova Remnant 3C 391": ["3C 391"],
    "The Interaction between Spiral Galaxies IC 2163 and NGC 2207": ["NGC 2207", "IC 2163"],
    "Star Formation in the Gemini OB1": ["Gem OB1"],
    "Optical and H I studies of the 'gas-rich' dwarf irregular galaxy DDO 154": ["DDO 154"],
    "Star Formation in the Spiral Arms of NGC 4321": ["M100"],
    "Bubbles and jets in the center of M51": ["M51"],
    "The Hot Gaseous Halo of the Spiral Galaxy NGC 3628": ["NGC 3628"],
    "The Structure and Properties of an Intermediate-Velocity Cloud in the Direction of the Globular Cluster M13": ["M13"],
    "The Molecular Core Associated with HH 25-26": ["HH 25"],
    "Cometary globules in the southeast quadrant of the Rosette nebula": ["NGC 2244"],
    "Giant molecular complexes and OB associations. I - The Rosette molecular complex": ["NGC 2244"],
    "Molecular Gas Disk in the Flocculent Spiral Galaxy NGC 4414": ["NGC 4414"],
    "The detection of molecular gas in the ring galaxy ARP 143": ["Arp 143"],
    "VRO 42.05.01": ["VRO 42.05.01"],
    "Counterrotating gaseous disks in NGC 4826": ["M64"],
    "4C 29.47": ["4C 29.47"],
    "VLA OH Observations of High Negative Velocity Gas toward Sagittarius A West": ["Sgr A*"],
    "Molecular Gasdynamics of the Young Nuclear Starburst in the Barred Galaxy NGC 3504": ["NGC 3504"],
    "Radio observations of the remnant of the supernova of AD 1006": ["SN 1006"],
    "A spatially resolved photodissociation region in the planetary nebula NGC 7027": ["NGC 7027"],
    "Soft X-ray observations of the interacting galaxies NGC 1808 and NGC 1792": ["NGC 1808", "NGC 1792"],
    "Einstein observations of NGC 4438": ["NGC 4438"],
    "Cold, warm, and hot gas in the late-stage merger NGC 7252": ["NGC 7252"],
    "Spiral Structure Based Limits on the Disk Mass of the Low Surface Brightness Galaxies UGC 6614 and F568-6": ["UGC 6614", "[SB96] F568-6", "F568-6"],
    "A Multiwavelength Study of 30 Doradus": ["30 Dor"],
    "Star Formation in the NGC 2024 Molecular Ridge": ["NGC 2024"],
    "Neutral hydrogen in the interacting pair NGC 4725/NGC 4747": ["NGC 4725", "NGC 4747"],
    "H I studies of the Sculptor group galaxies. IV - NGC 247": ["NGC 247"],
    "VLA Zeeman observations of W3": ["W3"],
    "H I and mass distribution in the dwarf 'regular' galaxy UGC 2259": ["UGC 2259"],
    "Infrared and millimeter-wave observations of the Sharpless 156": ["Sh2-156"],
    "NGC 4314. III.": ["NGC 4314"],
}

_cache = {}


def resolve(name):
    if name not in _cache:
        url = "https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?" + urllib.parse.quote(name)
        xml = urllib.request.urlopen(url, timeout=30).read().decode()
        ra, de = re.search(r"<jradeg>([^<]+)", xml), re.search(r"<jdedeg>([^<]+)", xml)
        _cache[name] = (float(ra.group(1)), float(de.group(1))) if ra and de else None
        time.sleep(0.2)
    return _cache[name]


def is_round(ra, dec):
    """Coordinates that sit exactly on a round sexagesimal value (likely typed in by hand)."""
    ra_s, dec_s = ra * 240.0, dec * 3600.0     # RA in seconds of time, Dec in arcsec
    return abs(ra_s * 2 - round(ra_s * 2)) < 1e-4 and abs(dec_s - round(dec_s)) < 1e-3


files = sorted(glob.glob(os.path.join(root, "metadata", "*.json")))
metas = [json.load(open(f)) for f in files]
coord_counts = Counter((round(float(m["wwt"]["ra"]), 5), round(float(m["wwt"]["dec"]), 5)) for m in metas)
dois_by_coord = {}
for m in metas:
    dois_by_coord.setdefault((round(float(m["wwt"]["ra"]), 5), round(float(m["wwt"]["dec"]), 5)), set()).add(m["doi"])

out_rows = []
for f, m in zip(files, metas):
    a = m["avm"]
    ra, dec = map(float, a["Spatial.ReferenceValue"])
    x, y = map(float, a["Spatial.ReferencePixel"])
    scale = float(a["Spatial.Scale"][0])                       # arcsec/px
    W, H = Image.open(os.path.join(root, m["image_file"])).size
    fw, fh = W * scale / 3600, H * scale / 3600                # field size, deg
    # sky position of the image center (north up, east left, TAN ~ flat for small fields)
    cx, cy = W / 2 - x, H / 2 - y
    center = SkyCoord(ra * u.deg, dec * u.deg).spherical_offsets_by(-cx * scale * u.arcsec, cy * scale * u.arcsec) \
        if max(fw, fh) < 30 else SkyCoord(ra * u.deg, dec * u.deg)
    half_diag = 0.5 * np.hypot(fw, fh)

    reasons, notes = [], []
    names = next((v for k, v in TARGETS.items() if m["title"].startswith(k)), None)
    target, sep = None, None
    if names:
        for n in names:
            try:
                pos = resolve(n)
            except Exception:
                pos = None
            if pos is None:
                continue
            s = center.separation(SkyCoord(pos[0] * u.deg, pos[1] * u.deg)).deg
            if sep is None or s < sep:
                target, sep = n, s
        if target is None:
            notes.append(f"title target(s) {names} not resolved by Sesame")
        # extended targets (e.g. Cygnus Loop, Orion) can sit off-field; allow half-diag + max(2 deg, field diag)
        elif sep > half_diag + max(2.0, 2 * half_diag):
            reasons.append(f"title target {target} is {sep:.2f} deg from image center (field half-diagonal {half_diag:.3f} deg)")
        elif sep > half_diag + 0.25:
            notes.append(f"title target {target} lies {sep:.2f} deg from center, just outside field")
    else:
        notes.append("no single named target in title; position not checked")

    if max(fw, fh) * 3600 < 10:
        notes.append(f"field only {max(fw, fh) * 3600:.1f} arcsec across (very small; check scale)")
    if max(fw, fh) > 90:
        reasons.append(f"field {max(fw, fh):.0f} deg across: coordinates may be right, but a single TAN-projected mapping is not useful at this size")
    elif max(fw, fh) > 30:
        notes.append(f"wide field ({max(fw, fh):.0f} deg across); TAN mapping may distort toward the edges")
    if is_round(ra, dec):
        notes.append("reference coordinates fall on a round sexagesimal value (possibly hand-entered)")
    key = (round(ra, 5), round(dec, 5))
    own_target_ok = target is not None and sep <= half_diag + max(2.0, 2 * half_diag)
    if coord_counts[key] > 1 and len(dois_by_coord[key]) > 1 and not own_target_ok:
        reasons.append(f"identical reference coordinates shared with figures from {len(dois_by_coord[key]) - 1} other article(s)")
    elif coord_counts[key] > 1 and len(dois_by_coord[key]) > 1:
        notes.append("identical reference coordinates shared with another article, but this figure matches its own title target")
    elif coord_counts[key] > 1:
        notes.append(f"reference coordinates shared with {coord_counts[key] - 1} other figure(s) from the same article")

    check = {
        "marginal_correctness": bool(reasons),
        "reasons": reasons,
        "notes": notes,
        "title_target": target,
        "title_target_sep_deg": None if sep is None else round(sep, 4),
        "image_center_radec_deg": [round(center.ra.deg, 6), round(center.dec.deg, 6)],
        "field_deg": [round(fw, 5), round(fh, 5)],
        "image_size_px": [W, H],
        "method": "automated (astrometry_check.py): Sesame position of title target vs image footprint; field-size and duplicate-coordinate checks",
    }
    m["astrometry_check"] = check
    json.dump(m, open(f, "w"), indent=1)
    out_rows.append({"id": m["id"], "title": m["title"], "marginal_correctness": check["marginal_correctness"],
                     "title_target": target, "sep_deg": check["title_target_sep_deg"],
                     "field_w_deg": round(fw, 5), "field_h_deg": round(fh, 5),
                     "reasons": " | ".join(reasons), "notes": " | ".join(notes)})

with open(os.path.join(root, "astrometry_check.csv"), "w", newline="") as fh_:
    w = csv.DictWriter(fh_, fieldnames=list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)

# add the flag to index.csv
idx_path = os.path.join(root, "index.csv")
idx = list(csv.DictReader(open(idx_path)))
flag = {r["id"]: r for r in out_rows}
for r in idx:
    r["marginal_correctness"] = flag[r["id"]]["marginal_correctness"]
    r["astrometry_reasons"] = flag[r["id"]]["reasons"]
with open(idx_path, "w", newline="") as fh_:
    w = csv.DictWriter(fh_, fieldnames=list(idx[0].keys())); w.writeheader(); w.writerows(idx)

n_flag = sum(r["marginal_correctness"] for r in out_rows)
print(f"flagged {n_flag} / {len(out_rows)}; unchecked position (no target): {sum(r['title_target'] is None for r in out_rows)}")
for r in out_rows:
    if r["marginal_correctness"]:
        print("FLAG", r["id"][25:33], r["title"][:60], "::", r["reasons"])
for r in out_rows:
    if not r["marginal_correctness"] and r["notes"] and "no single" not in r["notes"]:
        print("note", r["id"][25:33], r["title"][:60], "::", r["notes"])
