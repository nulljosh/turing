// /api/speak's kernel format: 16-bit signed PCM from ElevenLabs becomes 8-bit unsigned, silence at 128.
import { pcm16ToPcm8, smallTalk } from "../worker.js";
const b = new ArrayBuffer(8), v = new DataView(b);
[0, 32767, -32768, 256].forEach((x, i) => v.setInt16(i * 2, x, true));
const out = Array.from(pcm16ToPcm8(b));
if (out.join() !== "128,255,0,129") { console.log("FAIL", out); process.exit(1); }
console.log("PASS: pcm16 to pcm8");

// "hi samantha, introduce yourself" is her introduction, not a tool and not "I couldn't find anything"
for (const q of ["hi Samantha, introduce yourself", "introduce yourself", "Hey, who are you?", "what can you do"]) {
  if (!/I'm Samantha/.test(smallTalk(q) || "")) { console.log("FAIL intro", q, smallTalk(q)); process.exit(1); }
}
if (smallTalk("introduce me to rust")) { console.log("FAIL: a real question became small talk"); process.exit(1); }
console.log("PASS: introductions");

// /api/speak end to end against a fake Worker environment: no network, no real key, no real cache.
const store = new Map();
globalThis.caches = { default: { match: async k => store.get(k.url), put: async (k, r) => { store.set(k.url, r); } } };
const worker = (await import("../worker.js")).default;
const ctx = { waitUntil: p => p };
const env = key => ({ ASSETS: { fetch: () => new Response("asset") }, ELEVENLABS_API_KEY: key });
const post = (body, headers = {}) => new Request("https://turing.heyitsmejosh.com/api/speak", {
  method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
const expect = (what, got, want) => { if (got !== want) { console.log("FAIL", what, got, "!=", want); process.exit(1); } };
expect("empty text", (await worker.fetch(post({ text: "  " }), env("k"), ctx)).status, 400);
expect("other site", (await worker.fetch(post({ text: "hi" }, { origin: "https://evil.example" }), env("k"), ctx)).status, 403);
expect("no key", (await worker.fetch(post({ text: "hi" }), env(undefined), ctx)).status, 503);
let calls = 0;
const realFetch = globalThis.fetch;
let sent;
globalThis.fetch = async (u, init) => { calls++; sent = { u, body: JSON.parse(init.body) }; const b = new ArrayBuffer(4); new DataView(b).setInt16(0, 32767, true); return new Response(b); };
const first = await worker.fetch(post({ text: "hello there", format: "pcm8" }), env("k"), ctx);
expect("pcm8 status", first.status, 200);
expect("pcm8 bytes", (await first.arrayBuffer()).byteLength, 2);
await worker.fetch(post({ text: "hello there", format: "pcm8" }), env("k"), ctx);
expect("second identical line served from cache", calls, 1);
// Eleven v4: Text to Dialogue at raw 16kHz PCM, the text (tags and all) passed through untouched
await worker.fetch(post({ text: "[whispering] hi there", format: "pcm8" }), env("k"), ctx);
expect("v4 endpoint", sent.u, "https://api.elevenlabs.io/v1/text-to-dialogue?output_format=pcm_16000");
expect("v4 model", sent.body.model_id, "eleven_v4");
expect("tags pass through", sent.body.inputs[0].text, "[whispering] hi there");
globalThis.fetch = realFetch;
console.log("PASS: /api/speak rejects empty text, other sites and a missing key, and caches repeats");

// On his own site the Joshua persona speaks as him: the reader's third-person sentence becomes first person
const { asJoshua } = await import("../worker.js");
for (const [a, want] of [
  ["Joshua Trommel is a developer in Vancouver, Canada, who builds apps.", "I'm a developer in Vancouver, Canada, who builds apps."],
  ["Joshua Trommel builds apps, a programming language, and an operating system.", "I build apps, a programming language, and an operating system."],
  ["He writes in C, Swift, JavaScript and Python.", "I write in C, Swift, JavaScript and Python."],
  ["Joshua Tree is his operating system.", "Joshua Tree is my operating system."],
  ["His site is heyitsmejosh.com.", "My site is heyitsmejosh.com."],
  ["Joshua was born to ship.", "I was born to ship."],
  ["I'm based in Vancouver, Canada, and writes in C, Swift.", "I'm based in Vancouver, Canada, and write in C, Swift."],
]) expect("asJoshua " + a, asJoshua(a), want);
console.log("PASS: Joshua speaks as himself");
