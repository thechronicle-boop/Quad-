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
 "MED": r"^(?!.*(veterinar|sport|complementary|herbal|bioengineering|molecular|cellular|translational|experimental))(.*\bmedicine\b|.*\bmbchb\b|.*\bmbbs\b|.*\bbm\s?bs\b)",
 "DEN": r"\bdental surgery\b|\bdentistry\b|\bbds\b",
 "VET": r"\bveterinary (medicine|science|surgery)\b|\bbvsc\b|\bbvms\b|\bbvetmed\b",
 "NUR": r"nursing.*adult|adult nursing|registered nurse.*adult",
 "NCH": r"nursing.*child|child(ren)?'?s? nursing|registered nurse.*child",
 "NMH": r"nursing.*mental health|mental health nursing|registered nurse.*mental",
 "MID": r"\bmidwifery\b",
 "PAR": r"\bparamedic",
 "PHY": r"^(?!.*(veterinar|equine|canine|animal))(.*\bphysiotherapy\b)",
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
 "CS":  r"computer science|computing science|^computing$|^computing \(|^computing with",
 "SE":  r"software engineering|software development",
 "DS":  r"\bdata science\b",
 "AI":  r"artificial intelligence",
 "CYB": r"cyber ?security",
 "ENG": r"\bengineering\b",
 "MEC": r"mechanical engineering",
 "ELE": r"electrical|electronic engineering|electronics",
 "CIV": r"civil engineering",
 "AEN": r"architectural engineering",
 "AER": r"aerospace|aeronautical",
 "CHM": r"chemical engineering",
 "BEN": r"biomedical engineering",
 "ARC": r"^(?!.*(landscape|naval|interior))(architecture|.*\barchitecture\b|.*\barchitectural studies\b)",
 "BUS": r"\bbusiness\b|\bmanagement\b",
 "ACC": r"\baccounting\b|\baccountancy\b|\bfinance\b|\bbanking\b",
 "ECO": r"\beconomics\b",
 "MKT": r"\bmarketing\b",
 "LAW": r"^law\b|\blaw\b|\bllb\b",
 "CRI": r"\bcriminology\b|criminal justice|^crime\b|\bcrime and\b",
 "POL": r"\bpolitics\b",
 "IR":  r"international relations",
 "TOU": r"\btourism\b|\bevents?( management)?\b|\bhospitality\b",
 "EN":  r"english literature|^english\b|\benglish\b(?!.*(language teaching|as a foreign))",
 "HIS": r"^(?!.*\bart\b)(.*\bhistory\b)",
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
 "FILM": r"\bfilm\b|\btelevision\b|\btv production\b|filmmaking|film-making|post[- ]production",
 "MDC": r"\bmedia\b|\bcommunications?\b",
 "JOU": r"\bjournalism\b",
 "MUS": r"\bmusic\b",
 "DRA": r"\bdrama\b|\btheatre\b|\bacting\b|performing arts",
 "GAM": r"\bgames?\b.*(design|development|art)|game design",
 "PHO": r"\bphotography\b",
 "SPS": r"sport.*(exercise|science)|exercise science",
 "SPM": r"sport.*(management|business)",
 "LDN": r"learning disabilit(y|ies) nursing|nursing.*learning disabilit",
 "DHT": r"dental (hygiene|therapy)|oral health",
 "OPT": r"\boptometry\b",
 "POD": r"\bpodiatr",
 "PHL": r"pharmacolog|pharmaceutical science",
 "MSC": r"\bmedical sciences?\b",
 "PUB": r"public health|environmental health",
 "HSC": r"health (and|&) social care",
 "STH": r"sports? therapy|sports? rehabilitation",
 "VN": r"veterinary nursing",
 "CNS": r"\bcounselling\b",
 "GEL": r"\bgeology\b|earth sciences?|geoscience",
 "MAR": r"marine biology",
 "MIC": r"microbiology|immunology|virology",
 "GEN": r"\bgenetics\b",
 "ECL": r"\becology\b|wildlife conservation",
 "NSC": r"natural sciences?",
 "BIT": r"biotechnology",
 "ANS": r"animal (science|behaviour|biology|welfare)|\bequine\b|bioveterinary",
 "AGR": r"agricultur|horticultur",
 "FDS": r"food (science|technology|innovation)",
 "ACT": r"actuarial",
 "IT": r"information technology",
 "MCT": r"mechatronic|robotic",
 "AUT": r"automotive|motorsport",
 "PDE": r"product design",
 "ATE": r"architectural technology",
 "QS": r"quantity surveying",
 "BSV": r"building surveying",
 "CON": r"construction (project )?management",
 "REA": r"real estate",
 "PLN": r"(urban|town|city|regional|spatial|environmental) (and \w+ )?planning|\bplanning\b.*\b(urban|town|regional)\b|^master of planning|(geography|environment) and planning",
 "HRM": r"human resource",
 "POC": r"\bpolicing\b",
 "EDS": r"education studies|^education$|^education[ ,(]|^education (and|with)",
 "ECS": r"early (childhood|years)|childhood studies|child(hood)? and youth|youth studies",
 "SPO": r"social policy|public policy",
 "SSC": r"^social sciences?\b",
 "DEV": r"(international|global) (sustainable )?development",
 "HOA": r"history of art|art history",
 "LIB": r"liberal arts(?! and media foundation)",
 "CW": r"creative writing",
 "ILL": r"illustration",
 "ANI": r"\banimation\b|visual effects|\bvfx\b",
 "INT": r"interior (design|architecture)",
 "TEX": r"\btextile",
 "DAN": r"\bdance\b",
 "MTH": r"musical theatre",
 "MPR": r"music (production|technology)|audio (production|engineering|technology)|sound (engineering|design|production)",
 "COA": r"physical education|\bcoaching\b",
 "HCS": r"healthcare science|\baudiology\b|cardiac physiology|clinical physiology|medical physiology|respiratory physiology",
 "OST": r"osteopath|chiropract",
 "ORT": r"orthoptic|ophthalmic dispensing|dispensing optic",
 "FIV": r"forensic investigation|criminal investigation|crime scene|investigative studies",
 "MTS": r"materials science|materials engineering",
 "STA": r"^statistics\b|\bstatistics$|statistical science",
 "LAR": r"landscape architecture",
 "SEN": r"special educational needs|special and inclusive education|inclusive (education|practice)",
 "CEL": r"\bwelsh\b|\bcymraeg\b|\bgaelic\b|\bceltic\b|\birish (studies|language)|^irish\b",
 "CRA": r"jewellery|silversmith|\bceramics?\b|\bglass\b(?!.*(engineering|science))|\bcrafts?\b",
 "DD": r"digital design|user experience|\bux\b|interaction design|^design$|^design \(|design for publishing",
}
COURSE_RX = {k: re.compile(v, re.I) for k, v in COURSE_RX.items()}

