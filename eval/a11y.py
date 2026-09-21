"""Accessibility audit of the live landing page with axe-core, in four modes: desktop and phone, light and dark.

Fails on any WCAG 2 A or AA violation or best-practice issue. axe-core is fetched from jsDelivr at run time, so nothing
is vendored. The page runs with reduced motion so scroll reveals do not hide sections from the audit.

Run: .venv/bin/python eval/a11y.py [URL]     (gate.sh --full runs it against the live site)
"""
import sys
import urllib.request

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://turing.heyitsmejosh.com"
AXE = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"
RUN = ("() => axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']}})"
       ".then(r => r.violations.map(v => v.id + ' x' + v.nodes.length + ': ' + v.help))")


def main():
    """Audit each mode, print what fails, exit 1 if anything does."""
    axe = urllib.request.urlopen(AXE, timeout=30).read().decode()
    failed = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, size in (("desktop", {"width": 1200, "height": 900}), ("phone", {"width": 390, "height": 844})):
            for scheme in ("light", "dark"):
                page = browser.new_context(viewport=size, color_scheme=scheme, reduced_motion="reduce").new_page()
                page.goto(URL, wait_until="networkidle")
                page.wait_for_timeout(1200)
                page.evaluate(axe)
                found = page.evaluate(RUN)
                failed += len(found)
                print(f"[{'FAIL' if found else 'PASS'}] {name} {scheme}: {'; '.join(found) or 'no violations'}")
    print(f"{'BROKEN' if failed else 'ok'}: {failed} accessibility problems")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
