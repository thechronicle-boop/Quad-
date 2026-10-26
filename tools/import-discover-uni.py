#!/usr/bin/env python3
"""
Quad — Discover Uni importer.

Reads the official Discover Uni dataset (CSV version, from HESA / Office for Students)
and writes the official course data Quad uses into data/discover-uni.json.

Usage:
  python3 tools/import-discover-uni.py path/to/DiscoverUni.zip   (or an unzipped folder)
  python3 tools/import-discover-uni.py                            (uses the newest zip in source/)

Then run:  node tools/build-data.mjs
"""
import csv, io, json, os, re, statistics, sys, zipfile, glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- uni IDs (PUBUKPRN)
UNI_IDS = json.load(open(os.path.join(HERE, "uni-ids.json")))

# ---------------------------------------------------------------- course matching
# Each Quad course is matched by the official course TITLE (any full-time first degree whose title matches).
COURSE_RX = {
 "MED": r"\bmedicine\b(?!.*(veterinar|sport|complementary|herbal))|\bmbchb\b|\bmbbs\b|\bbm\s?bs\b",
 "DEN": r"\bdental surgery\b|\bdentistry\b|\bbds\b",
 "VET": r"\bveterinary (medicine|science|surgery)\b|\bbvsc\b|\bbvms\b|\bbvetmed\b",
 "NUR": r"nursing.*adult|adult nursing|registered nurse.*adult",
 "NCH": r"nursing.*child|child(ren)?'?s? nursing|registered nurse.*child",
 "NMH": r"nursing.*mental health|mental health nursing|registered nurse.*mental",
 "MID": r"\bmidwifery\b",
 "PAR": r"\bparamedic",
 "PHY": r"\bphysiotherapy\b",
 "OT":  r"\boccupational therapy\b",
 "RAD": r"diagnostic radiography|\bradiography\b",
 "ODP": r"operating department practice",
 "SLT": r"speech (and|&) language (therapy|science|pathology)|speech and language sciences",
 "NUT": r"\bdietetics\b|\bnutrition\b",
 "PHA": r"^pharmacy|\bmpharm\b|\bpharmacy\b",
 "BMS": r"biomedical science",
 "PSY": r"\bpsychology\b",
 "NEU": r"\bneuroscience\b",
 "BIO": r"^biology|\bbiological sciences?\b|^biology\b|\bbiology\b",
 "BCH": r"\bbiochemistry\b",
 "CHE": r"^chemistry\b|\bchemistry\b(?!.*(bio))",
 "PHS": r"\bphysics\b|\bastrophysics\b",
 "MAT": r"\bmathematics\b|\bmaths\b|\bmathematical\b",
 "ENV": r"environmental science",
 "GEO": r"\bgeography\b",
 "ZOO": r"\bzoology\b",
 "FOR": r"forensic science",
 "CS":  r"computer science",
 "SE":  r"software engineering|software development",
 "DS":  r"\bdata science\b",
 "AI":  r"artificial intelligence",
 "CYB": r"cyber ?security",
 "ENG": r"\bengineering\b",
 "MEC": r"mechanical engineering",
 "ELE": r"electrical|electronic engineering|electronics",
 "CIV": r"civil engineering",
 "AER": r"aerospace|aeronautical",
 "CHM": r"chemical engineering",
 "BEN": r"biomedical engineering",
 "ARC": r"^architecture|\barchitecture\b(?!.*landscape)|\barchitectural studies\b",
 "BUS": r"\bbusiness\b|\bmanagement\b",
 "ACC": r"\baccounting\b|\bfinance\b",
 "ECO": r"\beconomics\b",
 "MKT": r"\bmarketing\b",
 "LAW": r"^law\b|\blaw\b|\bllb\b",
 "CRI": r"\bcriminology\b",
 "POL": r"\bpolitics\b",
 "IR":  r"international relations",
 "TOU": r"\btourism\b|\bevents?( management)?\b",
 "EN":  r"english literature|^english\b|\benglish\b(?!.*(language teaching|as a foreign))",
 "HIS": r"\bhistory\b(?!.*\bart\b)",
 "PHI": r"\bphilosophy\b",
 "CLA": r"\bclassics\b|classical (studies|civilisation)|\bancient history\b|\blatin\b|\bgreek\b",
 "LNG": r"\bfrench\b|\bspanish\b|\bgerman\b|\bitalian\b|modern languages|\bjapanese\b|\bchinese\b|\bmandarin\b|\barabic\b|\brussian\b|\bportuguese\b",
 "LIN": r"\blinguistics\b",
 "SOC": r"\bsociology\b",
 "ANT": r"\banthropology\b",
 "ARCH": r"\barchaeology\b",
 "THE": r"\btheology\b|\breligio(n|us)\b|\bdivinity\b",
 "SW":  r"\bsocial work\b",
 "EDU": r"primary education|primary teaching|\bqts\b",
 "ART": r"\bfine art\b",
 "FAS": r"\bfashion\b",
 "GD":  r"graphic design|graphic communication",
 "FILM": r"\bfilm\b|\btelevision\b|\btv production\b",
 "MDC": r"\bmedia\b|\bcommunications?\b",
 "JOU": r"\bjournalism\b",
 "MUS": r"\bmusic\b",
 "DRA": r"\bdrama\b|\btheatre\b|\bacting\b",
 "GAM": r"\bgames?\b.*(design|development|art)|game design",
 "PHO": r"\bphotography\b",
 "SPS": r"sport.*(exercise|science)|exercise science",
 "SPM": r"sport.*(management|business)",
}
COURSE_RX = {k: re.compile(v, re.I) for k, v in COURSE_RX.items()}