# Official subject codes (HECoS CAH) that also count as a match — catches courses with unusual titles.
CAH_MAP = {
 "VET": ["CAH05-01-01"], "NUR": ["CAH02-04-02"], "NCH": ["CAH02-04-05"],
 "NMH": ["CAH02-04-07"], "MID": ["CAH02-04-04"], "PHA": ["CAH02-02-03"], "RAD": ["CAH02-05-01"],
 "BMS": ["CAH02-05-03"], "PSY": ["CAH04-01"], "BIO": ["CAH03-01-01", "CAH03-01-02"], "BCH": ["CAH03-01-08"], "ZOO": ["CAH03-01-06"],
 "CHE": ["CAH07-02-01"], "PHS": ["CAH07-01-01", "CAH07-01-02"], "MAT": ["CAH09-01-01"], "ENV": ["CAH26-01-04"],
 "GEO": ["CAH26-01-01", "CAH26-01-02", "CAH26-01-03"], "CS": ["CAH11-01-01"], "AI": ["CAH11-01-05"], "GAM": ["CAH11-01-06"],
 "ENG": ["CAH10-01"], "MEC": ["CAH10-01-02"], "AER": ["CAH10-01-04"], "CIV": ["CAH10-01-07"],
 "ELE": ["CAH10-01-08"], "ARC": ["CAH13-01-01"], "ECO": ["CAH15-02-01"], "POL": ["CAH15-03-01"],
 "BUS": ["CAH17-01-01", "CAH17-01-02", "CAH17-01-04"], "MKT": ["CAH17-01-03"], "TOU": ["CAH17-01-06"], "ACC": ["CAH17-01-07", "CAH17-01-08"],
 "SW": ["CAH15-04-01"], "EN": ["CAH19-01-01", "CAH19-01-03"], "LIN": ["CAH19-01-07"], "LNG": ["CAH19-04"],
 "HIS": ["CAH20-01-01"], "ARCH": ["CAH20-01-03"], "CLA": ["CAH20-01-05"], "PHI": ["CAH20-02-01"], "THE": ["CAH20-02-02"],
 "ART": ["CAH25-01-02"], "MDC": ["CAH24-01-05"], "JOU": ["CAH24-01-04"], "MUS": ["CAH25-02-02"], "DRA": ["CAH25-02-03"], "SPS": ["CAH03-02-01"],
 "LDN": ["CAH02-04-08"], "DHT": ["CAH02-04-06"], "PHL": ["CAH02-02-01"], "GEN": ["CAH03-01-07"], "ANS": ["CAH06-01-01"], "FDS": ["CAH06-01-07"], "CW": ["CAH19-01-05"],
 "LAR": ["CAH13-01-03"],
}

