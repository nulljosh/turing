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
