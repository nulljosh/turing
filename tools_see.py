"""Her eyes: a local vision model (Qwen2.5-VL 3B on MLX, about 2GB) looks at a picture or the screen and answers a
question about it. Reading the screen already worked for text (Vision OCR); this sees what is not text: photos,
charts, icons, layouts. Nothing leaves the Mac. Both tools are private, so they ask first and are only used by name.

    "what's on my screen", "look at my screen and tell me what's wrong with this chart"
    "what's in ~/Desktop/cat.png", "describe ~/Pictures/trip.jpg"
"""
import os
import subprocess
import tempfile

MODEL = os.environ.get("SAMANTHA_VISION", "mlx-community/Qwen2.5-VL-3B-Instruct-4bit")
IMAGES = (".png", ".jpg", ".jpeg", ".heic", ".gif", ".webp", ".tiff", ".tif", ".bmp")
_eyes = None  # (model, processor, config), loaded on first look and kept


def _headless():
    """True when nothing visible may happen (evals, tests)."""
    return os.environ.get("SAMANTHA_HEADLESS") == "1"


def _load():
    """The vision model, loaded once. Raises OSError when mlx-vlm or the weights are not here."""
    global _eyes
    if _eyes is None:
        try:
            from mlx_vlm import load
            from mlx_vlm.utils import load_config
            model, processor = load(MODEL)
            _eyes = (model, processor, load_config(MODEL))
        except Exception as e:
            raise OSError(f"vision model unavailable: {e}") from e
    return _eyes


def look(image, question):
    """What the vision model says about one image file, in a few plain sentences."""
    from mlx_vlm import generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, processor, config = _load()
    ask = (question.strip() or "Describe what you see.") + " Answer in two or three plain sentences. If you cannot tell, say so."
    prompt = apply_chat_template(processor, config, ask, num_images=1)
    got = generate(model, processor, prompt, image=[image], max_tokens=200, verbose=False)
    return (getattr(got, "text", got) or "").strip()


def _answer(image, question):
    """look(), with every failure as a sentence."""
    try:
        said = look(image, question)
    except OSError:
        return "My eyes need the vision model: .venv/bin/pip install mlx-vlm, then ask again (the first look downloads about 2GB)."
    except Exception as e:
        return f"I could not look at that: {e}"
    return (said or "").strip() or "I looked but could not make anything out."


def see_screen(question=""):
    """Look at the screen right now and answer a question about it, or describe it. Asks first; stays on the Mac."""
    if _headless():
        return "Would look at the screen."
    fd, shot = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        subprocess.run(["screencapture", "-x", "-m", "-t", "png", shot], timeout=15, check=False)
        if os.path.getsize(shot) == 0:
            return "I could not capture the screen. Screen Recording may need to be allowed for this terminal."
        return _answer(shot, question)
    finally:
        os.unlink(shot)


def see_image(request):
    """Look at a picture in the home folder and answer about it. Takes 'question<TAB>path' or just a path. Asks first."""
    import tools_util
    question, _, path = request.rpartition("\t")
    full = tools_util._home_path(path)
    if not full or not os.path.isfile(full):
        return f"I do not see a picture at {path.strip() or 'that path'} in your home folder."
    if not full.lower().endswith(IMAGES):
        return "That is not a picture I can look at: png, jpg, heic, gif, webp, tiff or bmp."
    if _headless():
        return f"Would look at {os.path.basename(full)}."
    return _answer(full, question)