# Specialist higher-education institutions students apply to through UCAS (conservatoires, art, drama and music schools,
# veterinary and rural colleges, small universities). Further-education colleges are deliberately not included.
SPECIALIST = {
 "10007779": "Royal Veterinary College", "10034449": "Leeds Conservatoire", "10003945": "LIPA (Liverpool Institute for Performing Arts)",
 "10002681": "Glasgow School of Art", "10001503": "The Northern School of Art", "10005561": "Royal Conservatoire of Scotland",
 "10003022": "Hereford College of Arts", "10005700": "SRUC (Scotland's Rural College)", "10067406": "NMITE",
 "10048199": "Northeastern University London", "10005523": "Rose Bruford College", "10007816": "Royal Central School of Speech and Drama",
 "10008010": "Stranmillis University College", "10007838": "Royal Welsh College of Music and Drama", "10039082": "City and Guilds of London Art School",
 "10008017": "Trinity Laban Conservatoire", "10031982": "BPP University", "10007825": "Guildhall School of Music and Drama",
 "10007835": "Royal Academy of Music", "10008026": "St Mary's University College, Belfast", "10004450": "Mountview Academy of Theatre Arts",
 "10042570": "Escape Studios", "10035638": "ICMP (Institute of Contemporary Music Performance)", "10019178": "Point Blank Music School",
 "10088321": "DBS Institute (Deep Blue Sound)", "10085293": "WaterBear College of Music", "10007839": "SAE Institute",
 "10052868": "London College of Contemporary Arts", "10010308": "Cambridge School of Visual and Performing Arts", "10010457": "Spirit Studios",
 "10066551": "LCCM (London College of Contemporary Music)", "10067853": "ACM (Academy of Contemporary Music)", "10009527": "Istituto Marangoni London",
 "10022087": "Futureworks", "10031239": "Liverpool Media Academy", "10008173": "University College of Estate Management",
}

# Titles that must NOT count for a subject even if their official subject code matches (e.g. Sound Engineering is not Engineering)
NOT_RX = {k: re.compile(v, re.I) for k, v in {
 "ENG": r"sound|audio|music|^architecture", "ELE": r"sound|audio|music", "MEC": r"sound|audio|music",
 "CS": r"graphic|illustration|animation", "SW": r"\barts with community\b", "CIV": r"^architecture",
}.items()}
# Titles that MUST contain one of these words to count for the subject
NEED_RX = {k: re.compile(v, re.I) for k, v in {
 "TOU": r"touris|event|hospitality|travel|leisure",
}.items()}

# registered address isn't where students study
CITY_FIX = {"10067648": "Manchester", "10019178": "Several cities", "10007839": "Several cities", "10035638": "Several cities",
            "10088321": "Several cities", "10085293": "Several cities", "10031982": "Several cities"}

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