# ---------------------------------------------------------------- helpers
def open_source(path):
    """Return a function name -> csv rows, from a zip or folder."""
    if path and os.path.isdir(path):
        def rows(name):
            f = glob.glob(os.path.join(path, "**", name + ".csv"), recursive=True)
            return csv.DictReader(open(f[0], encoding="utf-8-sig", errors="replace", newline=""))
        return rows, path
    z = zipfile.ZipFile(path)
    names = z.namelist()
    def rows(name):
        n = next(x for x in names if x.upper().endswith("/" + name.upper() + ".CSV") or x.upper() == name.upper() + ".CSV")
        return csv.DictReader(io.TextIOWrapper(z.open(n), encoding="utf-8-sig", errors="replace", newline=""))
    return rows, path

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

TARIFF_BINS = [("T001", 24), ("T048", 56), ("T064", 72), ("T080", 88), ("T096", 104), ("T112", 120), ("T128", 136),
               ("T144", 152), ("T160", 168), ("T176", 184), ("T192", 200), ("T208", 216), ("T224", 232), ("T240", 248)]

def tariff_median(r):
    """Median UCAS tariff points of entrants, from the binned percentages."""
    vals = [(num(r.get(k)) or 0, mid) for k, mid in TARIFF_BINS]
    tot = sum(v for v, _ in vals)
    if tot <= 0: return None
    acc = 0
    for v, mid in vals:
        acc += v
        if acc >= tot / 2: return mid
    return None

def wavg(items):
    """weighted average of (value, weight)"""
    items = [(v, w or 1) for v, w in items if v is not None]
    if not items: return None
    return sum(v * w for v, w in items) / sum(w for _, w in items)

