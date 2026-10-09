"""Travel Attribute Extraction - sequence labelling (BIO) + attribute extraction.
No chatbot: sentence in -> tokens -> BIO tags -> attributes -> JSON.

v2 additions (model-depth batch):
  1. Negation handling        -> "not from Delhi, from Hyderabad" ignores Delhi
  2. Multi-entity passengers  -> "2 adults and 1 child" extracted separately
  3. Return date / round trip -> "...returning on 10 October" tagged RETURN_DATE
"""
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

@app.route("/")
def home():
    return "Travel Attribute Extractor is running!"
CORS(app)

CITIES = {c.lower() for c in [
    "Hyderabad", "Delhi", "New Delhi", "Mumbai", "Bangalore", "Bengaluru", "Chennai", "Kolkata",
    "Vizag", "Visakhapatnam", "Vijayawada", "Tirupati", "Pune", "Goa", "Jaipur", "Kochi",
    "Ahmedabad", "Lucknow", "Guwahati", "Bhubaneswar", "Coimbatore", "Nagpur", "Patna",
    "Dubai", "Singapore", "London", "Paris", "New York", "Bangkok", "Colombo", "Kathmandu"]}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
MONTH_ABBR = {m[:3]: m for m in MONTHS}
WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
REL_DATES = {"today", "tomorrow", "tonight"}
MODES = {"flight", "flights", "train", "trains", "bus", "buses", "cab", "taxi", "hotel"}
CLASSES = {"economy", "business", "first", "premium", "sleeper", "ac"}

# generic passenger words (no adult/child split)
PAX_WORDS = {"passenger", "passengers", "people", "persons", "person",
             "travellers", "travelers", "members", "seats", "tickets"}
# NEW: split adult / child / infant counts
PAX_ADULT_WORDS = {"adult", "adults"}
PAX_CHILD_WORDS = {"child", "children", "kid", "kids"}
PAX_INFANT_WORDS = {"infant", "infants"}

NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}

# NEW: connector words that can sit between "not" and the entity it negates
NEG_CONNECTORS = {"from", "to", "via", "through"}
# NEW: words that signal the date which follows belongs to the return leg
RETURN_TRIGGERS = {"return", "returning"}
RETURN_LOOKAHEAD = 4  # how many tokens after the trigger we still treat as "return context"
# NEW (multi-leg): a city right after one of these is a VIA stop, not the final destination
VIA_WORDS = {"via", "through"}
# NEW (v5): time of travel + budget
TIME_WORDS = {"morning", "afternoon", "evening", "night", "noon", "midnight"}
BUDGET_TRIGGERS = {"under", "below", "within", "budget"}
BUDGET_FILLER = {"of", "rs", "inr", "₹", "."}
# NEW (v6): seat / meal / stops preferences
SEAT_WORDS = {"window", "aisle", "middle"}
MEAL_WORDS = {"veg", "vegetarian", "vegan", "jain"}
STOP_WORDS = {"nonstop", "direct"}


def tokenize(text):
    return re.findall(r"\d+(?:[/-]\d+)*(?:st|nd|rd|th)?|[A-Za-z]+|[^\sA-Za-z\d]", text)


def _city_span_at(low, i):
    """Return span length if a city starts at index i, else 0."""
    for L in (2, 1):
        if i + L <= len(low) and " ".join(low[i:i + L]) in CITIES:
            return L
    return 0


def find_negated_indices(low):
    """NEW: token indices inside a 'not <city>' scope, e.g. 'not from Delhi'
    -> Delhi's index is negated and must not become SOURCE/DESTINATION."""
    negated = set()
    n = len(low)
    for i, w in enumerate(low):
        if w != "not":
            continue
        j = i + 1
        if j < n and low[j] in NEG_CONNECTORS:
            j += 1
        span = _city_span_at(low, j)
        if span:
            negated.update(range(j, j + span))
    return negated


def find_city_chain(low, negated):
    """NEW (multi-leg): every non-negated city span in the sentence, in the
    order they appear, as (start, end) index pairs."""
    spans, i, n = [], 0, len(low)
    while i < n:
        span = _city_span_at(low, i)
        if span and not any(k in negated for k in range(i, i + span)):
            spans.append((i, i + span))
            i += span
        else:
            i += 1
    return spans