COUNTIES = set(x.lower() for x in """Dorset Devon Somerset Cornwall Wiltshire Avon Hampshire Surrey Kent Essex Suffolk Norfolk Middlesex Berkshire
Oxfordshire Buckinghamshire Bedfordshire Hertfordshire Cambridgeshire Northamptonshire Leicestershire Nottinghamshire Derbyshire Staffordshire
Warwickshire Worcestershire Herefordshire Shropshire Gloucestershire Lincolnshire Cheshire Lancashire Cumbria Merseyside Northumberland
Renfrewshire Fife Midlothian Lothian Gwynedd Ceredigion Powys Glamorgan Antrim Down Londonderry""".split()) | {
"west midlands","east sussex","west sussex","west yorkshire","south yorkshire","north yorkshire","east yorkshire","greater manchester",
"mid glamorgan","south glamorgan","west glamorgan","tyne and wear","tyne & wear","county durham","co durham","isle of wight","co antrim",
"county antrim","co down","county down","greater london","east riding of yorkshire","north lanarkshire","south lanarkshire","west lothian","east lothian"}

NAME_FIX = {"goldsmiths' college": "Goldsmiths, University of London", "goldsmiths college, university of london": "Goldsmiths, University of London",
            "birkbeck college": "Birkbeck, University of London", "school of oriental and african studies": "SOAS University of London",
            "university academy 92": "UA92", "ua92": "UA92", "bimm university": "BIMM University"}

