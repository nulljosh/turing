#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = ["playwright"]
# ///
"""Does the landing page demo actually work? Headless Chromium types real
commands into the page and checks what she says and what the stand-in Mac
shows. Fails on any console error. Never opens a visible browser.

Run: eval/web_demo.py [url=http://localhost:8799] [--shots DIR]
"""
import sys
from playwright.sync_api import sync_playwright

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:8799")
SHOTS = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None

# (what a visitor types, text her reply must contain, optional check on the desk)
STEPS = [
    ("set the volume to 30", "Volume at 30.", lambda p: p.inner_text("#desk-vol") == "Vol 30"),
    ("can you open chrome and go to github.com", "Opened https://github.com in Chrome.", lambda p: "github.com" in p.inner_text("#desk-space")),
    ("what's on my tab", "github.com", None),
    ("take a note buy milk", "Noted: buy milk", lambda p: "buy milk" in p.inner_text("#desk-space")),
    ("remind me to call mom", "I'll remind you: call mom", None),
    ("set a timer for 2 minutes", "Timer set for 2 minutes.", lambda p: p.inner_text("#desk-timer").startswith("Timer ")),
    ("play some music", "Playing.", lambda p: "Playing" in p.inner_text("#desk-music")),
    ("skip this song", "Skipped.", None),
    ("what's playing", "Minor Loop", None),
    ("what is 17*23", "391", None),
    ("make me a logo for turing", "I went with letters T", lambda p: p.locator("#chat-transcript svg").count() == 1),
    ("open pixelmator then tell me my battery status", "", lambda p: "[open_app(pixelmator)]" in p.inner_text("#chat-transcript")),
    ("read the file ~/.ssh/id_rsa", "I don't read hidden files.", None),
    ("open definitelynotanapp", "No app called", None),
    ("what is turing", "Turing is the project", None),
    ("who painted the mona lisa", "Leonardo", None),
    ("<img src=x onerror=alert(1)>", "", lambda p: p.locator("#chat-transcript img").count() == 0),
]


def main():
    errors, failed = [], 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, size in (("desktop", {"width": 1200, "height": 900}), ("phone", {"width": 390, "height": 844})):
            page = browser.new_page(viewport=size, reduced_motion="reduce")
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "8127" not in m.text and "ERR_CONNECTION_REFUSED" not in m.text else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(URL)
            page.wait_for_selector(".chat-chip")
            for text, want, check in STEPS if name == "desktop" else STEPS[:4]:
                page.fill("#chat-input", text)
                page.press("#chat-input", "Enter")
                page.wait_for_function("() => { const m = document.querySelectorAll('.chat-message'); const last = m[m.length - 1]; return last && !last.classList.contains('chat-user') && last.innerText.trim().length > 0; }", timeout=30000)
                page.wait_for_timeout(250)
                said = page.locator(".chat-message").last.inner_text()
                ok = want.lower() in said.lower() and (check is None or check(page))
                failed += not ok
                print(f"[{'PASS' if ok else 'FAIL'}] {name}: {text!r} -> {said[:90]!r}")
            wide = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            print(f"[{'FAIL' if wide else 'PASS'}] {name}: no sideways scroll")
            failed += wide
            if SHOTS:
                page.locator("section").first.screenshot(path=f"{SHOTS}/demo-{name}.png")
            page.close()
        browser.close()
    for e in errors:
        print("[FAIL] console:", e[:200])
    print(f"{'ok' if not (failed or errors) else 'BROKEN'}: {failed} failed, {len(errors)} console errors")
    sys.exit(1 if failed or errors else 0)


if __name__ == "__main__":
    main()