def classify_city_chain(low, negated):
    """NEW (multi-leg): decide which city span is SOURCE, which is
    DESTINATION, and which ones are VIA stops in between.
    - "A to B to C"        -> A=SOURCE, B=VIA, C=DESTINATION
    - "A to C via B"       -> A=SOURCE, C=DESTINATION, B=VIA (explicit keyword)
    Falls back to the original single-pair, preceding-word logic when there
    are only one or two cities and no explicit via/through keyword, so every
    sentence that worked before still tags exactly the same way."""
    spans = find_city_chain(low, negated)
    via_flagged = {idx for idx, (s, e) in enumerate(spans) if s > 0 and low[s - 1] in VIA_WORDS}
    chain = [sp for idx, sp in enumerate(spans) if idx not in via_flagged]
    via_spans = [sp for idx, sp in enumerate(spans) if idx in via_flagged]

    if len(chain) < 3 and not via_spans:
        return None   # not multi-leg: let the original per-span logic handle it

    labels = {}
    if chain:
        labels[chain[0]] = "SOURCE"
        if len(chain) > 1:
            labels[chain[-1]] = "DESTINATION"
        for sp in chain[1:-1]:
            labels[sp] = "VIA"
    for sp in via_spans:
        labels[sp] = "VIA"
    return labels


def tag_tokens(tokens):
    """Returns one BIO tag per token. Swap this function for the RoBERTa
    token-classification model later; everything else stays the same."""
    low = [t.lower() for t in tokens]
    n = len(tokens)
    tags = ["O"] * n
    negated = find_negated_indices(low)          # NEW
    multi_leg = classify_city_chain(low, negated)  # NEW: None unless 3+ stops / explicit "via"

    def put(i, j, label):
        for k in range(i, j):
            tags[k] = ("B-" if k == i else "I-") + label

    return_near = 0   # NEW: >0 means "the next date we see is a RETURN_DATE"
    i = 0
    while i < n:
        w = low[i]

        # NEW: "return"/"returning" opens a short window where the next
        # date found belongs to the return leg, not the outbound date
        if w in RETURN_TRIGGERS:
            return_near = RETURN_LOOKAHEAD
            i += 1
            continue

        # cities (2-word first, then 1-word)
        span = _city_span_at(low, i)
        if span:
            if any(k in negated for k in range(i, i + span)):   # NEW: skip negated city
                i += span
                continue
            if multi_leg is not None:                            # NEW: 3+ stop itinerary
                label = multi_leg.get((i, i + span))
                if label:
                    put(i, i + span, label)
                i += span
                continue
            prev = low[i - 1] if i else ""
            put(i, i + span, "SOURCE" if prev in {"from", "leaving", "starting", "departing"} else "DESTINATION")
            i += span
            continue

        # dates
        date_end = None
        if w in REL_DATES or w in WEEKDAYS:
            date_end = i + 1
        elif re.fullmatch(r"\d{1,4}[/-]\d{1,2}[/-]\d{2,4}", w):
            date_end = i + 1
        elif re.fullmatch(r"\d{1,2}(st|nd|rd|th)?", w) and i + 1 < n and low[i + 1][:3] in MONTH_ABBR and low[i + 1] in MONTHS + list(MONTH_ABBR):
            date_end = i + 2
            if date_end < n and re.fullmatch(r"\d{4}", low[date_end]):
                date_end += 1
        elif w in MONTHS or w in MONTH_ABBR:
            if i + 1 < n and re.fullmatch(r"\d{1,2}(st|nd|rd|th)?", low[i + 1]):
                date_end = i + 2

        if date_end:
            label = "RETURN_DATE" if return_near > 0 else "DATE"   # NEW
            put(i, date_end, label)
            return_near = 0
            i = date_end
            continue

        if return_near > 0:
            return_near -= 1   # NEW: window closes if no date shows up in time

        # NEW (v6): STOPS ("non-stop", "direct"), MEAL ("veg meal", "non-veg"), SEAT ("window seat")
        if w == "non" and i + 2 < n and low[i + 1] == "-":
            if low[i + 2] == "stop":
                put(i, i + 3, "STOPS"); i += 3; continue
            if low[i + 2] in {"veg", "vegetarian"}:
                j = i + 3 + (1 if i + 3 < n and low[i + 3] in {"meal", "meals", "food"} else 0)
                put(i, j, "MEAL"); i = j; continue
        if w in STOP_WORDS:
            put(i, i + 1, "STOPS"); i += 1; continue
        if w in SEAT_WORDS and i + 1 < n and low[i + 1] == "seat":
            put(i, i + 2, "SEAT"); i += 2; continue
        if w in MEAL_WORDS:
            j = i + 1 + (1 if i + 1 < n and low[i + 1] in {"meal", "meals", "food"} else 0)
            put(i, j, "MEAL"); i = j; continue
        # NEW (v5): TIME -> "morning", "6 pm", "6:30 pm"
        if w in TIME_WORDS:
            put(i, i + 1, "TIME"); i += 1; continue
        if re.fullmatch(r"\d{1,2}", w) and i + 1 < n and low[i + 1] in {"am", "pm"}:
            put(i, i + 2, "TIME"); i += 2; continue
        if (re.fullmatch(r"\d{1,2}", w) and i + 3 < n and low[i + 1] == ":"
                and re.fullmatch(r"\d{2}", low[i + 2]) and low[i + 3] in {"am", "pm"}):
            put(i, i + 4, "TIME"); i += 4; continue
        # NEW (v5): BUDGET -> "under 5000", "budget of Rs 8000"
        if w in BUDGET_TRIGGERS:
            j = i + 1
            while j < n and low[j] in BUDGET_FILLER:
                j += 1
            if j < n and re.fullmatch(r"\d{3,7}", low[j]):
                put(j, j + 1, "BUDGET"); i = j + 1; continue

        # passengers (generic / adult / child / infant)
        if (re.fullmatch(r"\d{1,2}", w) or w in NUMWORDS) and i + 1 < n:
            nxt = low[i + 1]
            if nxt in PAX_ADULT_WORDS:
                put(i, i + 2, "PASSENGER_ADULT"); i += 2; continue
            if nxt in PAX_CHILD_WORDS:
                put(i, i + 2, "PASSENGER_CHILD"); i += 2; continue
            if nxt in PAX_INFANT_WORDS:
                put(i, i + 2, "PASSENGER_INFANT"); i += 2; continue
            if nxt in PAX_WORDS:
                put(i, i + 2, "PASSENGERS"); i += 2; continue

        # class
        if w in CLASSES and i + 1 < n and low[i + 1] in {"class", "ac"}:
            put(i, i + 2, "CLASS"); i += 2; continue
        if w in {"economy", "business"}:
            put(i, i + 1, "CLASS"); i += 1; continue
        if w == "premium" and i + 1 < n and low[i + 1] == "economy":
            put(i, i + 2, "CLASS"); i += 2; continue
        if w in MODES:
            put(i, i + 1, "MODE"); i += 1; continue

        i += 1
    return tags


