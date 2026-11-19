#!/usr/bin/env python3
"""Chartanalyse für das Börsen-Briefing.

Lädt 1 Jahr Tageskerzen (Yahoo Finance) für jede Depot-Position, berechnet
gleitende Durchschnitte, RSI, MACD, Unterstützungen/Widerstände, einen
statistischen Schwankungskorridor für die nächsten 20 Handelstage und
Analysten-Kursziele, Branche/Land sowie Euro-Wechselkurse, und schreibt alles nach data/charts.json.

Aufruf:  python3 scripts/charts.py [--out data/charts.json]
Nur Standardbibliothek. Keine Anlageberatung.
"""
import argparse, json, math, time, datetime, urllib.request, urllib.parse, http.cookiejar, statistics, os

POSITIONS_FILE = "data/portfolio.json"      # Depot (wird über die App / den Tageslauf gepflegt)
OPPORTUNITY_FILE = "data/opportunity.json"  # Chance der Woche (optional)
UA = {"User-Agent": "Mozilla/5.0"}
HORIZON = 20  # Handelstage für den Korridor (~1 Monat)

# ---------- Daten laden ----------
_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))
_crumb = None

def get(url, timeout=25, tries=3):
    for i in range(tries):
        try:
            return _opener.open(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:
            err = e
            time.sleep(2 + 3 * i)
    raise err

def resolve(query):
    """Yahoo-Symbol zu einem Ticker oder Firmennamen finden (Aktien und ETFs)."""
    j = json.loads(get("https://query2.finance.yahoo.com/v1/finance/search?q=" + urllib.parse.quote(query) + "&quotesCount=6&newsCount=0"))
    qs = [q for q in j.get("quotes", []) if q.get("quoteType") in ("EQUITY", "ETF")]
    if not qs: return None, None, None
    exact = [q for q in qs if q["symbol"].upper() == query.upper()]
    q = (exact or qs)[0]
    return q["symbol"], q.get("longname") or q.get("shortname") or query, "ETF" if q.get("quoteType") == "ETF" else "Aktie"

def candles(sym):
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2y&includePrePost=false"))
    r = j["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = []
    for i, ts in enumerate(r.get("timestamp") or []):
        o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, l, c):
            continue
        d = datetime.datetime.fromtimestamp(ts + r["meta"].get("gmtoffset", 0), datetime.timezone.utc).date().isoformat()
        if out and out[-1][0] == d:
            out[-1] = [d, o, h, l, c, v or 0]
        else:
            out.append([d, o, h, l, c, v or 0])
    return r["meta"], out

SECTOR_DE = {"Technology": "Technologie", "Communication Services": "Kommunikation & Medien", "Consumer Cyclical": "Konsum (zyklisch)",
             "Consumer Defensive": "Basiskonsum", "Healthcare": "Gesundheit & Pharma", "Financial Services": "Finanzen", "Industrials": "Industrie",
             "Energy": "Energie", "Basic Materials": "Rohstoffe", "Utilities": "Versorger", "Real Estate": "Immobilien"}
EUROPE = {"Germany", "France", "Netherlands", "Switzerland", "United Kingdom", "Ireland", "Italy", "Spain", "Denmark", "Sweden", "Norway",
          "Finland", "Belgium", "Austria", "Luxembourg", "Portugal", "Poland"}

def region_of(country):
    if not country: return None
    if country == "United States": return "USA"
    if country in EUROPE: return "Europa"
    if country in ("China", "Hong Kong"): return "China"
    return {"Japan": "Japan", "Canada": "Kanada", "Taiwan": "Taiwan", "South Korea": "Südkorea", "India": "Indien"}.get(country, "Andere")

def summary(sym):
    """Analysten-Kursziele und Firmenprofil (Branche, Land, Börsenwert) von Yahoo. Fehler -> (None, {})."""
    global _crumb
    try:
        if _crumb is None:
            try: get("https://fc.yahoo.com", tries=1)
            except Exception: pass
            _crumb = get("https://query2.finance.yahoo.com/v1/test/getcrumb").decode().strip()
        j = json.loads(get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=financialData,assetProfile,price&crumb={_crumb}"))
        res = j["quoteSummary"]["result"][0]
    except Exception:
        return None, {}
    f, ap, pr = res.get("financialData") or {}, res.get("assetProfile") or {}, res.get("price") or {}
    prof = {k: v for k, v in {"sector": SECTOR_DE.get(ap.get("sector"), ap.get("sector")), "industry": ap.get("industry"),
            "country": ap.get("country"), "region": region_of(ap.get("country")),
            "market_cap": (pr.get("marketCap") or {}).get("raw")}.items() if v}
    g = lambda k: (f.get(k) or {}).get("raw")
    n = g("numberOfAnalystOpinions")
    tgt = None
    if n and g("targetMeanPrice"):
        tgt = {"mean": g("targetMeanPrice"), "median": g("targetMedianPrice"), "high": g("targetHighPrice"),
               "low": g("targetLowPrice"), "n": n, "rec": f.get("recommendationKey")}
    return tgt, prof

def targets(sym):
    return summary(sym)[0]

def fx_rates():
    """Wechselkurse: Wert von 1 Einheit Fremdwährung in Euro, letzter Kurs + Tagesreihe (1 Jahr)."""
    out = {}
    for cur, pair in (("USD", "EURUSD=X"), ("HKD", "EURHKD=X"), ("GBP", "EURGBP=X"), ("CHF", "EURCHF=X")):
        try:
            _, c = candles(pair)
            ser = [[x[0], round(1 / x[4], 6)] for x in c[-260:] if x[4]]
            out[cur] = {"last": ser[-1][1], "date": ser[-1][0], "series": ser}
        except Exception as e:
            print("ERR fx", cur, e)
        time.sleep(0.3)
    return out

# ---------- Indikatoren ----------
def sma(vals, n):
    out, s = [], 0.0
    for i, v in enumerate(vals):
        s += v
        if i >= n: s -= vals[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out

def ema(vals, n):
    k, out, e = 2 / (n + 1), [], None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out

def rsi(closes, n=14):
    out = [None] * len(closes)
    if len(closes) <= n: return out
    gains = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for i in range(n, len(closes)):
        if i > n:
            ag = (ag * (n - 1) + gains[i - 1]) / n
            al = (al * (n - 1) + losses[i - 1]) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out

def atr(c, n=14):
    trs = [c[0][2] - c[0][3]] + [max(c[i][2] - c[i][3], abs(c[i][2] - c[i - 1][4]), abs(c[i][3] - c[i - 1][4])) for i in range(1, len(c))]
    return sum(trs[-n:]) / min(n, len(trs))

def levels(c, price, a):
    """Unterstützungen/Widerstände aus Wendepunkten (Swing-Hochs/-Tiefs), geclustert."""
    w = 5
    piv = []
    for i in range(w, len(c) - w):
        hi, lo = c[i][2], c[i][3]
        if hi == max(x[2] for x in c[i - w:i + w + 1]): piv.append((hi, i))
        if lo == min(x[3] for x in c[i - w:i + w + 1]): piv.append((lo, i))
    tol = max(a * 0.6, price * 0.012)
    clusters = []
    for p, i in sorted(piv):
        if clusters and p - clusters[-1]["max"] <= tol:
            cl = clusters[-1]; cl["pts"].append((p, i)); cl["max"] = p
        else:
            clusters.append({"pts": [(p, i)], "max": p})
    n = len(c)
    res = []
    for cl in clusters:
        ps = [p for p, _ in cl["pts"]]
        lvl = statistics.median(ps)
        touches = len(ps)
        recency = max(i for _, i in cl["pts"]) / n
        res.append({"price": round(lvl, 4), "touches": touches, "score": touches + 2 * recency})
    sup = sorted([r for r in res if r["price"] < price * 0.995], key=lambda r: -r["price"])
    rst = sorted([r for r in res if r["price"] > price * 1.005], key=lambda r: r["price"])
    def pick(lst):
        # Zonen im Umkreis von 30 %: nächste zuerst; Einzel-Berührungen nur, wenn sonst <2 Zonen
        near = [r for r in lst if abs(r["price"] / price - 1) <= 0.30] or lst[:1]
        out = []
        for r in near:
            if r["touches"] >= 2 or len([x for x in near if x["touches"] >= 2]) < 2:
                out.append(r)
            if len(out) == 3: break
        # zu dicht beieinander liegende Zonen (< 1 ATR) zusammenfassen
        merged = []
        for r in out:
            if merged and abs(r["price"] - merged[-1]["price"]) < a: continue
            merged.append(r)
        return merged
    def fmt(r):
        return {"price": r["price"], "touches": r["touches"], "dist_pct": round((r["price"] / price - 1) * 100, 1),
                "strength": "stark" if r["touches"] >= 3 else "mittel" if r["touches"] == 2 else "schwach"}
    return [fmt(r) for r in pick(sup)], [fmt(r) for r in pick(rst)]

def next_trading_days(last_iso, k):
    d = datetime.date.fromisoformat(last_iso); out = []
    while len(out) < k:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5: out.append(d.isoformat())
    return out

def fmtp(x, cur):
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + {"USD": " $", "EUR": " €", "HKD": " HK$"}.get(cur, " " + cur)

# ---------- Analyse ----------
def analyze(disp, sym, name, typ):
    meta, c = candles(sym)
    cur = meta.get("currency", "USD")
    closes = [x[4] for x in c]
    price, prev = closes[-1], closes[-2]
    s20, s50, s200 = sma(closes, 20), sma(closes, 50), sma(closes, 200)
    r = rsi(closes)
    m_fast, m_slow = ema(closes, 12), ema(closes, 26)
    macd = [a - b for a, b in zip(m_fast, m_slow)]
    sig = ema(macd, 9)
    a = atr(c)
    Y = min(252, len(c))                      # letztes Jahr für Zonen, Hoch/Tief und Anzeige
    cy = c[-Y:]
    sup, res = levels(cy, price, a)
    hi52, lo52 = max(x[2] for x in cy), min(x[3] for x in cy)
    if not res and hi52 > price * 1.005:
        res = [{"price": round(hi52, 4), "touches": 1, "dist_pct": round((hi52 / price - 1) * 100, 1), "strength": "52-Wochen-Hoch"}]
    if not sup and lo52 < price * 0.995:
        sup = [{"price": round(lo52, 4), "touches": 1, "dist_pct": round((lo52 / price - 1) * 100, 1), "strength": "52-Wochen-Tief"}]
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(len(closes) - 60, len(closes))]
    sd = statistics.stdev(rets)
    days = next_trading_days(c[-1][0], HORIZON)
    cone = [{"t": d, "u1": round(price * math.exp(sd * math.sqrt(k)), 4), "d1": round(price * math.exp(-sd * math.sqrt(k)), 4),
             "u2": round(price * math.exp(2 * sd * math.sqrt(k)), 4), "d2": round(price * math.exp(-2 * sd * math.sqrt(k)), 4)}
            for k, d in enumerate(days, 1)]
    tgt, prof = summary(sym) if typ == "Aktie" else (None, {})

    # --- Bewertung der Signale ---
    pts, notes = 0, []
    v50, v200, vr, vm, vs = s50[-1], s200[-1], r[-1], macd[-1], sig[-1]
    if v200:
        if price > v200: pts += 1; notes.append(f"Kurs über dem 200-Tage-Schnitt ({fmtp(v200, cur)}) – langfristiger Aufwärtstrend intakt")
        else: pts -= 1; notes.append(f"Kurs unter dem 200-Tage-Schnitt ({fmtp(v200, cur)}) – langfristig angeschlagen")
    if v50 and v200:
        if v50 > v200: pts += 1
        else: pts -= 1
        # Golden/Death Cross in den letzten 15 Tagen?
        for i in range(max(1, len(c) - 15), len(c)):
            if s50[i - 1] and s200[i - 1] and s50[i] and s200[i]:
                if s50[i - 1] <= s200[i - 1] and s50[i] > s200[i]: notes.append(f"Golden Cross am {c[i][0][8:10]}.{c[i][0][5:7]}. (50-Tage-Linie steigt über 200-Tage-Linie) – gilt als positives Signal")
                if s50[i - 1] >= s200[i - 1] and s50[i] < s200[i]: notes.append(f"Death Cross am {c[i][0][8:10]}.{c[i][0][5:7]}. (50-Tage-Linie fällt unter 200-Tage-Linie) – gilt als negatives Signal")
    if vm > vs: pts += 1; macd_txt = "MACD über Signallinie – Momentum positiv"
    else: pts -= 1; macd_txt = "MACD unter Signallinie – Momentum negativ"
    if macd[-2] <= sig[-2] and vm > vs: macd_txt = "MACD hat gerade nach oben gekreuzt – frisches Kaufsignal (technisch)"
    if macd[-2] >= sig[-2] and vm < vs: macd_txt = "MACD hat gerade nach unten gekreuzt – frisches Verkaufssignal (technisch)"
    if vr is not None:
        if vr >= 70: pts -= 1; rsi_txt = f"RSI {vr:.0f}: überkauft – Rücksetzer wahrscheinlicher"
        elif vr <= 30: pts += 1; rsi_txt = f"RSI {vr:.0f}: überverkauft – Gegenbewegung möglich"
        elif vr >= 55: rsi_txt = f"RSI {vr:.0f}: kräftig, aber nicht überhitzt"
        elif vr <= 45: rsi_txt = f"RSI {vr:.0f}: eher schwach"
        else: rsi_txt = f"RSI {vr:.0f}: neutral"
    else:
        rsi_txt = "RSI: zu wenig Daten"
    tone = "positiv" if pts >= 2 else "negativ" if pts <= -2 else "neutral"

    pct = lambda x: f"{(x / price - 1) * 100:+.1f} %".replace(".", ",")
    up1m, dn1m, up2m, dn2m = cone[-1]["u1"], cone[-1]["d1"], cone[-1]["u2"], cone[-1]["d2"]
    s1 = sup[0]["price"] if sup else dn1m
    r1 = res[0]["price"] if res else up1m
    if len(sup) > 1: s2, s2_txt = sup[1]["price"], "die nächste Unterstützung"
    elif v200 and v200 < s1 * 0.99: s2, s2_txt = v200, "der 200-Tage-Schnitt"
    else: s2, s2_txt = dn2m, "die untere Grenze des statistischen 95-%-Korridors"
    if len(res) > 1: r2, r2_txt = res[1]["price"], "der nächste Widerstand"
    elif hi52 > r1 * 1.02: r2, r2_txt = hi52, "das 52-Wochen-Hoch"
    else: r2, r2_txt = up2m, "die obere Grenze des statistischen 95-%-Korridors (darüber kein Widerstand aus dem Chart)"
    scen = {
        "bull": {"title": "Ausbruch nach oben",
                 "text": f"Schließt der Kurs über {fmtp(r1, cur)} ({pct(r1)}), ist {r2_txt} bei {fmtp(r2, cur)} ({pct(r2)}) das nächste Ziel."
                         + (f" Analysten sehen im Schnitt {fmtp(tgt['mean'], cur)} ({pct(tgt['mean'])})." if tgt else "")},
        "base": {"title": "Seitwärts",
                 "text": f"Zwischen {fmtp(s1, cur)} und {fmtp(r1, cur)} liegt die aktuelle Handelsspanne. Statistisch liegt der Kurs in 1 Monat mit ~68 % Wahrscheinlichkeit zwischen {fmtp(dn1m, cur)} und {fmtp(up1m, cur)}."},
        "bear": {"title": "Bruch nach unten",
                 "text": f"Fällt der Kurs unter {fmtp(s1, cur)} ({pct(s1)}), ist {s2_txt} bei {fmtp(s2, cur)} ({pct(s2)}) die nächste Auffanglinie."},
    }
    first = cy[0][0]
    cut = lambda arr: [[c[i][0], round(v, 4 if arr is not r else 1)] for i, v in enumerate(arr) if v is not None and c[i][0] >= first]
    item = {
        "ticker": disp, "symbol": sym, "name": name, "type": typ, "currency": cur,
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "date": c[-1][0], "last": round(price, 4), "change_pct": round((price / prev - 1) * 100, 2),
        "candles": [[x[0], round(x[1], 4), round(x[2], 4), round(x[3], 4), round(x[4], 4)] for x in cy],
        "sma20": cut(s20), "sma50": cut(s50), "sma200": cut(s200), "rsi": cut(r),
        "supports": sup, "resistances": res,
        "high52": round(hi52, 4), "low52": round(lo52, 4),
        "atr": round(a, 4), "vol_daily_pct": round(sd * 100, 2),
        "cone": cone, "target": tgt, **prof,
        "analysis": {"tone": tone, "score": pts, "points": notes, "rsi": rsi_txt, "macd": macd_txt,
                     "perf": {"1M": round((price / closes[-22] - 1) * 100, 1) if len(closes) > 22 else None,
                              "3M": round((price / closes[-64] - 1) * 100, 1) if len(closes) > 64 else None,
                              "1J": round((price / closes[-Y] - 1) * 100, 1)},
                     "scenarios": scen},
    }
    return item

def load_positions():
    pf = json.load(open(POSITIONS_FILE))
    pos = [dict(p, group="depot") for p in pf["positions"]]
    if os.path.exists(OPPORTUNITY_FILE):
        op = json.load(open(OPPORTUNITY_FILE))
        for p in op.get("picks", []):
            if not any(x.get("ticker") == p.get("ticker") for x in pos):
                pos.append({"ticker": p["ticker"], "symbol": p.get("symbol", ""), "name": p.get("name", p["ticker"]), "type": p.get("type", "Aktie"), "group": "chance"})
                if p.get("sector"): pos[-1]["sector"] = p["sector"]
    return pf, pos

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="data/charts.json"); a = ap.parse_args()
    pf, pos = load_positions()
    items, errors, resolved = [], [], False
    for p in pos:
        try:
            if not p.get("symbol"):
                sym, nm, ty = resolve(p["ticker"] if p["ticker"] else p["name"])
                if not sym: raise ValueError("Symbol nicht gefunden")
                p["symbol"], p["type"] = sym, p.get("type") or ty
                if not p.get("name") or p["name"] == p["ticker"]: p["name"] = nm
                resolved = True
            it = analyze(p["ticker"], p["symbol"], p["name"], p.get("type") or "Aktie")
            it["group"] = p["group"]
            for k in ("sector", "region", "sp500"):   # Angaben aus portfolio.json/opportunity.json (v. a. für ETFs) haben Vorrang
                if p.get(k) is not None: it[k] = p[k]
            items.append(it); print("ok ", p["ticker"], p["symbol"])
        except Exception as e:
            errors.append(f"{p['ticker']}: {e}"); print("ERR", p["ticker"], e)
        time.sleep(0.4)
    if resolved:  # gefundene Symbole ins Depot zurückschreiben
        by = {p["ticker"]: p for p in pos if p["group"] == "depot"}
        pf["positions"] = [dict(q, symbol=by.get(q["ticker"], q).get("symbol", ""), name=by.get(q["ticker"], q).get("name", q["name"]), type=by.get(q["ticker"], q).get("type", q.get("type"))) for q in pf["positions"]]
        json.dump(pf, open(POSITIONS_FILE, "w"), ensure_ascii=False, indent=1)
    fx = fx_rates()
    if len(fx) < 3: errors.append("Wechselkurse unvollständig: " + ", ".join(fx) or "keine")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    json.dump({"updated": now.isoformat(timespec="minutes"), "updated_label": now.strftime("%d.%m.%Y, %H:%M Uhr"),
               "source": "Yahoo Finance (Tageskerzen, Schlusskurse; Analysten-Kursziele)", "errors": errors, "fx": fx, "items": items},
              open(a.out, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(items)} Werte, {len(errors)} Fehler -> {a.out}")

if __name__ == "__main__":
    main()
