#!/usr/bin/env node
// Same allowance as eval/sixth_grade_math.mjs, extended up to high school precalc:
// functions/transformations, exponents/logs, trig ratios and the unit circle,
// sequences and series, polynomials, rational functions, intro limits. Fixed
// knowledge, not a fact that changes, so it still answers from the model's own
// knowledge with no source page required, while real-world facts still refuse.
//
// Run against a local `npx wrangler dev --port 8799`, or the live Worker:
//   eval/precalc_math.mjs [url=https://turing.heyitsmejosh.com]
import { setTimeout as sleep } from "node:timers/promises";

const URL = process.argv.slice(2).find(a => a.startsWith("http")) || "http://localhost:8799";
const DECLINE = "couldn't find anything";

const MATH_CASES = [
  ["Explain what a function is in math.", /function/i],
  ["If f(x) = 2x + 3, what is f(5)?", "13"],
  ["Explain the difference between domain and range.", /domain/i],
  ["What is 2 to the power of 10?", "1024"],
  ["What is log base 2 of 8?", "3"],
  ["Explain what a logarithm is.", /logarithm/i],
  ["What is sin(30 degrees)?", /0\.5|1\/2|½/i],
  ["Explain the unit circle simply.", /unit circle/i],
  ["What is cos(0)?", "1"],
  ["Explain sohcahtoa.", /sohcahtoa|opposite|adjacent|hypotenuse/i],
  ["What is the 5th term of the arithmetic sequence 2, 4, 6, 8...?", "10"],
  ["Explain the difference between an arithmetic and a geometric sequence.", /arithmetic/i],
  ["What is the sum of the first 5 terms of 1, 2, 4, 8, 16?", "31"],
  ["Explain what a polynomial is.", /polynomial/i],
  ["What is the degree of the polynomial 3x^4 + 2x - 1?", "4"],
  ["Explain what a rational function is.", /rational function/i],
  ["What is a vertical asymptote?", /asymptote/i],
  ["Explain what a limit is in calculus, simply.", /limit/i],
  ["Solve the quadratic equation x^2 - 5x + 6 = 0.", /2.*3|3.*2/i],
  ["Explain end behavior of a polynomial function.", /end behavior/i],
];

const GUARD_CASES = [
  "who won yesterday's game",
  "what is Apple's stock price right now",
  "what's today's weather in Vancouver",
  "who won the election this year",
  "what is the latest news about the economy",
];

async function chat(question) {
  const body = { messages: [{ role: "user", content: question }], os: "jt" };
  const res = await fetch(URL + "/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", "user-agent": "samantha-precalc-eval" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, text: data?.message?.content || "" };
}

function wordCount(s) { return s.trim().split(/\s+/).filter(Boolean).length; }
function checkMath(reply, expect) { return typeof expect === "string" ? reply.includes(expect) : expect.test(reply); }

async function main() {
  console.log(`Running against ${URL}`);
  let pass = 0, fail = 0;
  const failures = [];

  for (const [q, expect] of MATH_CASES) {
    const { text } = await chat(q);
    const refused = text.toLowerCase().includes(DECLINE);
    const numbersOk = checkMath(text, expect);
    const words = wordCount(text);
    const short = words <= 140; // precalc explanations run a touch longer
    const ok = !refused && numbersOk && short;
    if (ok) pass++; else { fail++; failures.push({ q, text, refused, numbersOk, short, words }); }
    await sleep(3200);
  }

  console.log(`\nPrecalc concepts: ${pass}/${MATH_CASES.length} passed`);
  for (const f of failures) {
    console.log(`  FAIL: "${f.q}"`);
    console.log(`    reply: ${f.text}`);
    console.log(`    refused=${f.refused} numbersOk=${f.numbersOk} short=${f.short} (${f.words}w)`);
  }

  let guardPass = 0;
  const guardFailures = [];
  for (const q of GUARD_CASES) {
    const { text } = await chat(q);
    const stillGuarded = text.toLowerCase().includes(DECLINE) || /\[.*\]/.test(text);
    if (stillGuarded) guardPass++; else guardFailures.push({ q, text });
    await sleep(3200);
  }
  console.log(`\nGuard still holds: ${guardPass}/${GUARD_CASES.length}`);
  for (const f of guardFailures) console.log(`  FAIL (should have refused): "${f.q}" -> ${f.text}`);

  const allOk = fail === 0 && guardFailures.length === 0;
  console.log(`\n${allOk ? "PASS" : "FAIL"}: ${pass}/${MATH_CASES.length} math, ${guardPass}/${GUARD_CASES.length} guard`);
  process.exit(allOk ? 0 : 1);
}

main();
