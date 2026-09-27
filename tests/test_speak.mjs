// /api/speak's kernel format: 16-bit signed PCM from ElevenLabs becomes 8-bit unsigned, silence at 128.
import { pcm16ToPcm8 } from "../worker.js";
const b = new ArrayBuffer(8), v = new DataView(b);
[0, 32767, -32768, 256].forEach((x, i) => v.setInt16(i * 2, x, true));
const out = Array.from(pcm16ToPcm8(b));
if (out.join() !== "128,255,0,129") { console.log("FAIL", out); process.exit(1); }
console.log("PASS: pcm16 to pcm8");
