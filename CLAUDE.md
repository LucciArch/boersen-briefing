# Börsen-Briefing – Regeln für die tägliche Aufgabe

Diese Datei ergänzt den Prompt der geplanten Aufgabe „Börsen-Briefing“. Wo sie dem
Prompt widerspricht, gilt diese Datei (Luca hat das so festgelegt). Alle übrigen
Regeln des Prompts gelten unverändert, vor allem das Prüfprotokoll und
„Genauigkeit vor Vollständigkeit“.

## Chancen der Woche je Branche (ersetzt Abschnitt 2 „Chance der Woche“)

Wann: sonntags, oder wenn data/opportunity.json älter als 7 Tage ist, oder wenn
dort noch kein Pick ein Feld "sector" hat.

Was: je Branche EINE Aktie, die NICHT im Depot ist, als Idee für einen möglichen
Neueinstieg. Ziel sind 6 Picks in dieser Reihenfolge, mit genau diesen Werten für
"sector":
1. "Technologie"
2. "Gesundheit & Pharma"
3. "Finanzen"
4. "Industrie"
5. "Konsum (zyklisch)" oder "Basiskonsum"
6. "Energie" oder "Rohstoffe"

Findet sich für eine Branche kein Kandidat, der alle Kriterien und das
Prüfprotokoll erfüllt, die Branche weglassen (lieber 4 gute als 6 schwache Picks).

- Kandidaten: große, liquide Aktien (USA/Europa, Börsenwert > 10 Mrd. $; keine
  Pennystocks, keine Hebelprodukte, keine Pump-Verdachtsfälle) mit frischem,
  bestätigtem positivem Anlass.
- Technischer Filter mit charts.analyze(ticker, yahoo_symbol, name, 'Aktie') für
  3–6 Kandidaten je Branche (bevorzugt: Kurs über 200-Tage-Schnitt, MACD positiv,
  RSI nicht über 70, Analysten-Kursziel deutlich über Kurs).
- Fakten jeder Begründung mit ≥2 unabhängigen Quellen prüfen; der unabhängige
  Faktencheck umfasst alle Picks.
- data/opportunity.json: wie im Prompt beschrieben, aber jeder Pick bekommt
  zusätzlich als erstes Feld "sector":
  {"week", "updated", "method", "picks": [{"sector", "ticker", "symbol", "name",
  "type", "headline", "strength", "why", "risks", "entry", "stop", "targets",
  "horizon", "sources"}]}
- Danach `python3 scripts/charts.py` laufen lassen (es lädt alle Picks mit).
- In der Endnachricht die Chancen kurz als „Branche: Name“ nennen.

## ETFs im Depot

Fehlen bei einem ETF in data/portfolio.json die Felder "sector" (z. B.
"Breiter Index (MSCI World)", "Technologie", "Rohstoffe", "Energie") oder
"region" ("USA", "Europa", "Welt", "China", "Schwellenländer"), nach Prüfung der
offiziellen ETF-Beschreibung eintragen. Bei Aktien liefert charts.py Branche und
Region automatisch.

## Nicht ändern

Die Aufgabe ändert nur Dateien in data/. Nie index.html, sw.js, manifest, icons,
vendor/, scripts/ oder diese Datei.
