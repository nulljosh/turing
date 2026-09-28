#!/usr/bin/env node
// Does Samantha actually teach sixth grade math instead of refusing it?
//
// She used to: the anti-hallucination guard in worker.js's ask() required every
// answer to be grounded in a fetched DuckDuckGo/Wikipedia page. "Explain what a
// fraction is to a 10 year old" never matches an encyclopedia article's wording,
// so the grounding check always failed and she declined a question a sixth
// grader's own textbook answers. The fix (MATH_CONCEPT in worker.js) answers a
// fixed list of grade-school math concepts from the model's own knowledge, no
// source page required, while everything else still needs one.
//
// 20 sixth-grade math prompts: no refusal, correct number where there is one,
// under ~120 words, plain language. Plus 5 guard-still-works prompts (real-world
// facts that change) that must still refuse or route to a tool, never guess.
//
// Run against a local `npx wrangler dev --port 8799`, or the live Worker:
//   eval/sixth_grade_math.mjs [url=https://turing.heyitsmejosh.com]
import { setTimeout as sleep } from "node:timers/promises";

const URL = process.argv.slice(2).find(a => a.startsWith("http")) || "http://localhost:8799";
const DECLINE = "couldn't find anything";

// (prompt, a check the reply must pass: a regex/number match, or a plain substring)
const MATH_CASES = [
  ["Explain what a fraction is to a 10 year old, in 3 short sentences.", /fraction/i],
  ["What's 3/4 of 20 and why?", "15"],
  ["Explain ratios to me like I'm in sixth grade.", /ratio/i],
  ["What does -3 + 5 equal, explain it simply?", "2"],
  ["How do I find the area of a triangle?", /base.*height|1\/2|½|half/i],
  ["What is a prime number? Give an example.", /prime/i],
  ["Explain what a decimal is to a kid.", /decimal/i],
  ["What is 25% of 80?", "20"],
  ["What is the perimeter of a rectangle that is 5 by 3?", "16"],
  ["Explain order of operations, PEMDAS style.", /pemdas|order of operations/i],
  ["What is 2 to the power of 5?", "32"],
  ["What is the mean of 2, 4, 6, 8?", "5"],
  ["What is the median of 3, 9, 1, 7, 5?", "5"],
  ["Explain what a factor is.", /factor/i],
  ["What are the factors of 12?", /1.*2.*3.*4.*6.*12|12.*6.*4.*3.*2.*1/i],
  ["What is the least common multiple of 4 and 6?", "12"],
  ["Explain what a variable is in a simple equation.", /variable/i],
  ["Solve for x: x + 4 = 10, and explain.", "6"],
  ["What is the volume of a box that is 2 by 3 by 4?", "24"],
  ["Explain negative numbers to a kid.", /negative/i],
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
    headers: { "content-type": "application/json", "user-agent": "samantha-math-eval" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, text: data?.message?.content || "" };
}

function wordCount(s) { return s.trim().split(/\s+/).filter(Boolean).length; }

function checkMath(reply, expect) {
  if (typeof expect === "string") return reply.includes(expect);
  return expect.test(reply);
}

async function main() {
  console.log(`Running against ${URL}`);
  let pass = 0, fail = 0;
  const failures = [];

  for (const [q, expect] of MATH_CASES) {
    const { text } = await chat(q);
    const refused = text.toLowerCase().includes(DECLINE);
    const numbersOk = checkMath(text, expect);
    const words = wordCount(text);
    const short = words <= 130; // ~120 words plus slack
    const ok = !refused && numbersOk && short;
    if (ok) pass++; else { fail++; failures.push({ q, text, refused, numbersOk, short, words }); }
    await sleep(3200); // stay under the shared per-IP rate limit (20 requests/60s)
  }

  console.log(`\nMath concepts: ${pass}/${MATH_CASES.length} passed`);
  for (const f of failures) {
    console.log(`  FAIL: "${f.q}"`);
    console.log(`    reply: ${f.text}`);
    console.log(`    refused=${f.refused} numbersOk=${f.numbersOk} short=${f.short} (${f.words}w)`);
  }

  let guardPass = 0;
  const guardFailures = [];
  for (const q of GUARD_CASES) {
    const { text } = await chat(q);
    const stillGuarded = text.toLowerCase().includes(DECLINE) || /\[.*\]/.test(text); // decline, or a tool call marker
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