# ---------------------------------------------------------------- main
def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        zips = sorted(glob.glob(os.path.join(ROOT, "source", "*.zip")), key=os.path.getmtime)
        dirs = [d for d in glob.glob(os.path.join(ROOT, "source", "*")) if os.path.isdir(d)]
        src = (zips[-1] if zips else None) or (dirs[0] if dirs else os.path.join(ROOT, "source"))
    rows, label = open_source(src)
    pub2id = {v: k for k, v in UNI_IDS.items()}

    # dataset date from folder name e.g. on_2026_10_20_...
    m = re.search(r"on_(\d{4})_(\d\d)_(\d\d)", " ".join(zipfile.ZipFile(src).namelist()[:3]) if src.endswith(".zip") else src)
    published = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

    # courses: full-time (KISMODE 01), first degree (KISLEVEL 03)
    courses = {}
    for r in rows("KISCOURSE"):
        if r["PUBUKPRN"] in pub2id and r["KISMODE"] == "01" and r["KISLEVEL"] == "03":
            courses[(r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])] = r

    def load(name):
        out = {}
        for r in rows(name):
            k = (r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])
            if k in courses: out[k] = r
        return out
    nss, tar, cont, sal, emp = load("NSS"), load("TARIFF"), load("CONTINUATION"), load("GOSALARY"), load("EMPLOYMENT")
    accred = set()
    for r in rows("ACCREDITATION"):
        k = (r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])
        if k in courses: accred.add(k)

    # TEF ratings
    tef = {}
    try:
        for r in rows("TEFOutcome"):
            p = r.get("PUBUKPRN") or r.get("UKPRN")
            if p in pub2id:
                tef[pub2id[p]] = r.get("OVERALL_RATING") or r.get("TEFOVERALL") or next((v for k, v in r.items() if "OVERALL" in k.upper()), None)
    except StopIteration:
        pass

    # main campus location = location with most courses
    loc_count = defaultdict(lambda: defaultdict(int))
    for r in rows("COURSELOCATION"):
        k = (r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])
        if k in courses and r["LOCID"]: loc_count[r["PUBUKPRN"]][(r["UKPRN"], r["LOCID"])] += 1
    locs = {}
    for r in rows("LOCATION"):
        locs[(r["UKPRN"], r["LOCID"])] = r
    campus = {}
    for pub, c in loc_count.items():
        for key, _ in sorted(c.items(), key=lambda x: -x[1]):
            L = locs.get(key)
            if L and num(L["LATITUDE"]) and num(L["LONGITUDE"]):
                campus[pub2id[pub]] = {"lat": round(num(L["LATITUDE"]), 4), "lon": round(num(L["LONGITUDE"]), 4), "name": L["LOCNAME"], "accomUrl": L.get("ACCOMURL") or None}
                break

    # group courses into Quad course codes
    agg = defaultdict(lambda: defaultdict(list))
    for k, r in courses.items():
        title = r["TITLE"] or r["TITLEW"] or ""
        for code, rx in COURSE_RX.items():
            if rx.search(title):
                agg[pub2id[k[0]]][code].append(k)

    out = {}
    for uid, cmap in agg.items():
        ucourses = {}
        for code, keys in cmap.items():
            def stat(table, field, popfield):
                return wavg([(num(table[k].get(field)), num(table[k].get(popfield))) for k in keys if k in table])
            nss_vals = []
            for k in keys:
                if k in nss:
                    t = [num(nss[k].get(f"T{i}")) for i in range(1, 8)]
                    t = [x for x in t if x is not None]
                    if t: nss_vals.append((sum(t) / len(t), num(nss[k].get("NSSPOP"))))
            tars = [(tariff_median(tar[k]), num(tar[k].get("TARPOP"))) for k in keys if k in tar]
            work = []
            for k in keys:
                if k in emp:
                    e = emp[k]; ws = num(e.get("WORKSTUDY"))  # % in work and/or further study 15 months after graduating
                    if ws is not None: work.append((ws, num(e.get("EMPPOP"))))
            best = max(keys, key=lambda k: (bool(courses[k]["CRSEURL"]), -len(courses[k]["TITLE"] or "")))
            single = [k for k in keys if COURSE_RX[code].search(courses[k]["TITLE"] or "") and " and " not in (courses[k]["TITLE"] or "").lower() and " with " not in (courses[k]["TITLE"] or "").lower()]
            if single: best = min(single, key=lambda k: len(courses[k]["TITLE"]))
            c = {
                "n": len(keys),
                "title": courses[best]["TITLE"],
                "url": courses[best]["CRSEURL"] or None,
                "sat": round(wavg(nss_vals)) if nss_vals else None,
                "tariff": round(wavg(tars)) if wavg(tars) else None,
                "cont": round(stat(cont, "UCONT", "CONTPOP")) if stat(cont, "UCONT", "CONTPOP") is not None else None,
                "salary": round(stat(sal, "GOINSTMED", "GOSALPOP") / 500) * 500 if stat(sal, "GOINSTMED", "GOSALPOP") else None,
                "work": round(wavg(work)) if work else None,
                "placement": any(courses[k]["SANDWICH"] in ("1", "2") for k in keys),
                "abroad": any(courses[k]["YEARABROAD"] in ("1", "2") for k in keys),
                "accredited": any(k in accred for k in keys),
            }
            ucourses[code] = c
        out[uid] = {"courses": ucourses, "tef": tef.get(uid), "campus": campus.get(uid)}

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    result = {"published": published, "source": "Discover Uni dataset (HESA / Office for Students), CC BY 4.0", "unis": out}
    json.dump(result, open(os.path.join(ROOT, "data", "discover-uni.json"), "w"), separators=(",", ":"))
    n = sum(len(u["courses"]) for u in out.values())
    print(f"Imported {len(out)} unis, {n} uni-course matches (dataset published {published})")

if __name__ == "__main__":
    main()
