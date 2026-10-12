# Turing loop handoff (2026-10-11, evening)

## What the loop is

A `/loop` that QAs the three things people see, one at a time: the iOS app in the simulator, the Mac app, and the website demo. Each run records a video, grades it, fixes what the video shows, and repeats until every part grades A+.

A round ends with a fix shipped or an honest "not yet" for that part. Every shipped fix gets a version tag and a release. Hard stop and checkpoint at 90 percent usage.

## Where things stand

- **Live:** v5.14.0 adds Samantha Sans, her own typeface, on the site and in the Mac and iPhone apps. Before it, v5.12.3 added code blocks with a Copy button in the Mac app, on the phone and on the landing, makes the phone app build for Mac, and fixes model labels.
- **Shipped earlier today, from v5.11.4 on:** the live demo on the landing page is back (it had been dead since v5.9.0, a syntax error in its script); the Mac app keeps focus, ships its icon and keeps her weights in its own Application Support folder; a time-zone bug on the landing page is fixed; training run 23 became the hands picker (v5.12.0); the landing shows her flat mascot icon; the phone bridge takes signed requests; the iPhone app runs her exact tools in JavaScriptCore and loads her models with MLX Swift on the phone, with the Mac optional; the iPhone app has a splash screen.
- **Picker:** training run 23, shipped as v5.12.0. Sealed 619-sentence test: 351 right picks (v5.0 had 317), 79 wrong (126), 27 past the guard (30), about 4 percent refusals. The under-2-percent refusal goal is still open. Weights: https://huggingface.co/trommatic/samantha-hands-1.5b-mlx. The 0.5B GGUF for Windows and Linux stays at trommatic/samantha-hands-gguf.
- **Grades so far:** the iOS simulator walkthrough of eight questions graded A-. The landing demo recorded 8/8. No part has an A+ grade yet.
- **Sealed sets** are read as counts only. Never tune on their misses.
- **Working tree:** the loop's current round has uncommitted edits in progress across `app/`, `gui/`, `ios/`, `web/`, `.github/workflows/test.yml` and `docs/ARCHITECTURE.md`. None of it is part of a release yet. Commit only by exact path, and only after that round's checks pass.
- **Blocked:** the image model test waits for 10 GB free memory. Qwen-Image-2.1-Turbo needs 12 to 16 GB on this Mac.

## Next, in order

1. iOS QA: record the simulator walkthrough (at least 30 seconds, 5 to 10 questions), grade it, fix what the video shows, and repeat until A+.
2. Mac QA: same loop for the Mac app, now with the Copy buttons in place.
3. Website QA: record the landing demo, grade it, fix what it shows, and repeat until A+.
4. Profiles with Sign in with Apple.
5. iOS hands: Reminders and Calendar.
6. Store submission at $1, once each app grades A.

## Restart prompt

```
/loop until a+ : record a video of QAing the iOS app (simulator), the Mac app and the website demo, grade it, fix what it shows, repeat until every part grades A+. The iOS video must be at least 30 seconds long and walk 5-10 questions.
```
