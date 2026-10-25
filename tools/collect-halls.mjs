// Quad halls price collector
// Visits each uni's website, finds its accommodation price pages and pulls out weekly prices by room type.
// Run:  node tools/collect-halls.mjs            (all unis)
//       node tools/collect-halls.mjs uea bath   (just these ids)
// Output: data/halls.json  +  data/halls-review.md (what needs a human check)
import fs from "node:fs/promises";

const UA = "QuadUniMatcherBot/1.0 (+student project; checks published accommodation prices)";
const MAX_PAGES = Number(process.env.MAX_PAGES || 18);   // pages per uni
const DELAY_MS = Number(process.env.DELAY_MS || 800);    // be polite
const TIMEOUT_MS = 15000;
const BASE = process.env.QUAD_BASE || "";                 // for tests: rewrite https://www.<domain> to a local server

const sleep = ms => new Promise(r => setTimeout(r, ms));
const root = d => d.replace(/^www\./, "");
const norm = u => u.replace(/\/+$/, "").replace(/\?.*$/, "");

// ---------- fetching ----------
async function get(url) {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { "user-agent": UA, accept: "text/html" }, redirect: "follow", signal: ctl.signal });
    const type = r.headers.get("content-type") || "";
    if (!r.ok || !type.includes("html")) return null;
    return { url: r.url, html: await r.text() };
  } catch { return null; } finally { clearTimeout(t); }
}
async function robots(origin) {
  try {
    const res = await fetch(origin + "/robots.txt", { headers: { "user-agent": UA } });
    if (!res.ok) return [];
    const txt = await res.text(); const dis = []; let on = false;
    for (const line of txt.split(/\r?\n/)) {
      const [k, ...v] = line.split(":"); const val = v.join(":").trim();
      if (/^user-agent$/i.test(k.trim())) on = val === "*" || /quad/i.test(val);
      else if (on && /^disallow$/i.test(k.trim()) && val) dis.push(val);
    }
    return dis;
  } catch { return []; }
}

// ---------- html → text rows ----------
function toText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<\/(tr|p|li|h[1-6]|div|section|article|dt|dd|caption|table)>|<br\s*\/?>/gi, "\n")
    .replace(/<\/t[dh]>/gi, " | ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&pound;|&#163;|&#xa3;/gi, "£").replace(/&nbsp;|&#160;/gi, " ").replace(/&amp;/gi, "&").replace(/&#8211;|&ndash;/gi, "–")
    .split("\n").map(l => l.replace(/\s+/g, " ").trim()).filter(Boolean);
}
function links(html, base) {
  const out = [];
  for (const m of html.matchAll(/<a\b[^>]*href=["']([^"'#]+)["'][^>]*>([\s\S]*?)<\/a>/gi)) {
    try { out.push({ url: new URL(m[1], base).href.split("#")[0], text: m[2].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim() }); } catch {}
  }
  return out;
}

// ---------- price extraction ----------
const WEEK = /(per|a|each|\/|p\/?)\s*(week|wk)\b|\bpw\b|\bweekly\b/i;
const YEARISH = /(per|a)\s*(year|annum|term)|\btotal\b|\bdeposit\b|\bbooking fee\b|\bper night\b|\bnightly\b/i;
function classify(ctx) {
  const c = ctx.toLowerCase();
  if (/\bstudio\b/.test(c)) return "studio";
  if (/wet ?room|\bpod\b|shower pod/.test(c)) return "wet";
  if (/en-?\s?suite|ensuite|private bathroom/.test(c)) return /premium|large|deluxe|plus|double|full bath/.test(c) ? "full" : "wet";
  if (/shared bath|shared facilities|standard room|non-?en-?suite|single room|twin/.test(c)) return "shared";
  return null;
}
function extract(lines) {
  const found = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.includes("£")) continue;
    const ctx = [lines[i - 2] || "", lines[i - 1] || "", line].join(" ");
    const weekly = WEEK.test(line) || (WEEK.test(lines[i - 1] || "") && !YEARISH.test(line)) || /weekly|per week/i.test(lines.slice(Math.max(0, i - 6), i).join(" "));
    if (!weekly || YEARISH.test(line) && !WEEK.test(line)) continue;
    const type = classify(line) || classify(ctx);
    if (!type) continue;
    for (const m of line.matchAll(/£\s?(\d{2,3}(?:\.\d{1,2})?)(?!\d|,\d)/g)) {
      const v = Number(m[1]);
      if (v >= 60 && v <= 600) found.push({ type, v, catered: /\bcatered\b/i.test(ctx) && !/self[- ]catered/i.test(ctx), text: line.slice(0, 160) });
    }
  }
  return found;
}
const median = a => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : Math.round((s[n / 2 - 1] + s[n / 2]) / 2)) : null; };

