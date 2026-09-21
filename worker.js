// The landing page's lookup chain. Same steps as general_knowledge() in ask.py:
// DuckDuckGo instant answer, then Wikipedia, and when the page found is the
// right topic but not an answer, a small model reads it and may only answer
// from the text. On the Mac that reader is a 1.7B under Ollama. Here a 3B on
// Workers AI stands in, held to the same grounding check.
import "./web/samantha.js";

const S = globalThis.Samantha;
const READER = "@cf/meta/llama-3.2-3b-instruct";  // the 1B said Peter S. Fischer wrote 1984, off the Murder, She Wrote page
const DECLINE = "I couldn't find anything on that, so I'm not going to make something up.";
const UA = { "User-Agent": "Samantha landing demo (turing.heyitsmejosh.com)" };

const QUESTION_PREFIX = /^(what'?s?|who'?s?|when'?s?|where'?s?|why|how)\s+(is|are|was|were|does|do|did)\s+(the\s+)?/i;
const LOOKUP_PREFIX = /^(?:tell me (?:about|of)|explain|describe|define|what do you know about)\s+(?:the\s+)?/i;
const FACT_SHAPED = /^(?:how many|how much|what (?:color|colour|year|time|temperature))\b/i;

const normalize = q => q.trim().replace(QUESTION_PREFIX, "").replace(LOOKUP_PREFIX, "").replace(/\?+$/, "").trim() || q;
const bareTitle = t => t.replace(/\s*\([^)]*\)/g, "");
const sameSet = (a, b) => a.length === b.length && a.every(x => b.includes(x));

async function getJSON(url) {
  try {
    const r = await fetch(url, { headers: UA, cf: { cacheTtl: 86400, cacheEverything: true } });
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

function isDefinitionOf(query, title) {
  const asked = S.keywords(normalize(query));
  return asked.length > 0 && sameSet(asked, S.keywords(bareTitle(title)));
}

function readingOrder(asked, found) {
  const topic = [], rest = [];
  for (const h of found) {
    if (/^lists? of/i.test(h.title)) continue;
    const named = S.keywords(bareTitle(h.title));
    const snippet = (h.snippet || "").replace(/<[^>]+>/g, "").toLowerCase();
    const hedged = /\b(?:one of the|among the)\b|\w+-(?:large|long|tall|big|small|high|deep|fast|old)/.test(snippet);
    const inSnippet = S.keywords(snippet);
    if (named.length && named.every(k => asked.includes(k))) topic.push(h.title);
    else if (named.some(k => asked.includes(k)) || (asked.length > 1 && asked.every(k => inSnippet.includes(k)) && !hedged)) rest.push(h.title);
  }
  return topic.concat(rest);
}

async function readArticle(env, query, title) {
  const page = await getJSON("https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exsectionformat=plain" +
                             `&redirects=1&titles=${encodeURIComponent(title)}&format=json&origin=*`);
  const pages = page?.query?.pages || {};
  const text = (Object.values(pages)[0]?.extract || "").slice(0, 7000);
  if (!text || text.slice(0, 300).includes("may refer to")) return null;
  let answer = "";
  try {
    const out = await env.AI.run(READER, { temperature: 0, max_tokens: 80, messages: [
      { role: "system", content: "Answer the question in one short sentence using ONLY the text. If the text does not contain the answer, reply exactly UNKNOWN." },
      { role: "user", content: `Text:\n${text}\n\nQuestion: ${query}` }] });
    answer = (out.response || "").trim();
  } catch { return null; }
  // every number and every capitalised name in the answer has to be on the page
  const claims = answer.match(/\d[\d,.]*\d|\d|\b[A-Z][a-z]{2,}\b/g) || [];
  const hay = text.toLowerCase(), asked = query.toLowerCase();
  const grounded = (claims.length > 1 ? claims.slice(1) : claims).every(c => hay.includes(c.toLowerCase().replace(/[.,]+$/, "")) || asked.includes(c.toLowerCase()));
  const declined = /unknown|does not (?:contain|mention|say|provide|specify)|doesn't (?:contain|mention|say)|not (?:mentioned|stated|specified|provided)|no (?:information|mention)/i.test(answer);
  // "The largest ocean." answers nothing: an answer has to bring a word the question did not have
  const adds = S.keywords(answer).some(k => !S.keywords(query).includes(k));
  return answer && !declined && grounded && adds ? answer : null;
}

const firstSentences = (text, n) => (text.match(/[^.!?]+[.!?]+(?:\s|$)/g) || [text]).slice(0, n).join("").trim();

async function ask(env, query) {
  if (!S.keywords(query).length) return { answer: DECLINE };
  const normalized = normalize(query);
  const d = await getJSON(`https://api.duckduckgo.com/?q=${encodeURIComponent(normalized)}&format=json&no_html=1&skip_disambig=1`);
  if (d?.Answer && typeof d.Answer === "string") return { answer: d.Answer.trim(), source: "DuckDuckGo" };
  if (d?.AbstractText && isDefinitionOf(query, d.Heading || "")) return { answer: firstSentences(d.AbstractText, 2), source: d.AbstractSource || "DuckDuckGo" };

  const s = await getJSON(`https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(normalized)}&format=json&srlimit=6&origin=*`);
  const found = s?.query?.search || [];
  if (!found.length) return { answer: DECLINE };
  const title = found[0].title;
  if (isDefinitionOf(query, title)) {
    const summary = await getJSON(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`);
    if (summary?.extract && summary.type !== "disambiguation" && !FACT_SHAPED.test(query.trim()))
      return { answer: firstSentences(summary.extract, 2), source: `Wikipedia: ${title}` };
  }
  for (const candidate of readingOrder(S.keywords(normalized), found).slice(0, 3)) {
    const read = await readArticle(env, query, candidate);
    if (read) return { answer: read, source: `Wikipedia: ${candidate}`, read: true };
  }
  return { answer: DECLINE };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/ask") return env.ASSETS.fetch(request);
    if (request.method !== "POST") return new Response("POST only", { status: 405 });
    const ip = request.headers.get("cf-connecting-ip") || "anon";
    if (env.LIMIT && !(await env.LIMIT.limit({ key: ip })).success)
      return Response.json({ answer: "That's a lot of questions in one minute. Give me a moment." }, { status: 429 });
    let q = "";
    try { q = String((await request.json()).q || "").trim().slice(0, 200); } catch {}
    if (!q) return Response.json({ answer: DECLINE }, { status: 400 });
    // the same question a day later is the same answer: no second trip to Wikipedia, no second model run
    const key = new Request("https://turing.heyitsmejosh.com/__ask/" + encodeURIComponent(q.toLowerCase()));
    const hit = await caches.default.match(key);
    if (hit) return hit;
    const res = Response.json(await ask(env, q), { headers: { "Cache-Control": "public, max-age=86400" } });
    ctx.waitUntil(caches.default.put(key, res.clone()));
    return res;
  }
};
