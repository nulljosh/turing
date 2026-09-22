"""Live smoke run of the ten image tools through a real, hidden Pixelmator Pro, checking what comes out.

Not part of CI (it needs a Mac with Pixelmator Pro and ImageMagick). ./gate.sh --full runs it. The tools write to
~/Desktop/samantha-*.png, never over the original. This found two broken tools the mocked tests could not: grayscale and
enhance were sending AppleScript that Pixelmator rejects.

Run: python3 eval/smoke_images.py
"""
import os
import shutil
import subprocess
import sys

os.environ["SAMANTHA_HEADLESS"] = "1"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import tools

SAMPLE = os.path.expanduser("~/samantha-smoke/mona.jpg")
DESK = os.path.expanduser("~/Desktop")


def magick(*argv):
    """Run ImageMagick and return its output, so a result can be measured instead of trusted."""
    return subprocess.run(["magick", *argv], capture_output=True, text=True).stdout.strip()


def rmse(a, b):
    """How different two images are, from ImageMagick's compare (it prints the number on stderr)."""
    return float(subprocess.run(["magick", "compare", "-metric", "RMSE", a, b, "null:"], capture_output=True, text=True).stderr.split()[0])


def size(name):
    """Width and height of one of the tools' output files."""
    w, h = magick("identify", "-format", "%w %h", os.path.join(DESK, name)).split()
    return int(w), int(h)


def main():
    """Run every tool on a 603x900 photo and check each output. Exit 1 on any failure."""
    if not (shutil.which("magick") and os.path.exists("/Applications/Pixelmator Pro.app")):
        print("skipped: needs ImageMagick and Pixelmator Pro")
        return
    os.makedirs(os.path.dirname(SAMPLE), exist_ok=True)
    shutil.copy(os.path.join(REPO, "web", "mona.jpg"), SAMPLE)
    fails = 0

    def check(name, arg, ok, what):
        """Run one tool and print PASS or FAIL with what was measured."""
        nonlocal fails
        reply = tools.TOOLS[name](arg)
        try:
            good = ok()
        except Exception as e:
            good, what = False, f"{what} ({e})"
        fails += not good
        print(f"[{'PASS' if good else 'FAIL'}] {name}: {what}" + ("" if good else f" | said: {reply[:120]}"))

    check("image_info", SAMPLE, lambda: "603x900" in tools.image_info(SAMPLE), "reads 603x900")
    check("grayscale_image", SAMPLE, lambda: float(magick("convert", f"{DESK}/samantha-grayscale.png", "-colorspace", "HSL", "-channel", "G",
                                                          "-separate", "+channel", "-format", "%[fx:mean]", "info:")) < 0.01, "saturation is near zero")
    check("enhance_image", SAMPLE, lambda: rmse(SAMPLE, f"{DESK}/samantha-enhanced.png") > 100, "differs from the original")
    check("flip_image", SAMPLE, lambda: size("samantha-flipped.png") == (603, 900), "keeps 603x900")
    check("rotate_image", SAMPLE + " by 90", lambda: size("samantha-rotated.png") == (900, 603), "becomes 900x603")
    check("resize_image", SAMPLE + " to 400", lambda: size("samantha-resized.png") == (268, 400), "becomes 268x400")
    check("crop_square", SAMPLE, lambda: size("samantha-square.png") == (603, 603), "becomes 603x603")
    check("convert_image", SAMPLE + " to png", lambda: size("samantha-converted.png") == (603, 900), "a PNG of the same size")
    check("upscale_image", SAMPLE, lambda: size("samantha-upscaled.png") == (1809, 2700), "three times bigger")
    check("remove_background", SAMPLE, lambda: magick("identify", "-format", "%A", f"{DESK}/samantha-nobg.png") == "Blend", "has a transparent background")
    print(f"{'BROKEN' if fails else 'ok'}: {fails} of 10 image tools failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