// ---------- crawl one uni ----------
const ACC = /accommodation|residences|halls|living|housing/i;
const PRICE = /fee|price|cost|rent|rates|tariff|rooms|compare|our-halls|residences|halls/i;
async function crawl(uni) {
  const host = "www." + root(uni.domain);
  const originReal = "https://" + host;
  const origin = BASE ? BASE + "/" + root(uni.domain) : originReal;
  const disallow = BASE ? [] : await robots(originReal);
  const allowed = u => { try { const x = new URL(u); if (BASE) return u.startsWith(origin); return x.hostname.endsWith(root(uni.domain)) && !disallow.some(d => x.pathname.startsWith(d)); } catch { return false; } };
  const queue = [...(uni.start || []), origin + "/accommodation", origin + "/accommodation/", origin + "/"];
  const seen = new Set(), pages = [], hits = [];
  while (queue.length && pages.length < MAX_PAGES) {
    const url = queue.shift(); if (seen.has(norm(url)) || !allowed(url)) continue; seen.add(norm(url));
    const page = await get(url); await sleep(DELAY_MS);
    if (!page || pages.includes(norm(page.url))) continue;
    pages.push(norm(page.url)); seen.add(norm(page.url));
    const lines = toText(page.html);
    const f = extract(lines).filter((x, i, a) => a.findIndex(y => y.text === x.text && y.v === x.v) === i);
    if (f.length) hits.push({ url: page.url, year: (page.html.match(/20(2[6-9])\s*[\/–-]\s*(2[7-9]|20(2[7-9]))/) || [])[0] || null, items: f });
    const ls = links(page.html, page.url).filter(l => allowed(l.url));
    const acc = ls.filter(l => ACC.test(l.url + " " + l.text));
    const priced = acc.filter(l => PRICE.test(l.url + " " + l.text));
    for (const l of [...priced, ...acc]) if (!seen.has(norm(l.url)) && !queue.includes(l.url)) (PRICE.test(l.url + l.text) ? queue.unshift(l.url) : queue.push(l.url));
  }
  // summarise
  const all = hits.flatMap(h => h.items);
  const rooms = {};
  for (const t of ["shared", "wet", "full", "studio"]) {
    const v = all.filter(x => x.type === t && !x.catered).map(x => x.v);
    if (v.length) rooms[t] = { median: median(v), min: Math.min(...v), max: Math.max(...v), n: v.length };
  }
  const cat = all.filter(x => x.catered).map(x => x.v);
  if (cat.length) rooms.catered = { median: median(cat), min: Math.min(...cat), max: Math.max(...cat), n: cat.length };
  const years = hits.map(h => h.year).filter(Boolean);
  const n = all.length;
  const confidence = n >= 6 && years.length ? "high" : n >= 3 ? "medium" : n ? "low" : "none";
  return {
    id: uni.id, name: uni.name, checked: new Date().toISOString().slice(0, 10), confidence,
    year: years.sort().pop() || null, catered: all.some(x => x.catered), rooms,
    sources: [...new Set(hits.map(h => h.url))].slice(0, 6), pagesVisited: pages.length,
    examples: all.slice(0, 5).map(x => `${x.type} £${x.v}: ${x.text}`)
  };
}

// ---------- main ----------
const unis = JSON.parse(await fs.readFile(new URL("./unis.json", import.meta.url)));
const only = process.argv.slice(2);
const list = only.length ? unis.filter(u => only.includes(u.id)) : unis;
await fs.mkdir("data", { recursive: true });
let prev = {}; try { prev = JSON.parse(await fs.readFile("data/halls.json", "utf8")); } catch {}
const out = { ...prev };
for (const u of list) {
  process.stdout.write(`• ${u.name} … `);
  try { const r = await crawl(u); out[u.id] = r; console.log(`${r.confidence} (${Object.keys(r.rooms).join(", ") || "no prices"})`); }
  catch (e) { console.log("error " + e.message); }
}
await fs.writeFile("data/halls.json", JSON.stringify(out, null, 1));
const review = Object.values(out).filter(r => r.confidence !== "high")
  .map(r => `- **${r.name}** — ${r.confidence}${r.sources[0] ? ` — ${r.sources[0]}` : " — add a start URL in tools/unis.json"}`).join("\n");
await fs.writeFile("data/halls-review.md", `# Halls prices to check by hand\n\nChecked ${new Date().toISOString().slice(0, 10)}. High-confidence results are used automatically; medium are used but flagged; low/none are not used.\n\n${review || "Nothing — all high confidence."}\n`);
console.log("\nSaved data/halls.json and data/halls-review.md");
