# Turing loop handoff (2026-09-23, evening)

## What the loop is

One ability per minor release, a major when a whole roadmap family completes, until version 10. Each round: a frontier check first (ChatGPT, Claude, Gemini, Apple Intelligence, Operator-style agents; any real gap goes under "Gaps found by the loop" in roadmap.md with where it was seen), then the easiest, most relevant open gap, built, dogfooded for real on this Mac (the new ability plus one old one), full gate plus every file in tests/ green, docs and landing page in the same commit, push, CI checked, a line in docs/PROGRESS.md. Celebrate at 5.0.0 and 6.0.0 (4.0.0 and 100 tools are done). Every version gets a tag and a GitHub release from release.yml.

## Where things stand

v4.0.1, 101 tools (audited, all distinct), 275 tests, docs 100%, laws all hold, CI green. Today shipped v3.5.0 through v4.0.1: transcribe_video, unread_mail, summarize, translate, timed reminders, the files family (read and write halves), the docs de-spam, and the tidy (tests/, training/, swift/, roadmap 94 KB to 15 KB with docs/HISTORY.md, README simplified with docs/ABILITIES.md). Usage was the limit at close, not the work.

## Found today, worth knowing

- The 9B through Ollama takes over five minutes to load cold on this Mac; twice a 280 second and once a 900 second budget was not enough after a long idle. Warm it with a throwaway ask first, then do the real one. Once warm it answers in seconds (summarize and translate were both verified that way).
- Spotlight lags a few seconds on a brand new file; find_file now walks the usual folders before saying no.
- Reminders AppleScript: a `whose due date < d` filter errors on reminders with no due date (missing value); check inside the loop instead.
- mlx_whisper already shells out to ffmpeg, so a video needs no audio extraction step; transcribe_video is one function.
- Moving files into folders broke three tests that assumed the repo root (test_chat, test_tools_image, test_edges) and the scorecard's test count; all fixed, but the local gate only runs a subset, so run every file in tests/ before pushing. CI runs them all.
- At close, this checkout was on a branch named jt-chat that another session created; v4.0.1 was committed there and fast-forwarded onto main. Check `git branch --show-current` before committing.

## Next, in order

1. Docs in her voice: the README intro is hand-written to SOUL.md; the 9B timed out cold twice. Warm it first (any ask), then have it redo the README intro, docs/ABILITIES.md and WHITEPAPER.md in first person, check facts and house rules by hand.
2. What needs me: one answer from unread mail, today's calendar and due reminders. The Reminders AppleScript must skip `missing value` due dates inside the loop, a `whose` filter on due date errors out (probed today).
3. Am I free: calendar gaps for a day or a week.
4. Camera eyes: one frame through ffmpeg avfoundation, then see_image.
5. Edit the last draft: rewrite the file write_document just saved, showing the diff, asking first.
6. Then the remaining gaps in roadmap.md, easiest first. tools.py is at 737 of 760 lines: the next tool there forces a split.

## Restart prompt

```
/loop until version 10. ultrathink
keep close watch on usage. read docs/LOOP-HANDOFF.md first.
```