def extract_attributes(tokens, tags):
    spans, cur, label = [], [], None

    def flush():
        if cur:
            spans.append((label, " ".join(cur)))

    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            flush()
            cur, label = [tok], tag[2:]
        elif tag.startswith("I-") and label == tag[2:]:
            cur.append(tok)
        else:
            flush()
            cur, label = [], None
    flush()

    attrs = {}

    def to_num(text):
        v = text.split()[0].lower()
        return int(v) if v.isdigit() else NUMWORDS.get(v, v)

    adults = children = infants = generic_pax = None
    via_stops = []   # NEW (multi-leg): every VIA span, in the order it was found
    for lbl, text in spans:
        l = lbl.lower()
        if l == "passenger_adult":
            adults = (adults or 0) + to_num(text)
        elif l == "passenger_child":
            children = (children or 0) + to_num(text)
        elif l == "passenger_infant":
            infants = (infants or 0) + to_num(text)
        elif l == "passengers":
            generic_pax = to_num(text)
        elif l == "mode":
            attrs.setdefault("mode", {"flights": "flight", "trains": "train", "buses": "bus",
                                       "taxi": "cab"}.get(text.lower(), text.lower()))
        elif l == "time":
            attrs.setdefault("time", text.replace(" : ", ":"))   # NEW (v5)
        elif l in ("stops", "meal", "seat"):
            attrs.setdefault(l, text.replace(" - ", "-"))   # NEW (v6)
        elif l == "via":
            via_stops.append(text)   # NEW
        else:
            attrs.setdefault(l, text)   # source / destination / date / return_date / class

    # NEW (multi-leg): expose the stop list and a source->via->...->destination
    # leg-by-leg breakdown whenever there's more than one straight hop
    if via_stops:
        attrs["via"] = via_stops
        route = [attrs["source"]] + via_stops + [attrs["destination"]] if "source" in attrs and "destination" in attrs else None
        if route:
            attrs["legs"] = [{"from": route[k], "to": route[k + 1]} for k in range(len(route) - 1)]

    # NEW: combine adult/child/infant breakdown, or fall back to a single count
    if adults is not None or children is not None or infants is not None:
        if adults is not None:
            attrs["adults"] = adults
        if children is not None:
            attrs["children"] = children
        if infants is not None:
            attrs["infants"] = infants
        attrs["passengers"] = (adults or 0) + (children or 0) + (infants or 0)
    elif generic_pax is not None:
        attrs["passengers"] = generic_pax

    return attrs


