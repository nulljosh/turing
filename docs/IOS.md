# Samantha for iPhone

Her models run on the phone. Her tool picker (the Kaggle-trained Qwen2.5-1.5B, 4-bit) and a small instruct model answer on-device through MLX, her hands reach the phone's own apps (Reminders, Calendar, Contacts, Photos, the clipboard, Shortcuts), and anything that changes something asks first, same as on the Mac. The Mac is optional: paired over your own network it lends its bigger model and its own tools. Nothing goes to a cloud. Joshua, 2026-10-11: "The LLM should be local, that's the point. We should be able to do anything like with Claude: generate code, use tools, access apps. With Claude I can ask it to clean up my Reminders."

## Where things stand (2026-10-11)

- Shell: `ios/` (xcodegen `project.yml`, SwiftUI, iOS 17+, bundle id `com.nulljosh.samantha`). Home, chat, composer, drawer, confirm sheet, settings, light and dark, screenshotted and graded below.
- Her exact tools on the phone: `ios/App/Twins.swift` loads `web/samantha.js` in JavaScriptCore, so the router and the 49 JavaScript twins (word-for-word parity with the Mac) answer instantly and offline. Tools that need a real Mac (its disk, Wi-Fi, Finder, Shortcuts) are routed to the paired Mac when there is one.
- Her models on the phone: `ios/App/LocalModel.swift` loads the picker (`trommatic/samantha-hands-1.5b-mlx`) and an instruct model (`mlx-community/Qwen2.5-1.5B-Instruct-4bit`) with MLX Swift, downloaded from Hugging Face once from Settings, the same `{"tool","arg"}` prompt as `app/tools_agent.py`. Order of play in `Store.run`: exact twin, then the phone's models, then the Mac. MLX does not run in the simulator, so the models are checked by a device build (`generic/platform=iOS`) and tried on Joshua's phone.
- Mac bridge, shipped in v5.11.13: `app/phone_bridge.py` (signed requests, Server-Sent Events, confirm round trip). The optional path.
- Video QA (2026-10-11): the simulator walkthrough graded B+. Finds fixed the same round: the port field showed "8,128", and Recents piled up chats from earlier test runs (mock launches now get a fresh folder).
- Next, in order: (1) iOS hands: Reminders and Calendar through EventKit (list, add, complete, clean up stale ones), Contacts, Photos, clipboard, open a URL or app, run a Shortcut, all writes behind the confirm sheet; (2) profiles: Sign in with Apple and a name for the greeting, chats and memory per person, synced only through your own iCloud (Joshua, 2026-10-11: "we can even add user authentication and profiles"); (3) the Mac app joins this codebase; (4) voice; (5) polish until every screen grades A, then the store.

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
