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

## Trefferquote (jeden Tag)

Nach `python3 scripts/charts.py` immer `python3 scripts/track.py` ausführen. Es
nimmt neue Chancen der Woche in data/track.json auf und rechnet aus, wie sie sich
im Vergleich zum S&P 500 entwickelt haben (laufend, nach 4 und 12 Wochen).
data/track.json nie von Hand ändern und nie Einträge löschen – die Bilanz soll
ehrlich bleiben, auch wenn eine Chance schlecht lief. Schlägt das Skript fehl,
weitermachen und es in der Endnachricht erwähnen.

## Fundamentale Signale nutzen

data/charts.json enthält je Aktie das Feld "fund": Änderung der
Gewinnschätzungen (30/90 Tage, Anzahl Anhebungen/Senkungen), Quartalsüberraschungen,
Anteil der Kaufempfehlungen jetzt und vor 3 Monaten, Insider-Käufe/-Verkäufe an der
Börse (90 Tage, nur US-Aktien), Kursreaktion auf die letzten Zahlen und den nächsten
Zahlentermin.

- Bei der Einordnung ("signal") je Depot-Position diese Daten mit berücksichtigen
  und in "note" die wichtigste davon kurz nennen (z. B. „Analysten haben die
  Gewinnschätzung in 30 Tagen um 5 % gesenkt“).
- Bei den Chancen der Woche Kandidaten mit steigenden Gewinnschätzungen
  bevorzugen; bei sinkenden Schätzungen (≤ −2 % in 30 Tagen) nur mit besonders
  starker, bestätigter Begründung und das als Risiko nennen.
- Insider-Käufe, die in Briefing oder Begründung genannt werden, mit der
  Original-Meldung (SEC EDGAR, Form 4) oder einer zweiten seriösen Quelle prüfen.
- Zahlentermine aus "next_earnings" gelten als 1 Quelle; mit "estimated": true
  sind sie „(voraussichtlich)“, bis das Unternehmen sie bestätigt.

## Wichtige Nachrichten: 3 Quellen

Für Nachrichten mit großer Wirkung auf eine Depot-Position (Quartalszahlen,
Prognose-Änderung, Übernahme, Kapitalerhöhung, Klage/Behörde, Rücktritt im
Vorstand, Herab-/Hochstufung durch große Banken) gelten 3 unabhängige
Quellen oder die Primärquelle (Pressemitteilung, SEC-Meldung) plus 1 weitere.
Lieber mehr suchen als weglassen; ist es nicht so belegbar, als „noch nicht
bestätigt“ kennzeichnen.

## ETFs im Depot

Fehlen bei einem ETF in data/portfolio.json die Felder "sector" (z. B.
"Breiter Index (MSCI World)", "Technologie", "Rohstoffe", "Energie") oder
"region" ("USA", "Europa", "Welt", "China", "Schwellenländer"), nach Prüfung der
offiziellen ETF-Beschreibung eintragen. Bei Aktien liefert charts.py Branche und
Region automatisch.

## Nicht ändern

Die Aufgabe ändert nur Dateien in data/. Nie index.html, sw.js, manifest, icons,
vendor/, scripts/ oder diese Datei.
