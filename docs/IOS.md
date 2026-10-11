# Samantha for iPhone

A thin client to your own Mac. Her hands, files and memory stay on the Mac; the phone talks to `app/phone_bridge.py` over your own network, every request signed with a pairing secret, nothing in a cloud. The look is the Claude iPhone app: calm, warm, text first.

## Where things stand (2026-10-11)

- Mac side shipped in v5.11.13: `app/phone_bridge.py` (POST /v1/ask streams her `{working}`, `{confirm}` and `{answer}` messages as Server-Sent Events; POST /v1/confirm carries the phone's yes or no; GET /v1/ping tests pairing). Started by hand, never a daemon. `tests/test_phone_bridge.py` covers signatures, replays, the stream order and the confirm round trip.
- iOS side: not started. Lives in `ios/` (xcodegen `project.yml`, SwiftUI, iOS 17+, bundle id `com.heyitsmejosh.samantha`).

## The screens, graded against the Claude app

| Screen | What it needs | Grade |
|---|---|---|
| Home | Her mark, a time-of-day greeting, the composer pill | not built |
| Chat | Assistant text plain, user text in a soft gray bubble on the right, streaming reply, a "Working: tool" row, copy and retry under replies | not built |
| Composer | Pill at the bottom, plus button, send button in terracotta, grows with the text | not built |
| Top bar | Sidebar button, centered title, new chat button | not built |
| History | Slide-over list of past chats, persisted as JSON like the Mac app | not built |
| Confirm | A sheet for writes: what she is about to do, Yes and No | not built |
| Pairing | Host, port, token (from the samantha://pair link the bridge prints), test connection | not built |
| Voice | Dictation in, replies spoken out | not built |

Rules: SF Pro only, no serif, no emojis, no gradients, no shadows. Warm off-white #faf9f5 in light, #1f1e1d in dark, terracotta #b5502c only on the send button. Build check every slice: `xcodebuild -destination 'generic/platform=iOS Simulator' build`. Screens get headless screenshots and an honest grade here; the work is done when every row says A. Never submitted to TestFlight or the App Store by the loop.

## Pairing, in words

Start the bridge on the Mac (`./.venv/bin/python app/phone_bridge.py --lan`), it prints a `samantha://pair?...` link. Open it on the phone (or type host, port and token into Pairing). From then on every request carries a timestamp, a nonce and an HMAC under that secret; the secret itself never crosses the network. A write still asks on the phone before it happens.