def town_from(addr):
    parts = [p.strip() for p in (addr or "").split(",") if p.strip()]
    if parts and re.match(r"^[A-Z]{1,2}\d", parts[-1].upper()): parts = parts[:-1]
    while parts and parts[-1].lower() in COUNTIES: parts = parts[:-1]
    t = parts[-1] if parts else ""
    t = t.rstrip(". ")
    return t.title() if t.isupper() or t.islower() else t

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
    legacy = {v: k for k, v in UNI_IDS.items()}

    # every UK university in the dataset (plus KCL, Imperial, LSE which don't have "University" in their name)
    inst = {}
    for r in rows("INSTITUTION"):
        inst.setdefault(r["PUBUKPRN"], r)
    ft = defaultdict(int)
    for r in rows("KISCOURSE"):
        if r["KISMODE"] == "01" and r["KISLEVEL"] == "03": ft[r["PUBUKPRN"]] += 1
    pub2id = {}
    for p, r in inst.items():
        n = r["LEGAL_NAME"] + " | " + r["FIRST_TRADING_NAME"]
        isuni = re.search(r"universit", n, re.I) and not re.search(r"university centre|university campus", n, re.I) and r["LEGAL_NAME"].strip() != "University of London"
        special = re.search(r"king's college london|imperial college|london school of economics", n, re.I)
        if p in legacy or p in SPECIALIST or ((isuni or special) and ft[p] >= 10):
            pub2id[p] = legacy.get(p, "p" + p)
    NATION = {"XF": "eng", "XG": "ni", "XH": "sco", "XI": "wal"}
    meta = {}
    for p, uid in pub2id.items():
        r = inst[p]
        legal, trade = r["LEGAL_NAME"].strip(), r["FIRST_TRADING_NAME"].strip()
        name = trade if trade and (re.search(r"universit", trade, re.I) or not re.search(r"universit", legal, re.I)) else legal
        name = re.sub(r"\s+(Limited|Ltd|plc|inc\.?)$", "", re.sub(r",?\s*inc\.?$", "", name, flags=re.I), flags=re.I)
        name = name.split("/")[0].strip()
        name = re.sub(r"\bOf\b", "of", re.sub(r"\bThe\b(?!$)", "the", name)) if name.istitle() else name
        name = re.sub(r"\s+Higher Education Corporation$", "", name)
        name = NAME_FIX.get(name.lower(), name)
        if name[0].islower(): name = name[0].upper() + name[1:]
        if name.isupper() or name.lower().startswith("the ") and name.isupper(): name = name.title()
        name = re.sub(r"^The ", "", re.sub(r",? ?The$", "", name)).strip()
        name = re.sub(r"\s*\(Part of .*?\)", "", name)
        name = re.sub(r"\b(Of|And|For|The|At)\b", lambda m: m.group(1).lower(), name)
        name = name[0].upper() + name[1:]
        if name.lower() in ("ua92", "university academy 92"): name = "UA92"
        if p in SPECIALIST: name = SPECIALIST[p]
        town = CITY_FIX.get(p) or town_from(r["PROVADDRESS"])
        meta[uid] = {"name": name, "town": town, "nation": NATION.get(r["COUNTRY"], "eng"), "web": r["PROVURL"]}

    # dataset date from folder name e.g. on_2026_10_20_...
    m = re.search(r"on_(\d{4})_(\d\d)_(\d\d)", " ".join(zipfile.ZipFile(src).namelist()[:3]) if src.endswith(".zip") else src)
    published = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

    # courses: full-time (KISMODE 01), first degree (KISLEVEL 03); part-time first degrees kept separately
    courses, parttime = {}, defaultdict(list)
    for r in rows("KISCOURSE"):
        if r["PUBUKPRN"] in pub2id and r["KISLEVEL"] == "03":
            if r["KISMODE"] == "01": courses[(r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])] = r
            elif r["KISMODE"] == "02": parttime[r["PUBUKPRN"]].append(r["TITLE"] or "")
    MASTERS = {c for c in ["040","041","046","047","048","049","051","053","054","056","057","058","059","060","061","062","063","064","065","066","067","068","070","071","073","074","075","077","078","079","088"]}

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
    course_locs = defaultdict(list)
    for r in rows("COURSELOCATION"):
        k = (r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])
        if k in courses and r["LOCID"]:
            loc_count[r["PUBUKPRN"]][(r["UKPRN"], r["LOCID"])] += 1
            course_locs[k].append((r["UKPRN"], r["LOCID"]))
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

    # official subject codes for each course
    sbj = defaultdict(list)
    for r in rows("SBJ"):
        k = (r["PUBUKPRN"], r["KISCOURSEID"], r["KISMODE"])
        if k in courses: sbj[k].append(r["SBJ"])

    # group courses into Quad course codes: matched by title, or by official subject code
    agg = defaultdict(lambda: defaultdict(list))
    for k, r in courses.items():
        title = r["TITLE"] or r["TITLEW"] or ""
        for code, rx in COURSE_RX.items():
            if code in NOT_RX and NOT_RX[code].search(title): continue
            if code in NEED_RX and not NEED_RX[code].search(title): continue
            if rx.search(title) or any(sc.startswith(pref) for sc in sbj[k] for pref in CAH_MAP.get(code, [])):
                agg[pub2id[k[0]]][code].append(k)

    aims = {r["KISAIMCODE"]: r["KISAIMLABEL"] for r in rows("KISAIM")}
    out = {}
    variants = defaultdict(dict)
    id2pub = {v: k for k, v in pub2id.items()}
    for uid, cmap in agg.items():
        k_pub = id2pub[uid]
        ucourses = {}
        for code, allkeys in cmap.items():
            # single-subject courses (one official subject code) give the figures when the uni has any;
            # otherwise the subject is only offered as part of a joint degree
            singles = [k for k in allkeys if len(set(sbj[k])) <= 1]
            joint_only = not singles
            keys = singles or allkeys
            def stat(table, field, popfield, keys=keys):
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
            # how specific each figure is: the official data gives level 4 = this exact course;
            # 3/2/1 = combined with similar courses at this uni (3 = narrow subject group, 1 = very broad)
            def level(table, field, ks):
                lv = [int(table[k][field][1]) for k in ks if k in table and len(table[k].get(field) or "") == 2]
                return min(lv) if lv else None
            grp = {n: l for n, l in (("sat", level(nss, "NSSAGG", keys)), ("tariff", level(tar, "TARAGG", keys)), ("cont", level(cont, "CONTAGG", keys)),
                                     ("salary", level(sal, "GOSALAGG", keys)), ("work", level(emp, "EMPAGG", keys))) if l is not None and l < 4}
            best = max(keys, key=lambda k: (bool(courses[k]["CRSEURL"]), -len(courses[k]["TITLE"] or "")))
            single = [k for k in keys if COURSE_RX[code].search(courses[k]["TITLE"] or "") and " and " not in (courses[k]["TITLE"] or "").lower() and " with " not in (courses[k]["TITLE"] or "").lower()]
            if single: best = min(single, key=lambda k: len(courses[k]["TITLE"]))
            c = {
                "n": len(allkeys),
                "jointOnly": joint_only,
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
                "foundation": any(courses[k]["FOUNDATION"] in ("1", "2") for k in keys),
                "masters": any(courses[k]["KISAIMCODE"] in MASTERS for k in keys),
                "parttime": any(COURSE_RX[code].search(t) for t in parttime[k_pub]),
            }
            if grp: c["grp"] = grp
            # every campus this course is taught at (multi-campus unis); the app uses the one nearest the student
            lc = defaultdict(int)
            for k in keys:
                for L in set(course_locs.get(k, [])): lc[L] += 1
            places = []
            for key, _ in sorted(lc.items(), key=lambda x: (-x[1], x[0])):  # ties broken by id so every run gives the same list
                L = locs.get(key)
                if L and num(L["LATITUDE"]) and num(L["LONGITUDE"]):
                    p_ = {"lat": round(num(L["LATITUDE"]), 4), "lon": round(num(L["LONGITUDE"]), 4), "name": L["LOCNAME"]}
                    if all(abs(p_["lat"] - q["lat"]) + abs(p_["lon"] - q["lon"]) > 0.02 for q in places): places.append(p_)
                if len(places) >= 4: break
            main = campus.get(uid)
            if places and not (len(places) == 1 and main and abs(main["lat"] - places[0]["lat"]) + abs(main["lon"] - places[0]["lon"]) <= 0.02):
                c["locs"] = places
            ucourses[code] = c
            # every individual course in this group, so students can pick the exact one
            vlist = []
            for k in sorted(allkeys, key=lambda k: (len(set(sbj[k])) > 1, courses[k]["TITLE"] or "")):
                r_ = courses[k]
                t = [num(nss[k].get(f"T{i}")) for i in range(1, 8)] if k in nss else []
                t = [x for x in t if x is not None]
                sal_ = num(sal[k].get("GOINSTMED")) if k in sal else None
                vlist.append([r_["TITLE"], r_["CRSEURL"] or None,
                    round(sum(t) / len(t)) if t else None,
                    tariff_median(tar[k]) if k in tar else None,
                    round(num(cont[k].get("UCONT"))) if k in cont and num(cont[k].get("UCONT")) is not None else None,
                    round(sal_ / 500) * 500 if sal_ else None,
                    round(num(emp[k].get("WORKSTUDY"))) if k in emp and num(emp[k].get("WORKSTUDY")) is not None else None,
                    1 if r_["SANDWICH"] in ("1", "2") else 0, 1 if r_["YEARABROAD"] in ("1", "2") else 0,
                    1 if r_["FOUNDATION"] in ("1", "2") else 0, 1 if r_["KISAIMCODE"] in MASTERS else 0,
                    1 if len(set(sbj[k])) > 1 else 0, 1 if k in accred else 0, aims.get(r_["KISAIMCODE"], ""),
                    {n: l for n, l in (("sat", level(nss, "NSSAGG", [k])), ("tariff", level(tar, "TARAGG", [k])), ("cont", level(cont, "CONTAGG", [k])),
                                       ("salary", level(sal, "GOSALAGG", [k])), ("work", level(emp, "EMPAGG", [k]))) if l is not None and l < 4}])
            variants[code][uid] = vlist[:40]
        out[uid] = {"courses": ucourses, "tef": tef.get(uid), "campus": campus.get(uid), **meta[uid]}

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    result = {"published": published, "source": "Discover Uni dataset (HESA / Office for Students), CC BY 4.0", "unis": out}
    json.dump(result, open(os.path.join(ROOT, "data", "discover-uni.json"), "w"), separators=(",", ":"))
    vdir = os.path.join(ROOT, "data", "variants"); os.makedirs(vdir, exist_ok=True)
    for code, m in variants.items():
        json.dump(m, open(os.path.join(vdir, code + ".json"), "w"), separators=(",", ":"))
    n = sum(len(u["courses"]) for u in out.values())
    print(f"Imported {len(out)} unis, {n} uni-course matches (dataset published {published})")

if __name__ == "__main__":
    main()
