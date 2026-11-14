#!/usr/bin/env python3
"""Übernimmt Depot-Änderungen aus der App.

Die App öffnet ein GitHub-Issue mit dem Titel „Depot-Update“ und einem JSON-Text
{"add": ["NVDA", "Infineon"], "remove": ["SOFI"]}. Dieses Skript liest alle offenen
Issues dieses Titels, die vom Besitzer (LucciArch) stammen, wendet sie der Reihe nach
auf data/portfolio.json an, kommentiert und schließt sie.
Issues von anderen Personen werden ignoriert (das Repo ist öffentlich).

Aufruf:  python3 scripts/apply_depot_updates.py [--file data/portfolio.json] [--dry-run]
Benötigt die gh-CLI mit Zugriff auf LucciArch/boersen-briefing.
"""
import argparse, json, re, subprocess, datetime

REPO = "LucciArch/boersen-briefing"
OWNER = "LucciArch"
OK = re.compile(r"^[\w .&\-]{1,40}$", re.UNICODE)

def gh(*args, data=None):
    cmd = ["gh", "api", *args]
    out = subprocess.run(cmd, input=data, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or out.stdout.strip())
    return json.loads(out.stdout) if out.stdout.strip() else None

def parse(body):
    m = re.search(r"\{.*\}", body or "", re.S)
    if not m: raise ValueError("kein JSON im Text gefunden")
    d = json.loads(m.group(0))
    add = [str(x).strip() for x in d.get("add", []) if str(x).strip()]
    rem = [str(x).strip() for x in d.get("remove", []) if str(x).strip()]
    bad = [x for x in add + rem if not OK.match(x)]
    if bad: raise ValueError("ungültige Einträge: " + ", ".join(bad))
    return add, rem

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--file", default="data/portfolio.json"); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    pf = json.load(open(a.file))
    issues = gh(f"repos/{REPO}/issues?state=open&per_page=50&sort=created&direction=asc")
    todo = [i for i in issues if not i.get("pull_request") and i["title"].strip().lower().startswith("depot-update")]
    summary = []
    for i in todo:
        if i["user"]["login"].lower() != OWNER.lower():
            print(f"#{i['number']} ignoriert (von {i['user']['login']})"); continue
        try:
            add, rem = parse(i["body"])
        except Exception as e:
            msg = f"Konnte nicht übernommen werden: {e}"
            print(f"#{i['number']} {msg}")
            if not a.dry_run:
                gh(f"repos/{REPO}/issues/{i['number']}/comments", "-f", f"body={msg}")
            continue
        pos = pf["positions"]
        removed = []
        for r in rem:
            before = len(pos)
            pos[:] = [p for p in pos if p["ticker"].upper() != r.upper() and (p.get("name") or "").upper() != r.upper()]
            if len(pos) < before: removed.append(r)
        added = []
        for x in add:
            if any(p["ticker"].upper() == x.upper() or (p.get("name") or "").upper() == x.upper() for p in pos): continue
            if len(pos) >= 50: break
            # Kurze Eingaben sind Kürzel, längere Firmennamen; das Symbol löst scripts/charts.py auf
            pos.append({"ticker": x.upper() if len(x) <= 6 and " " not in x else x, "symbol": "", "name": x, "type": ""})
            added.append(x)
        pf["updated"] = datetime.date.today().isoformat()
        msg = f"Übernommen. Neu: {', '.join(added) or '–'} · Entfernt: {', '.join(removed) or '–'}. Ab dem nächsten Briefing gilt das neue Depot ({len(pos)} Positionen)."
        summary.append(msg); print(f"#{i['number']} {msg}")
        if not a.dry_run:
            gh(f"repos/{REPO}/issues/{i['number']}/comments", "-f", f"body={msg}")
            gh(f"repos/{REPO}/issues/{i['number']}", "-X", "PATCH", "-f", "state=closed")
    if not a.dry_run:
        json.dump(pf, open(a.file, "w"), ensure_ascii=False, indent=1)
    print(f"{len(summary)} Depot-Update(s) übernommen; Depot hat {len(pf['positions'])} Positionen.")

if __name__ == "__main__":
    main()
