# Security

## Reporting

Found something? Email **trommatic@icloud.com**. Don't open a public issue for anything exploitable.

You'll hear back within a week. This is a solo side project. No bounty, no SLA, just a reply.

## Supported versions

The deployed version and the tip of `main`. Nothing else.

## What's guarded

Samantha has hands, so the guards are the product.

On the Mac, she only reads inside your home folder. Hidden files are refused outright, so `.ssh` and `.env` stay unread. When a model picks a tool, `_sound()` checks the pick: the tool must exist, and its argument must come from your own words. She can't invent one.

On the landing page, nothing she does leaves your browser tab. The page writes text, never markup. A strict CSP allows no outside scripts and no `eval`. `/api/ask`, `/api/pick` and `/api/draw` take JSON from this site only, at 20 calls a minute per visitor, and drawing gets its own limit of 5 a minute because a picture costs real compute. A short list of words the image endpoint refuses, a 120 character cap, and a day of caching for repeat prompts keep it small. The reader model answers from the article in front of it or declines. Every reply is capped, so no upstream can flood the chat.

`eval/web_demo.py` attacks all of this in headless Chromium: script injection, `javascript:` links, prompt leaks, made-up tools. It runs before every deploy.

## Not in the repo

Training data and adapters are built from private notes. They are gitignored and never pushed.
