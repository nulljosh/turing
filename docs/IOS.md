# Samantha for iPhone

Her models run on the phone. Her tool picker (the Kaggle-trained Qwen2.5-1.5B, 4-bit) and a small instruct model answer on-device through MLX, her hands reach the phone's own apps (Reminders, Calendar, Contacts, Photos, the clipboard, Shortcuts), and anything that changes something asks first, same as on the Mac. The Mac is optional: paired over your own network it lends its bigger model and its own tools. Nothing goes to a cloud. Joshua, 2026-10-11: "The LLM should be local, that's the point. We should be able to do anything like with Claude: generate code, use tools, access apps. With Claude I can ask it to clean up my Reminders."

## Where things stand (2026-10-11)

- Shell, first build: `ios/` (xcodegen `project.yml`, SwiftUI, iOS 17+, bundle id `com.nulljosh.samantha`). Home, chat, composer, drawer, confirm sheet, settings, light and dark, screenshotted and graded below. Runs against a mock Samantha and against the Mac bridge; not yet against a model on the phone.
- Mac bridge, shipped in v5.11.13: `app/phone_bridge.py` (signed requests, Server-Sent Events, confirm round trip). Now the optional path.
- Next, in order: (1) her 49 exact tools on the phone by loading `web/samantha.js` in JavaScriptCore (the router and the JavaScript twins already pass word-for-word parity with the Mac); (2) the picker and an instruct model on-device with MLX Swift, downloaded from Hugging Face on first run (`trommatic/samantha-hands-1.5b-mlx` plus `mlx-community/Qwen2.5-1.5B-Instruct-4bit`), the same `{"tool","arg"}` prompt as `app/tools_agent.py`; (3) iOS hands: Reminders and Calendar through EventKit (list, add, complete, clean up stale ones), Contacts, Photos, clipboard, open a URL or app, run a Shortcut, all writes behind the confirm sheet; (4) voice; (5) polish until every screen grades A. MLX does not run in the simulator, so on-device inference is checked by a device build (`generic/platform=iOS`) and tried on Joshua's phone.

## The screens, graded against the Claude app (first build, 2026-10-11)

| Screen | What it needs | Grade | What is missing for an A |
|---|---|---|---|
| Home | Her mark, a time-of-day greeting, the composer pill | A- | Her name for you in the greeting |
| Chat | Assistant text plain, user text in a soft gray bubble on the right, streaming reply, a "Working: tool" row, copy and retry under replies | A- | Replies land whole; on-device generation will stream them |
| Composer | Pill at the bottom, plus button, send button in terracotta, grows with the text | B+ | The plus button does nothing yet; Claude's also has a voice button |
| Top bar | Sidebar button, centered title, new chat button | A | |
| History | Slide-over list of past chats, persisted as JSON | B+ | Search, and grouping by day like Claude's |
| Confirm | A sheet for writes: what she is about to do, Yes and No | A | |
| Settings | Pairing with the Mac (host, port, token from the samantha://pair link), test connection | B | Was iOS blue and green on a gray form; now paper and terracotta. Needs the model download state once models are on-device |
| Voice | Dictation in, replies spoken out | not built | |

Rules: SF Pro only, no serif, no emojis, no gradients, no shadows. Warm off-white #faf9f5 in light, #1f1e1d in dark, terracotta #b5502c only on the send button and the yes button. Build check every slice: `xcodebuild -destination 'generic/platform=iOS Simulator' build`. Screenshots: `ios/UITests/Shots.swift` walks every screen with the mock Samantha and writes PNGs (`TEST_RUNNER_SHOTS_DIR`, `TEST_RUNNER_SHOTS_PREFIX`), run once per appearance with `xcrun simctl ui <device> appearance light|dark` between; shut the simulator down after. The loop never submits to TestFlight or the App Store.

## Pairing the Mac, in words

Start the bridge on the Mac (`./.venv/bin/python app/phone_bridge.py --lan`), it prints a `samantha://pair?...` link. Open it on the phone (or type host, port and token into Settings). From then on every request carries a timestamp, a nonce and an HMAC under that secret; the secret itself never crosses the network. A write on the Mac still asks on the phone before it happens.
