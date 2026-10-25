// Merges collected data into quad-data.json (the file the app reads).
// Keeps anything you've added by hand to quad-data.json.
import fs from "node:fs/promises";

const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
let data = {}; try { data = JSON.parse(await fs.readFile("quad-data.json", "utf8")); } catch {}
let halls = {}; try { halls = JSON.parse(await fs.readFile("data/halls.json", "utf8")); } catch {}
let manual = {}; try { manual = JSON.parse(await fs.readFile("tools/halls-manual.json", "utf8")); } catch {}

data.version = today;
data.halls = {};
for (const [id, r] of Object.entries(halls)) {
  if (!["high", "medium"].includes(r.confidence)) continue;
  const rooms = Object.fromEntries(Object.entries(r.rooms).filter(([k]) => k !== "catered").map(([k, v]) => [k, Math.round(v.median)]));
  data.halls[id] = { rooms, catered: r.catered, cateredPrice: r.rooms.catered ? Math.round(r.rooms.catered.median) : null, checked: r.checked, year: r.year, confidence: r.confidence, source: r.sources[0] || null };
}
// Prices checked by hand (tools/halls-manual.json) take priority over the automatic checker
for (const [id, m] of Object.entries(manual)) {
  data.halls[id] = { rooms: m.rooms || {}, from: m.from ?? null, catered: !!m.catered, cateredPrice: m.catPrice ?? null, checked: m.checked || "2026-10-25",
    year: m.year || null, weeks: m.weeks || null, note: m.note || null, confidence: "high", method: "checked by hand", source: m.source };
}
await fs.writeFile("quad-data.json", JSON.stringify(data, null, 1));
console.log(`quad-data.json updated (${Object.keys(data.halls).length} unis with checked halls prices)`);
