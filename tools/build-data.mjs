// Merges collected data into quad-data.json (the file the app reads).
// Keeps anything you've added by hand to quad-data.json.
import fs from "node:fs/promises";

const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
let data = {}; try { data = JSON.parse(await fs.readFile("quad-data.json", "utf8")); } catch {}
let halls = {}; try { halls = JSON.parse(await fs.readFile("data/halls.json", "utf8")); } catch {}
let manual = {}; try { manual = JSON.parse(await fs.readFile("tools/halls-manual.json", "utf8")); } catch {}
let du = null; try { du = JSON.parse(await fs.readFile("data/discover-uni.json", "utf8")); } catch {}

data.version = today;
data.halls = {};
for (const [id, r] of Object.entries(halls)) {
  if (!["high", "medium"].includes(r.confidence)) continue;
  const rooms = Object.fromEntries(Object.entries(r.rooms).filter(([k]) => k !== "catered").map(([k, v]) => [k, Math.round(v.median)]));
  // sanity checks: drop prices that can't be right (e.g. picked up from a deposit or a shared twin)
  for (const k of Object.keys(rooms)) if (rooms[k] < 90) delete rooms[k];
  if (rooms.shared && rooms.wet && rooms.wet < rooms.shared) delete rooms.shared;
  if (rooms.full && rooms.wet && rooms.full < rooms.wet) delete rooms.full;
  if (rooms.studio && rooms.wet && rooms.studio < rooms.wet) delete rooms.studio;
  if (!Object.keys(rooms).length) continue;
  data.halls[id] = { rooms, catered: r.catered, cateredPrice: r.rooms.catered ? Math.round(r.rooms.catered.median) : null, checked: r.checked, year: r.year, confidence: r.confidence, source: r.sources[0] || null };
}
// Prices checked by hand (tools/halls-manual.json) are used unless the checker finds a newer year with high confidence
const yr = y => { const m = String(y || "").match(/20(\d\d)/); return m ? Number(m[1]) : 0; };
for (const [id, m] of Object.entries(manual)) {
  const auto = data.halls[id];
  // a newer automatic result (a later price year, high confidence) replaces the hand-checked one
  if (auto && auto.confidence === "high" && yr(auto.year) > yr(m.year)) { auto.method = "automatic"; continue; }
  data.halls[id] = { rooms: m.rooms || {}, from: m.from ?? null, catered: !!m.catered, cateredPrice: m.catPrice ?? null, checked: m.checked || "2026-10-25",
    year: m.year || null, weeks: m.weeks || null, note: m.note || null, confidence: "high", method: "checked by hand", source: m.source };
}
if (du) data.du = du;
delete data.parVerified; delete data.addCourse; delete data.removeCourse; delete data.unis;
await fs.writeFile("quad-data.json", JSON.stringify(data));
// quad-data.js lets the app load its data even when opened straight from a file
await fs.writeFile("quad-data.js", "window.QUAD_DATA=" + JSON.stringify(data) + ";\n");
console.log(`quad-data.json + quad-data.js updated (${Object.keys(data.halls).length} unis with checked halls prices${du ? ", Discover Uni data published " + du.published : ""})`);