@app.post("/api/extract")
def extract():
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify(error="Enter a travel sentence first."), 400
    tokens = tokenize(text)
    tags = tag_tokens(tokens)
    attrs = extract_attributes(tokens, tags)
    return jsonify(text=text, tokens=[{"token": t, "tag": g} for t, g in zip(tokens, tags)], attributes=attrs)



@app.get("/api/cities")
def cities():
    """City list for the Extractor's autocomplete. Uses the same CITIES
    gazetteer the tagger matches against, so suggestions always stay in sync.
    GET /api/cities        -> every city, A-Z
    GET /api/cities?q=hy   -> cities starting with 'hy' first, then cities
                              that merely contain it (max 8)."""
    q = (request.args.get("q") or "").strip().lower()
    names = sorted(c.title() for c in CITIES)
    if not q:
        return jsonify(names)
    starts = [c for c in names if c.lower().startswith(q)]
    has = [c for c in names if q in c.lower() and c not in starts]
    return jsonify((starts + has)[:8])


# ===================== v3 EXTRAS (additive, nothing above is changed) =====================
from datetime import date, timedelta

_WD = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_date_text(s, today=None):
    """Turn extracted date text ('tomorrow', '25 September', 'Friday', '12/10/2026') into a date."""
    today = today or date.today()
    s = s.strip().lower().replace(",", " ")
    t = s.split()
    if not t:
        return None
    w = t[0]
    if w in ("today", "tonight"):
        return today
    if w == "tomorrow":
        return today + timedelta(days=1)
    if w in _WD:
        return today + timedelta(days=((_WD.index(w) - today.weekday()) % 7) or 7)
    m = re.fullmatch(r"(\d{1,4})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        x, y, z = map(int, m.groups())
        try:
            return date(x, y, z) if x > 31 else date(z if z > 99 else 2000 + z, y, x)
        except ValueError:
            return None
    day = month = year = None
    for x in t:
        xm = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", x)
        if xm and day is None:
            day = int(xm.group(1))
        elif re.fullmatch(r"\d{4}", x):
            year = int(x)
        elif x[:3] in MONTH_ABBR and (x in MONTHS or x in MONTH_ABBR):
            month = MONTHS.index(MONTH_ABBR[x[:3]]) + 1
    if not (day and month):
        return None
    try:
        d = date(year or today.year, month, day)
        if not year and d < today:
            d = date(today.year + 1, month, day)
        return d
    except ValueError:
        return None


@app.post("/api/analyze")
def analyze():
    """Extra layer: tokens/tags/attributes + ISO dates, validation warnings,
    completeness score and a one-line trip summary."""
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify(error="Enter a travel sentence first."), 400
    tokens = tokenize(text)
    tags = tag_tokens(tokens)
    attrs = extract_attributes(tokens, tags)
    today = date.today()

    d1 = parse_date_text(attrs["date"]) if "date" in attrs else None
    d2 = parse_date_text(attrs["return_date"]) if "return_date" in attrs else None
    if d1 and d2 and d2 < d1 and not re.search(r"\d{4}", attrs["return_date"]):
        d2 = d2.replace(year=d2.year + 1)   # "25 Dec ... return 2 Jan" -> next year

    warnings = []
    if "source" not in attrs:
        warnings.append("Source city is missing.")
    if "destination" not in attrs:
        warnings.append("Destination city is missing.")
    if "date" not in attrs:
        warnings.append("Travel date is missing.")
    if "mode" not in attrs:
        warnings.append("Travel mode (flight/train/bus) not mentioned.")
    if attrs.get("source") and attrs.get("source", "").lower() == attrs.get("destination", "").lower():
        warnings.append("Source and destination are the same city.")
    if d1 and d1 < today:
        warnings.append("Travel date is in the past.")
    if d1 and d2 and d2 < d1:
        warnings.append("Return date is before the travel date.")
    if attrs.get("infants", 0) > attrs.get("adults", 0) and "adults" in attrs:
        warnings.append("Each infant needs an accompanying adult.")

    if "meal" in attrs and attrs.get("mode") in ("bus", "cab"):
        warnings.append("Meal preference is usually not available on bus/cab.")
    if "stops" in attrs and "via" in attrs:
        warnings.append("Non-stop/direct requested but the route has a via stop.")
    need = ["mode", "source", "destination", "date", "passengers"]
    score = round(100 * sum(k in attrs for k in need) / len(need))

    parts = [attrs.get("mode", "trip").capitalize()]
    if "source" in attrs or "destination" in attrs:
        parts.append(f"from {attrs.get('source', '?')} to {attrs.get('destination', '?')}")
    if d1:
        parts.append("on " + d1.strftime("%a, %d %b %Y"))
    if d2:
        parts.append("returning " + d2.strftime("%a, %d %b %Y"))
    if "passengers" in attrs:
        parts.append(f"for {attrs['passengers']} traveller(s)")
    if "time" in attrs:
        parts.append(f"around {attrs['time']}")
    prefs = [attrs[k] for k in ("stops", "seat", "meal") if k in attrs]
    if prefs:
        parts.append("(" + ", ".join(prefs) + ")")
    if "budget" in attrs:
        parts.append(f"with a budget of Rs {int(attrs['budget']):,}")
    if "class" in attrs:
        parts.append(f"in {attrs['class']}")

    return jsonify(
        text=text,
        tokens=[{"token": t, "tag": g} for t, g in zip(tokens, tags)],
        attributes=attrs,
        iso_dates={"date": d1.isoformat() if d1 else None, "return_date": d2.isoformat() if d2 else None},
        trip_days=((d2 - d1).days if d1 and d2 and d2 >= d1 else None),
        round_trip=bool(d2),
        warnings=warnings,
        completeness=score,
        summary=" ".join(parts) + ".",
    )



# ===================== v4 EXTRAS: distance / fare estimate + spelling suggestions =====================
import math, difflib

COORDS = {
    "hyderabad": (17.385, 78.487), "delhi": (28.614, 77.209), "new delhi": (28.614, 77.209),
    "mumbai": (19.076, 72.878), "bangalore": (12.972, 77.595), "bengaluru": (12.972, 77.595),
    "chennai": (13.083, 80.270), "kolkata": (22.573, 88.364), "vizag": (17.687, 83.218),
    "visakhapatnam": (17.687, 83.218), "vijayawada": (16.506, 80.648), "tirupati": (13.629, 79.420),
    "pune": (18.520, 73.857), "goa": (15.299, 74.124), "jaipur": (26.912, 75.787), "kochi": (9.931, 76.267),
    "ahmedabad": (23.023, 72.572), "lucknow": (26.847, 80.947), "guwahati": (26.144, 91.736),
    "bhubaneswar": (20.296, 85.825), "coimbatore": (11.017, 76.956), "nagpur": (21.146, 79.088),
    "patna": (25.594, 85.138), "dubai": (25.205, 55.271), "singapore": (1.352, 103.820),
    "london": (51.507, -0.128), "paris": (48.857, 2.352), "new york": (40.713, -74.006),
    "bangkok": (13.756, 100.502), "colombo": (6.927, 79.861), "kathmandu": (27.717, 85.324)}
# mode -> (base fare INR, INR per km, speed km/h, fixed overhead hours, route factor)
RATES = {"flight": (1800, 5.5, 750, 1.5, 1.0), "train": (100, 1.2, 55, 0.5, 1.25),
         "bus": (100, 1.8, 45, 0.5, 1.25), "cab": (0, 14, 50, 0.0, 1.25)}
CLASS_MULT = {"flight": {"premium": 1.5, "business": 2.5, "first": 3.5},
              "train": {"ac": 1.8, "first": 2.2}}


def _km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


@app.post("/api/insights")
def insights():
    """Indicative distance / duration / fare range + 'did you mean' city spelling hints."""
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify(error="Enter a travel sentence first."), 400
    tokens = tokenize(text)
    tags = tag_tokens(tokens)
    attrs = extract_attributes(tokens, tags)

    known = MODES | CLASSES | set(MONTHS) | WEEKDAYS | REL_DATES | RETURN_TRIGGERS | PAX_WORDS \
        | PAX_ADULT_WORDS | PAX_CHILD_WORDS | PAX_INFANT_WORDS | NEG_CONNECTORS
    suggestions = []
    for tok, tag in zip(tokens, tags):
        t = tok.lower()
        if tag == "O" and t.isalpha() and len(t) >= 4 and t not in known and t not in CITIES:
            m = difflib.get_close_matches(t, list(CITIES), n=1, cutoff=0.8)
            if m:
                suggestions.append({"token": tok, "suggest": m[0].title()})

    out = {"suggestions": suggestions, "distance_km": None, "estimates": [], "round_trip": "return_date" in attrs}
    s, d = attrs.get("source", "").lower(), attrs.get("destination", "").lower()
    if s in COORDS and d in COORDS and s != d:
        km = _km(COORDS[s], COORDS[d])
        out["distance_km"] = round(km)
        if "adults" in attrs or "children" in attrs or "infants" in attrs:
            pax = attrs.get("adults", 0) + 0.75 * attrs.get("children", 0) + 0.1 * attrs.get("infants", 0)
        else:
            pax = attrs.get("passengers", 1) if isinstance(attrs.get("passengers", 1), int) else 1
        cls = attrs.get("class", "").lower().split(" ")[0]
        modes = [attrs["mode"]] if attrs.get("mode") in RATES else list(RATES)
        for m in modes:
            base, per_km, speed, over, factor = RATES[m]
            road = km * factor
            fare = (base + per_km * road) * CLASS_MULT.get(m, {}).get(cls, 1) * pax
            if m == "cab":
                fare = per_km * road * 1.0   # a cab is priced per vehicle, not per head
            if out["round_trip"]:
                fare *= 2
            hrs = road / speed + over
            out["estimates"].append({"mode": m, "duration": f"{int(hrs)}h {int(round((hrs % 1) * 60)):02d}m",
                                     "fare_min": int(round(fare * 0.85 / 50) * 50),
                                     "fare_max": int(round(fare * 1.15 / 50) * 50)})
    if str(attrs.get("budget", "")).isdigit():   # NEW (v5): flag modes that fit the budget
        for e in out["estimates"]:
            e["fits_budget"] = e["fare_min"] <= int(attrs["budget"])
    return jsonify(out)


# ===================== v7 EXTRAS: destination guide (places / local food / stay types) =====================
# Indicative only (like the fare estimates above) - a static offline guide, not a live booking API.
_DEST_INFO = {
    "hyderabad": {"country": "India", "region": "Telangana",
        "places": ["Charminar", "Golconda Fort", "Hussain Sagar Lake", "Ramoji Film City"],
        "food": ["Hyderabadi Biryani", "Haleem", "Irani Chai", "Double ka Meetha"],
        "stay_types": ["Business hotel near Hitech City", "Heritage stay near the Old City", "Budget hotel near the railway station"]},
    "delhi": {"country": "India", "region": "Delhi NCR",
        "places": ["Red Fort", "India Gate", "Qutub Minar", "Humayun's Tomb"],
        "food": ["Chole Bhature", "Butter Chicken", "Paranthe Wali Gali food", "Kulfi"],
        "stay_types": ["Heritage hotel near Connaught Place", "Airport-area hotel", "Budget stay in Paharganj"]},
    "mumbai": {"country": "India", "region": "Maharashtra",
        "places": ["Gateway of India", "Marine Drive", "Elephanta Caves", "Juhu Beach"],
        "food": ["Vada Pav", "Pav Bhaji", "Bombay Sandwich", "Bhel Puri"],
        "stay_types": ["Sea-view hotel near Marine Drive", "Business hotel near BKC", "Budget stay near the station"]},
    "bangalore": {"country": "India", "region": "Karnataka",
        "places": ["Lalbagh Botanical Garden", "Bangalore Palace", "Cubbon Park", "ISKCON Temple"],
        "food": ["Masala Dosa", "Filter Coffee", "Bisi Bele Bath", "Mysore Pak"],
        "stay_types": ["Tech-park-area business hotel", "Boutique stay near MG Road", "Budget hotel near the station"]},
    "chennai": {"country": "India", "region": "Tamil Nadu",
        "places": ["Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "DakshinaChitra"],
        "food": ["Idli Sambar", "Chettinad Chicken", "Filter Coffee", "Pongal"],
        "stay_types": ["Beachfront hotel near Marina", "Business hotel in T. Nagar", "Budget stay near Egmore"]},
    "kolkata": {"country": "India", "region": "West Bengal",
        "places": ["Victoria Memorial", "Howrah Bridge", "Dakshineswar Temple", "Indian Museum"],
        "food": ["Macher Jhol", "Kosha Mangsho", "Rosogolla", "Kathi Roll"],
        "stay_types": ["Heritage hotel near Park Street", "Business hotel near Salt Lake", "Budget stay near Howrah"]},
    "vizag": {"country": "India", "region": "Andhra Pradesh",
        "places": ["RK Beach", "Kailasagiri", "Araku Valley", "Submarine Museum"],
        "food": ["Pesarattu", "Royyala Iguru (prawn curry)", "Gongura Mutton", "Filter Coffee"],
        "stay_types": ["Beachfront hotel near RK Beach", "Business hotel near the port area", "Budget stay near the station"]},
    "vijayawada": {"country": "India", "region": "Andhra Pradesh",
        "places": ["Kanaka Durga Temple", "Prakasam Barrage", "Undavalli Caves", "Bhavani Island"],
        "food": ["Pulihora", "Gongura Pachadi", "Andhra Meals", "Pootharekulu"],
        "stay_types": ["Business hotel near Benz Circle", "Budget stay near the railway station"]},
    "tirupati": {"country": "India", "region": "Andhra Pradesh",
        "places": ["Tirumala Venkateswara Temple", "Sri Kapileswara Swamy Temple", "Talakona Waterfalls"],
        "food": ["Tirupati Laddu", "Pongal", "Dosa", "Pulihora"],
        "stay_types": ["TTD guest house near Tirumala", "Budget hotel in town", "Mid-range hotel near the bus stand"]},
    "pune": {"country": "India", "region": "Maharashtra",
        "places": ["Shaniwar Wada", "Aga Khan Palace", "Sinhagad Fort", "Osho Garden"],
        "food": ["Misal Pav", "Puran Poli", "Bakarwadi", "Vada Pav"],
        "stay_types": ["Business hotel near Hinjewadi", "Boutique stay near Koregaon Park", "Budget hotel near the station"]},
    "goa": {"country": "India", "region": "Goa",
        "places": ["Baga Beach", "Fort Aguada", "Basilica of Bom Jesus", "Dudhsagar Falls"],
        "food": ["Goan Fish Curry", "Vindaloo", "Bebinca", "Prawn Balchao"],
        "stay_types": ["Beachfront resort", "Boutique Portuguese-villa stay", "Budget hostel near the beach"]},
    "jaipur": {"country": "India", "region": "Rajasthan",
        "places": ["Hawa Mahal", "Amber Fort", "City Palace", "Jantar Mantar"],
        "food": ["Dal Baati Churma", "Laal Maas", "Ghewar", "Pyaaz Kachori"],
        "stay_types": ["Heritage haveli stay", "Palace-view hotel", "Budget stay near the old city"]},
    "kochi": {"country": "India", "region": "Kerala",
        "places": ["Fort Kochi", "Chinese Fishing Nets", "Mattancherry Palace", "Marine Drive Kochi"],
        "food": ["Kerala Sadya", "Appam with Stew", "Karimeen Fry", "Puttu"],
        "stay_types": ["Backwater-view resort", "Heritage stay in Fort Kochi", "Budget hotel near the harbour"]},
    "ahmedabad": {"country": "India", "region": "Gujarat",
        "places": ["Sabarmati Ashram", "Adalaj Stepwell", "Kankaria Lake", "Jama Masjid"],
        "food": ["Dhokla", "Thepla", "Gujarati Thali", "Fafda-Jalebi"],
        "stay_types": ["Business hotel near SG Highway", "Budget stay near the railway station"]},
    "lucknow": {"country": "India", "region": "Uttar Pradesh",
        "places": ["Bara Imambara", "Rumi Darwaza", "Chota Imambara", "Hazratganj Market"],
        "food": ["Lucknowi Biryani", "Tunday Kababi", "Sheermal", "Kulfi Falooda"],
        "stay_types": ["Heritage hotel near Hazratganj", "Budget stay near the station"]},
    "guwahati": {"country": "India", "region": "Assam",
        "places": ["Kamakhya Temple", "Umananda Island", "Brahmaputra River Cruise"],
        "food": ["Assamese Thali", "Masor Tenga", "Pitha", "Khar"],
        "stay_types": ["Riverside hotel", "Budget stay near Paltan Bazaar"]},
    "bhubaneswar": {"country": "India", "region": "Odisha",
        "places": ["Lingaraj Temple", "Udayagiri & Khandagiri Caves", "Nandankanan Zoo"],
        "food": ["Dalma", "Pakhala", "Chhena Poda", "Macha Ghanta"],
        "stay_types": ["Business hotel near the airport", "Budget stay near the station"]},
    "coimbatore": {"country": "India", "region": "Tamil Nadu",
        "places": ["Marudamalai Temple", "VOC Park", "Black Thunder theme park"],
        "food": ["Kongunadu Chicken Curry", "Filter Coffee", "Idiyappam"],
        "stay_types": ["Business hotel near Race Course", "Budget stay near the station"]},
    "nagpur": {"country": "India", "region": "Maharashtra",
        "places": ["Deekshabhoomi", "Sitabuldi Fort", "Futala Lake"],
        "food": ["Saoji Mutton", "Tarri Poha", "Orange Burfi"],
        "stay_types": ["Business hotel near Civil Lines", "Budget stay near the station"]},
    "patna": {"country": "India", "region": "Bihar",
        "places": ["Golghar", "Patna Sahib Gurudwara", "Mahavir Mandir"],
        "food": ["Litti Chokha", "Sattu Paratha", "Khaja"],
        "stay_types": ["Business hotel near Fraser Road", "Budget stay near the station"]},
    "dubai": {"country": "UAE", "region": "Dubai",
        "places": ["Burj Khalifa", "Dubai Mall", "Palm Jumeirah", "Dubai Desert Safari"],
        "food": ["Shawarma", "Al Machboos", "Luqaimat", "Hummus with Khubz"],
        "stay_types": ["Beachfront resort on Jumeirah", "Downtown business hotel", "Budget hotel in Deira"]},
    "singapore": {"country": "Singapore", "region": "Singapore",
        "places": ["Marina Bay Sands", "Gardens by the Bay", "Sentosa Island", "Merlion Park"],
        "food": ["Hainanese Chicken Rice", "Laksa", "Chilli Crab", "Satay"],
        "stay_types": ["Marina Bay view hotel", "Boutique stay in Chinatown", "Budget hostel near Bugis"]},
    "london": {"country": "United Kingdom", "region": "England",
        "places": ["Big Ben", "Tower of London", "British Museum", "London Eye"],
        "food": ["Fish and Chips", "Sunday Roast", "Full English Breakfast", "Afternoon Tea"],
        "stay_types": ["Hotel near Westminster", "Boutique stay in Covent Garden", "Budget hostel near King's Cross"]},
    "paris": {"country": "France", "region": "Ile-de-France",
        "places": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Montmartre"],
        "food": ["Croissant", "Coq au Vin", "Crepes", "French Onion Soup"],
        "stay_types": ["Hotel near the Champs-Elysees", "Boutique stay in Le Marais", "Budget hostel near Gare du Nord"]},
    "new york": {"country": "USA", "region": "New York",
        "places": ["Statue of Liberty", "Central Park", "Times Square", "Empire State Building"],
        "food": ["New York Bagel", "Pizza Slice", "Cheesecake", "Pastrami Sandwich"],
        "stay_types": ["Hotel in Midtown Manhattan", "Boutique stay in Brooklyn", "Budget hostel near Queens"]},
    "bangkok": {"country": "Thailand", "region": "Bangkok",
        "places": ["Grand Palace", "Wat Arun", "Chatuchak Market", "Khao San Road"],
        "food": ["Pad Thai", "Tom Yum Soup", "Mango Sticky Rice", "Green Curry"],
        "stay_types": ["Riverside hotel", "Boutique stay near Sukhumvit", "Budget hostel near Khao San"]},
    "colombo": {"country": "Sri Lanka", "region": "Western Province",
        "places": ["Galle Face Green", "Gangaramaya Temple", "Independence Square"],
        "food": ["Rice and Curry", "Kottu Roti", "Hoppers", "Watalappam"],
        "stay_types": ["Beachfront hotel", "Business hotel in Colombo Fort", "Budget guesthouse"]},
    "kathmandu": {"country": "Nepal", "region": "Bagmati",
        "places": ["Pashupatinath Temple", "Boudhanath Stupa", "Durbar Square", "Swayambhunath"],
        "food": ["Momos", "Dal Bhat", "Newari Khaja Set", "Thukpa"],
        "stay_types": ["Heritage stay near Thamel", "Budget guesthouse", "Mid-range hotel near Durbar Square"]},
}
# aliases that extraction can produce but aren't separate guide entries
_DEST_ALIAS = {"new delhi": "delhi", "bengaluru": "bangalore", "visakhapatnam": "vizag"}


@app.get("/api/destination")
def destination():
    """Offline destination guide for the extracted city: country/region, a
    few well-known places, local food, and the kind of stay that suits the
    trip. Indicative only, like the fare estimates above - not a live
    places/hotel API."""
    raw = (request.args.get("city") or "").strip().lower()
    key = _DEST_ALIAS.get(raw, raw)
    info = _DEST_INFO.get(key)  
    if not info:
        return jsonify(found=False, city=request.args.get("city", ""))
    return jsonify(found=True, city=raw.title(), **info)


if __name__ == "__main__":
    app.run(port=5000, debug=True)