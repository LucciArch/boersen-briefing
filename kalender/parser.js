// Zerlegt einen gesprochenen deutschen Satz in Titel, Datum und Uhrzeit.
// Beispiel: "Morgen um halb drei Zahnarzt" -> { title: "Zahnarzt", date: <morgen>, hour: 14, minute: 30 }
(function (root) {
  "use strict";

  // ---------- Zahlwörter 0–59 ----------
  const ONES = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf",
    "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"];
  const TENS = { 20: "zwanzig", 30: "dreißig", 40: "vierzig", 50: "fünfzig" };
  const NUMWORDS = {};
  ONES.forEach((w, i) => (NUMWORDS[w] = i));
  for (const t of [20, 30, 40, 50]) {
    NUMWORDS[TENS[t]] = t;
    for (let o = 1; o <= 9; o++) NUMWORDS[(o === 1 ? "ein" : ONES[o]) + "und" + TENS[t]] = t + o;
  }
  Object.assign(NUMWORDS, { ein: 1, eine: 1, einer: 1, einem: 1, einen: 1, dreissig: 30 });
  // Ordinalzahlen für "am dritten", "zum vierundzwanzigsten"
  const ORD = {};
  const ordBase = { 1: "ers", 3: "drit", 7: "sieb", 8: "ach" };
  for (let n = 1; n <= 31; n++) {
    let w;
    if (n < 20) w = (ordBase[n] || ONES[n]) + "ten";
    else {
      const name = Object.keys(NUMWORDS).find(k => NUMWORDS[k] === n && k !== "dreissig" && !["ein","eine","einer","einem","einen"].includes(k));
      w = name + "sten";
    }
    ORD[w] = n;
  }

  const L = "[\\p{L}\\d]"; // Wortzeichen inkl. Umlaute
  const B = `(?<!${L})`;    // Wortanfang
  const E = `(?!${L})`;     // Wortende
  const NUMW = Object.keys(NUMWORDS).sort((a, b) => b.length - a.length).join("|");
  const NUM = `(\\d{1,2}|${NUMW})`;
  const ORDW = Object.keys(ORD).sort((a, b) => b.length - a.length).join("|");
  const num = s => (s == null ? null : /^\d+$/.test(s) ? parseInt(s, 10) : NUMWORDS[s] ?? null);

  const MONTHS = { januar: 1, jänner: 1, jaenner: 1, februar: 2, feber: 2, märz: 3, maerz: 3, april: 4, mai: 5, juni: 6, juli: 7,
    august: 8, september: 9, oktober: 10, november: 11, dezember: 12, jan: 1, feb: 2, mär: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, okt: 10, nov: 11, dez: 12 };
  const MONW = Object.keys(MONTHS).sort((a, b) => b.length - a.length).join("|");
  const WEEKDAYS = { montag: 1, dienstag: 2, mittwoch: 3, donnerstag: 4, freitag: 5, samstag: 6, sonnabend: 6, sonntag: 0 };
  const WDW = Object.keys(WEEKDAYS).join("|");

  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const dayStart = d => new Date(d.getFullYear(), d.getMonth(), d.getDate());

  function parse(text, now) {
    now = now ? new Date(now) : new Date();
    const today = dayStart(now);
    // o = Originaltext (für den Titel), s = kleingeschriebene Kopie (für die Erkennung), gleiche Länge
    let o = " " + String(text || "")
      .replace(/[„“"!?;]/g, " ")
      .replace(/(\d)\s*:\s*(\d)/g, "$1:$2") + " ";
    let s = [...o].map(c => { const l = c.toLowerCase(); return l.length === 1 ? l : c; }).join("");

    let date = null, hour = null, minute = 0, endHour = null, endMinute = 0;
    let period = null;         // "am" | "pm"
    let periodDefault = null;  // Standard-Uhrzeit, wenn nur "abends" o. ä. gesagt wurde
    let relMinutes = null;
    let explicitDate = false;

    const take = (re, fn) => {
      const rx = new RegExp(re, "iu");
      const m = s.match(rx);
      if (!m) return false;
      if (fn(m) === false) return false;
      s = s.slice(0, m.index) + " " + s.slice(m.index + m[0].length);
      o = o.slice(0, m.index) + " " + o.slice(m.index + m[0].length);
      return true;
    };

    const nextMonday = (weeks) => addDays(today, (((1 - today.getDay() + 7) % 7) || 7) + 7 * (weeks - 1));
    const WEEKQ = `(nächste|nächster|kommende|kommender|übernächste|übernächster|diese|dieser)\\s+woche`;
    const wkCount = w => /^über/.test(w) ? 2 : /^dies/.test(w) ? 0 : 1;
    const inWeek = (weeks, wd) => weeks === 0
      ? addDays(today, (wd - today.getDay() + 7) % 7 || (wd === today.getDay() ? 0 : 7))
      : addDays(nextMonday(weeks), (wd + 6) % 7);
    // "nächste Woche Dienstag", "nächste Woche am Dienstag", "übernächste Woche Freitag"
    take(`${B}(?:in\\s+der\\s+|in\\s+)?${WEEKQ}\\s+(?:am\\s+)?(${WDW})${E}`, m => {
      date = inWeek(wkCount(m[1]), WEEKDAYS[m[2]]); explicitDate = true;
    }) ||
    // "Dienstag nächste Woche", "am Dienstag in der nächsten Woche"
    take(`${B}(?:am\\s+)?(${WDW})\\s+(?:in\\s+der\\s+|in\\s+)?(nächsten|kommenden|übernächsten|dieser|diese|nächste|kommende|übernächste)\\s+woche${E}`, m => {
      date = inWeek(wkCount(m[2]), WEEKDAYS[m[1]]); explicitDate = true;
    }) ||
    // "Dienstag in einer Woche", "Freitag in zwei Wochen"
    take(`${B}(?:am\\s+)?(${WDW})\\s+in\\s+${NUM}\\s+wochen?${E}`, m => {
      const n = num(m[2]); if (n == null) return false;
      const wd = WEEKDAYS[m[1]]; let diff = (wd - today.getDay() + 7) % 7;
      date = addDays(today, diff + 7 * n); explicitDate = true;
    }) ||
    // "heute in einer Woche", "morgen in zwei Wochen"
    take(`${B}(heute|morgen|übermorgen)\\s+in\\s+${NUM}\\s+wochen?${E}`, m => {
      const n = num(m[2]); if (n == null) return false;
      date = addDays(today, ({ heute: 0, morgen: 1, "übermorgen": 2 })[m[1]] + 7 * n); explicitDate = true;
    }) ||
    // "Anfang nächster Woche", "Ende der Woche", "am Wochenende", "Ende des Monats"
    take(`${B}anfang\\s+(?:der\\s+)?(nächsten|nächster|kommenden|kommender|übernächsten)\\s+woche${E}`, m => {
      date = nextMonday(wkCount(m[1])); explicitDate = true;
    }) ||
    take(`${B}(?:am\\s+|zum\\s+|bis\\s+zum\\s+)?(nächsten\\s+|kommenden\\s+)?wochenende${E}`, m => {
      let diff = (6 - today.getDay() + 7) % 7; if (m[1] && diff < 2) diff += 7;
      date = addDays(today, diff); explicitDate = true;
    }) ||
    take(`${B}(?:bis\\s+)?ende\\s+(?:der|dieser)\\s+woche${E}`, () => {
      date = addDays(today, (5 - today.getDay() + 7) % 7); explicitDate = true;
    }) ||
    take(`${B}(?:bis\\s+|zum\\s+)?(?:ende\\s+(?:des|dieses)\\s+monats|monatsende)${E}`, () => {
      date = new Date(today.getFullYear(), today.getMonth() + 1, 0); explicitDate = true;
    });

    // ---------- Relativ: "in 2 Stunden", "in einer halben Stunde" ----------
    if (!date) take(`${B}in\\s+(?:einer\\s+)?(halben|anderthalb|eineinhalb)\\s+stunden?${E}`, m => {
      relMinutes = m[1] === "halben" ? 30 : 90;
    }) ||
    take(`${B}in\\s+${NUM}\\s*(minuten|min|stunden|stunde|std|tagen|tag|wochen|woche|monaten|monat)${E}`, m => {
      const n = num(m[1]); const u = m[2];
      if (n == null) return false;
      if (/^min/.test(u)) relMinutes = n;
      else if (/^st/.test(u)) relMinutes = n * 60;
      else if (/^tag/.test(u)) { date = addDays(today, n); explicitDate = true; }
      else if (/^woch/.test(u)) { date = addDays(today, n * 7); explicitDate = true; }
      else { date = new Date(today.getFullYear(), today.getMonth() + n, today.getDate()); explicitDate = true; }
    });

    // ---------- Datum ----------
    // 24.12.2026 / 24.12. / 24.12
    if (!date) take(`${B}(?:am\\s+|zum\\s+|den\\s+)?(\\d{1,2})\\.\\s?(\\d{1,2})\\.(?:\\s?(\\d{2,4}))?(?!\\d)`, m => {
      const d = +m[1], mo = +m[2]; let y = m[3] ? +m[3] : null;
      if (d < 1 || d > 31 || mo < 1 || mo > 12) return false;
      if (y != null && y < 100) y += 2000;
      date = resolveDayMonth(d, mo, y, today); explicitDate = true;
    }) ||
    take(`${B}(?:am|zum|den|bis\\s+zum|ab\\s+dem|ab)\\s+(\\d{1,2})[./](\\d{1,2})(?![\\d:.])(?!\\s*uhr)`, m => {
      const d = +m[1], mo = +m[2];
      if (d < 1 || d > 31 || mo < 1 || mo > 12) return false;
      date = resolveDayMonth(d, mo, null, today); explicitDate = true;
    }) ||
    // 24. Dezember 2026 / vierundzwanzigsten Dezember
    take(`${B}(?:am\\s+|zum\\s+|den\\s+)?(?:(\\d{1,2})\\.?|(${ORDW}))\\s*(${MONW})\\.?(?:\\s+(\\d{4}))?${E}`, m => {
      const d = m[1] ? +m[1] : ORD[m[2]]; const mo = MONTHS[m[3]]; const y = m[4] ? +m[4] : null;
      if (!d || d > 31) return false;
      date = resolveDayMonth(d, mo, y, today); explicitDate = true;
    }) ||
    // "am 3." / "am dritten" (Tag im aktuellen oder nächsten Monat)
    take(`${B}(?:am|zum|den)\\s+(?:(\\d{1,2})\\.|(${ORDW}))${E}`, m => {
      const d = m[1] ? +m[1] : ORD[m[2]];
      if (!d || d > 31) return false;
      let x = new Date(today.getFullYear(), today.getMonth(), d);
      if (x < today) x = new Date(today.getFullYear(), today.getMonth() + 1, d);
      date = x; explicitDate = true;
    });

    if (!date) {
      take(`${B}übermorgen${E}`, () => { date = addDays(today, 2); explicitDate = true; }) ||
      take(`${B}heute${E}`, () => { date = today; explicitDate = true; }) ||
      take(`${B}morgen${E}(?!\\s+(?:und|oder))`, m => {
        // "am Morgen" = morgens, nicht "morgen"
        const before = s.slice(0, m.index);
        if (/(?:am|den|jeden|heute)\s*$/.test(before)) return false;
        date = addDays(today, 1); explicitDate = true;
      }) ||
      take(`${B}(?:(nächste[nrms]?|kommende[nrms]?|diese[nrms]?)\\s+|am\\s+)?(${WDW})${E}`, m => {
        const target = WEEKDAYS[m[2]];
        let diff = (target - today.getDay() + 7) % 7;
        if (diff === 0) diff = 7;
        date = addDays(today, diff); explicitDate = true;
      }) ||
      take(`${B}(nächste|kommende)\\s+woche${E}`, () => {
        const diff = ((1 - today.getDay() + 7) % 7) || 7; // nächster Montag
        date = addDays(today, diff); explicitDate = true;
      }) ||
      take(`${B}(nächsten|kommenden)\\s+monat${E}`, () => {
        date = new Date(today.getFullYear(), today.getMonth() + 1, 1); explicitDate = true;
      });
    }

    take(`${B}(?:gleich|jetzt|sofort)${E}`, () => { if (relMinutes == null && !date) relMinutes = 0; });

    // ---------- Tageszeit ----------
    const periods = [
      [`(?:am\\s+)?früh(?:morgens)?|morgens|in\\s+der\\s+früh|am\\s+morgen`, "am", 8],
      [`(?:am\\s+)?vormittags?|am\\s+vormittag`, "am", 10],
      [`(?:zu\\s+)?mittags?|am\\s+mittag|zum\\s+mittagessen`, "noon", 12],
      [`(?:am\\s+)?nachmittags?|am\\s+nachmittag`, "pm", 15],
      [`(?:am\\s+)?abends?|am\\s+abend`, "pm", 19],
      [`(?:in\\s+der\\s+)?nachts?|in\\s+der\\s+nacht`, "pm", 22],
    ];
    for (const [re, p, def] of periods) {
      if (take(`${B}(?:${re})${E}`, () => { period = p; periodDefault = def; })) break;
    }

    // ---------- Uhrzeit ----------
    const pre = `(?:(?:um|ab|gegen|so\\s+um|bis)\\s+)?`;
    // Zeitspanne "von 14 bis 16 Uhr" / "14:00 - 15:30"
    take(`${B}(?:von\\s+)?(\\d{1,2})(?:[:.](\\d{2}))?\\s*(?:uhr\\s*)?(?:bis|-|–)\\s*(\\d{1,2})(?:[:.](\\d{2}))?\\s*(?:uhr)?${E}`, m => {
      const h1 = +m[1], h2 = +m[3];
      if (h1 > 24 || h2 > 24) return false;
      hour = h1; minute = m[2] ? +m[2] : 0; endHour = h2; endMinute = m[4] ? +m[4] : 0;
    }) ||
    take(`${B}${pre}(\\d{1,2})[:.](\\d{2})\\s*(?:uhr)?${E}`, m => {
      if (+m[1] > 24 || +m[2] > 59) return false;
      hour = +m[1]; minute = +m[2];
    }) ||
    take(`${B}${pre}${NUM}\\s*uhr(?:\\s+${NUM})?${E}`, m => {
      const h = num(m[1]); if (h == null || h > 24) return false;
      hour = h; minute = m[2] ? num(m[2]) || 0 : 0;
    }) ||
    take(`${B}${pre}halb\\s+${NUM}${E}`, m => {
      const h = num(m[1]); if (h == null || h > 24) return false;
      hour = (h + 23) % 24; minute = 30;
    }) ||
    take(`${B}${pre}(?:viertel|1/4)\\s+nach\\s+${NUM}${E}`, m => { const h = num(m[1]); if (h == null) return false; hour = h; minute = 15; }) ||
    take(`${B}${pre}(?:viertel|1/4)\\s+vor\\s+${NUM}${E}`, m => { const h = num(m[1]); if (h == null) return false; hour = (h + 23) % 24; minute = 45; }) ||
    take(`${B}${pre}(?:dreiviertel|drei\\s+viertel|3/4)\\s+${NUM}${E}`, m => { const h = num(m[1]); if (h == null) return false; hour = (h + 23) % 24; minute = 45; }) ||
    take(`${B}${pre}viertel\\s+${NUM}${E}`, m => { const h = num(m[1]); if (h == null) return false; hour = (h + 23) % 24; minute = 15; }) ||
    take(`${B}${pre}${NUM}\\s+(?:minuten\\s+)?(nach|vor)\\s+(halb\\s+)?${NUM}${E}`, m => {
      const mins = num(m[1]), h = num(m[4]); if (mins == null || h == null || mins >= 30) return false;
      const base = m[3] ? ((h + 23) % 24) * 60 + 30 : h * 60;
      const t = (base + (m[2] === "nach" ? mins : -mins) + 1440) % 1440;
      hour = Math.floor(t / 60); minute = t % 60;
    }) ||
    take(`${B}(?:um|gegen|ab)\\s+${NUM}${E}(?!\\s*(?:minuten|stunden|tage|wochen|min))`, m => {
      const h = num(m[1]); if (h == null || h > 24) return false;
      hour = h; minute = 0;
    });

    // ---------- Tageszeit anwenden ----------
    let timeGuessed = false;
    if (relMinutes != null) {
      const t = new Date(now.getTime() + relMinutes * 60000);
      date = dayStart(t); hour = t.getHours(); minute = t.getMinutes();
    } else if (hour == null) {
      if (periodDefault != null) hour = periodDefault;
      else { hour = 9; timeGuessed = true; }
      minute = 0;
    } else {
      if (period === "pm" && hour < 12) hour += 12;
      else if (period === "noon" && hour <= 4) hour += 12;
      else if (period === "am" && hour === 12) hour = 0;
      else if (!period && hour >= 1 && hour <= 6) hour += 12; // "um 3" meint meist 15 Uhr
      if (endHour != null) {
        if ((period === "pm" || (!period && endHour <= 6)) && endHour < 12) endHour += 12;
        if (endHour < hour) endHour += 12;
      }
    }
    if (hour === 24) hour = 0;

    // Nur Uhrzeit, kein Datum: heute, sonst morgen
    if (!date) {
      date = today;
      const t = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hour, minute);
      if (t <= now) date = addDays(today, 1);
    }

    const start = new Date(date.getFullYear(), date.getMonth(), date.getDate(), hour, minute);
    let end = null;
    if (endHour != null) end = new Date(date.getFullYear(), date.getMonth(), date.getDate(), endHour % 24, endMinute);

    let { title, location } = splitLocation(cleanTitle(o));
    if (/^(?:beim|bei|zum|zur)\s/i.test(title)) title = "Termin " + title.charAt(0).toLowerCase() + title.slice(1);
    return { title, location, start, end, timeGuessed, dateFound: explicitDate || relMinutes != null };
  }

  function resolveDayMonth(d, mo, y, today) {
    if (y) return new Date(y, mo - 1, d);
    let x = new Date(today.getFullYear(), mo - 1, d);
    if (x < today) x = new Date(today.getFullYear() + 1, mo - 1, d);
    return x;
  }

  const LEAD = [
    /^(?:hey|hallo|ok(?:ay)?|also|bitte|und|so)\b/,
    /^(?:erinnere?|erinner)\s+mich(?:\s+bitte)?(?:\s+(?:daran|an|dass|zu|ans?))*/,
    /^(?:trag(?:e)?|setz(?:e)?|leg(?:e)?|mach(?:e)?)\s+(?:mir\s+)?(?:bitte\s+)?(?:einen?\s+)?(?:neuen?\s+)?(?:termin\s+)?(?:ein|an)?/,
    /^(?:neuer|neuen|einen|ein)?\s*(?:termin|erinnerung)\s*(?::|für|zum|zur)?/,
    /^(?:ich\s+(?:habe|hab|muss|soll|will|möchte|sollte|müsste)(?:\s+(?:einen?|noch|unbedingt|dringend))*)/,
    /^(?:(?:habe|hab|muss|soll|will|möchte|sollte|müsste|hätte|gehe|geh|fahre|fahr)\s+ich(?:\s+(?:einen?|noch|unbedingt|dringend|mal))*)/,
    /^(?:(?:ist|steht|gibt\s+es|gibts|wäre)(?:\s+(?:ein|eine|einen|der|die|das))?)/,
    /^(?:muss|soll|noch)\b/,
    /^(?:dass\s+ich|daran\s+dass\s+ich|daran|dass|zu|um|am|an|ab|im|in|den|der|die|das|für|mit\s*$)\b/,
  ];
  const TRAIL = [
    /\b(?:eintragen|einplanen|erinnern|hinzufügen|notieren|bitte|ein|habe|hab|muss|soll|ist|zu|um|am|an|ab|im|in|den|der|die|das|für|und|bis|von|gegen|so)$/,
  ];

  function cleanTitle(s) {
    let t = s.replace(/\s+/g, " ").replace(/\s+([,.])/g, "$1").trim();
    let changed = true;
    while (changed) {
      changed = false;
      t = t.replace(/^[\s,.:\-–]+|[\s,:\-–]+$/g, "");
      for (const re of LEAD) { const n = t.replace(new RegExp(re.source, "iu"), "").trim(); if (n !== t) { t = n; changed = true; } }
      for (const re of TRAIL) { const n = t.replace(new RegExp(re.source, "iu"), "").trim(); if (n !== t) { t = n; changed = true; } }
      const n2 = t.replace(/\.$/, "");
      if (n2 !== t) { t = n2; changed = true; }
    }
    t = t.replace(/\s+(?:um|am)\s+(?=(?:mit|bei|in|im)\b)/gi, " ").replace(/\s{2,}/g, " ");
    if (!t) return "";
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  // Ort: "… im Büro", "… in der Stadthalle", "… beim Zahnarzt Dr. Weber", "Ort: Hauptstraße 5"
  function splitLocation(t) {
    if (!t) return { title: "", location: "" };
    let m = t.match(/^(.*?)[,\s]+(?:ort|adresse|treffpunkt)\s*:?\s+(.+)$/iu);
    if (m && m[1].trim()) return { title: cap(m[1].trim()), location: cap(m[2].trim()) };
    const PREP = "(?:im|in\\s+der|in\\s+dem|in\\s+den|ins|in|beim|bei\\s+der|bei\\s+dem|bei|auf\\s+dem|auf\\s+der|an\\s+der|am|vor\\s+dem|vor\\s+der|zum|zur|nach)";
    const re = new RegExp(`^(.+?)\\s+(${PREP})\\s+((?:\\p{Lu}|\\d)[\\p{L}\\d.\\-'/]*(?:\\s+(?:\\p{Lu}|\\d)[\\p{L}\\d.\\-'/]*|\\s+(?:str\\.|straße|platz|weg|allee|gasse|ring))*)(?:\\s+(.*))?$`, "u");
    m = t.match(re);
    if (m) {
      const head = m[1].trim(), prep = m[2].toLowerCase().replace(/\s+/g, " "), place = m[3].trim(), tail = (m[4] || "").trim();
      // nur wenn danach höchstens ein Verb folgt ("… im Büro abgeben") – sonst ist es kein Ort
      const tailOk = !tail || /^[\p{Ll}]+$/u.test(tail);
      const toWords = ["zum", "zur", "nach"];
      if (tailOk && head && !/^(?:mit|und)$/i.test(head)) {
        if (toWords.includes(prep)) return { title: t, location: "" }; // "Auto zum TÜV bringen" bleibt Titel
        const title = tail ? `${head} ${tail}` : head;
        return { title: cap(title), location: cap(place) };
      }
    }
    return { title: t, location: "" };
  }
  const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;

  root.parseTermin = parse;
  if (typeof module !== "undefined") module.exports = { parseTermin: parse };
})(typeof window !== "undefined" ? window : globalThis);
