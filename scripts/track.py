#!/usr/bin/env python3
"""Trefferquote der „Chancen der Woche“.

Merkt sich jede Chance aus data/opportunity.json mit dem Kurs, zu dem man sie nach
der Veröffentlichung hätte kaufen können (Eröffnungskurs des ersten Handelstags ab
dem Veröffentlichungsdatum), und vergleicht die Entwicklung mit dem S&P 500 (SPY):
laufend, nach 4 Wochen (20 Handelstage) und nach 12 Wochen (60 Handelstage).
Dividenden und Wechselkurse sind nicht berücksichtigt (Kursentwicklung in Handelswährung).

Aufruf:  python3 scripts/track.py [--file data/track.json]
Nur Standardbibliothek, nutzt die Kursabfrage aus scripts/charts.py.
"""
import argparse, datetime, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charts  # noqa: E402

OPP = "data/opportunity.json"
BENCH = "SPY"
HORIZONS = {"4w": 20, "12w": 60}


def add_picks(track, opp):
    """Neue Picks aus opportunity.json aufnehmen (einmal je Woche und Ticker)."""
    have = {p["id"] for p in track["picks"]}
    created = (opp.get("updated") or datetime.date.today().isoformat())[:10]
    added = []
    for p in opp.get("picks", []):
        if not p.get("ticker") or not p.get("why"):
            continue
        pid = f"{opp.get('week', created)}|{p['ticker'].upper()}"
        if pid in have:
            continue
        track["picks"].append({"id": pid, "week": opp.get("week"), "created": created, "sector": p.get("sector"),
                               "ticker": p["ticker"], "symbol": p.get("symbol") or "", "name": p.get("name") or p["ticker"],
                               "strength": p.get("strength")})
        have.add(pid); added.append(p["ticker"])
    return added


def series(sym, cache):
    if sym not in cache:
        _, c = charts.candles(sym)
        cache[sym] = c
        time.sleep(0.3)
    return cache[sym]


def first_index(c, date):
    for i, x in enumerate(c):
        if x[0] >= date:
            return i
    return None


def evaluate(p, cache):
    if not p.get("symbol"):
        sym, _, _ = charts.resolve(p["ticker"])
        if not sym:
            raise ValueError("Symbol nicht gefunden")
        p["symbol"] = sym
    c, b = series(p["symbol"], cache), series(BENCH, cache)
    i, j = first_index(c, p["created"]), first_index(b, p["created"])
    if i is None or j is None:
        p["status"] = "wartet auf ersten Handelstag"
        return
    p["entry_date"], p["entry"] = c[i][0], round(c[i][1], 4)          # Eröffnungskurs
    p["bench_entry"] = round(b[j][1], 4)
    p["last_date"], p["last"] = c[-1][0], round(c[-1][4], 4)
    p["ret"] = round(c[-1][4] / c[i][1] - 1, 4)
    p["bench_ret"] = round(b[-1][4] / b[j][1] - 1, 4)
    p["excess"] = round(p["ret"] - p["bench_ret"], 4)
    p["days"] = len(c) - 1 - i
    for k, n in HORIZONS.items():
        if i + n < len(c):
            # Vergleichstag beim SPY: gleicher Kalendertag wie beim Pick (oder der nächste Handelstag)
            jj = first_index(b, c[i + n][0])
            if jj is None:
                continue
            r, br = c[i + n][4] / c[i][1] - 1, b[jj][4] / b[j][1] - 1
            p[k] = {"date": c[i + n][0], "ret": round(r, 4), "bench": round(br, 4), "excess": round(r - br, 4)}
    p["status"] = "abgeschlossen" if "12w" in p else "läuft"


def stats(picks):
    out = {}
    for k in ["now", *HORIZONS]:
        rows = [(p["ret"], p["bench_ret"]) for p in picks if "ret" in p] if k == "now" else \
               [(p[k]["ret"], p[k]["bench"]) for p in picks if k in p]
        if not rows:
            out[k] = {"n": 0}
            continue
        n = len(rows)
        out[k] = {"n": n,
                  "beat": sum(1 for r, b in rows if r > b), "positive": sum(1 for r, _ in rows if r > 0),
                  "hit_rate": round(sum(1 for r, b in rows if r > b) / n, 4),
                  "avg_ret": round(sum(r for r, _ in rows) / n, 4), "avg_bench": round(sum(b for _, b in rows) / n, 4),
                  "avg_excess": round(sum(r - b for r, b in rows) / n, 4)}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--file", default="data/track.json"); a = ap.parse_args()
    track = json.load(open(a.file)) if os.path.exists(a.file) else {"picks": []}
    added = add_picks(track, json.load(open(OPP))) if os.path.exists(OPP) else []
    cache, errors = {}, []
    for p in track["picks"]:
        try:
            evaluate(p, cache)
        except Exception as e:
            errors.append(f"{p['ticker']}: {e}"); print("ERR", p["ticker"], e)
    track["picks"].sort(key=lambda p: (p["created"], p["id"]), reverse=True)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    track.update({"updated": now.isoformat(timespec="minutes"), "benchmark": f"S&P 500 ({BENCH})",
                  "method": "Einstieg zum Eröffnungskurs des ersten Handelstags ab Veröffentlichung; Vergleich mit dem S&P-500-ETF SPY "
                            "über denselben Zeitraum; Kursentwicklung in Handelswährung, ohne Dividenden und Gebühren.",
                  "stats": stats(track["picks"]), "errors": errors})
    json.dump(track, open(a.file, "w"), ensure_ascii=False, indent=1)
    print(f"{len(track['picks'])} Picks ({len(added)} neu: {', '.join(added) or '–'}), {len(errors)} Fehler -> {a.file}")


if __name__ == "__main__":
    main()
