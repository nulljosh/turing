"""Her document tools, split out of app/tools_util.py (law 8, 5.11.1): the home-folder fence (_home_path), the text of a
PDF, Word, RTF, HTML or plain file (_doc_text), read_document, transcribe_video, find_in_document, ask_document (the small
local reader over the closest passages), word_count on a file, and doc_pair, the 'words<TAB>path' split the guard reuses.
tools_util re-exports every name here, so nothing that imported them from there changes.
"""
import json
import os
import re
import urllib.request

from util_words import _words  # noqa: E402


def _sh(argv, timeout=5):
    """tools_util's shell helper, looked up at call time (tools_util imports this module while it loads)."""
    import tools_util
    return tools_util._sh(argv, timeout=timeout)


def _home_path(path):
    """The real path of something inside the home folder, or None: outside it, hidden, or not there."""
    home = os.path.realpath(os.path.expanduser("~"))
    full = os.path.realpath(os.path.expanduser(path.strip().strip("'\"")))
    rel = os.path.relpath(full, home)
    if rel.startswith("..") or any(part.startswith(".") and part != "." for part in rel.split(os.sep)) or not os.path.exists(full):
        return None
    return full


def _doc_text(path):
    """The text of a PDF, Word, RTF, HTML or plain text file, or (None, why). Home folder only, never hidden files."""
    full = _home_path(path)
    if not full or not os.path.isfile(full):
        return None, f"No file {path.strip()} I am allowed to read."
    ext = os.path.splitext(full)[1].lower()
    if ext == ".pdf":
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "swift", "pdf.swift")
        text = _sh(["swift", script, full], timeout=90)
    elif ext in (".docx", ".doc", ".rtf", ".rtfd", ".html", ".htm", ".odt", ".webarchive"):
        text = _sh(["textutil", "-convert", "txt", "-stdout", full], timeout=30)
    elif ext in (".txt", ".md", ".csv", ".json", ".log", ""):
        try:
            text = open(full, errors="replace").read(400_000)
        except OSError:
            text = ""
    else:
        return None, f"I do not read {ext} files."
    text = re.sub(r"[ \t]+", " ", text or "").strip()
    return (text, None) if text else (None, "I found no text in that file. It may be a scan.")


def read_document(path):
    """Read the text of a PDF, Word, RTF, HTML or text file in the home folder. The first 3000 characters."""
    text, why = _doc_text(path)
    return why if why else re.sub(r"\s*\n\s*", " ", text)[:3000]


_VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".aac", ".flac")


def transcribe_video(path):
    """What is said in a video or audio file in the home folder, via the same Whisper pipeline voice.py uses for the
    mic (ffmpeg decodes the audio track from any container, so a video needs no separate extraction step)."""
    full = _home_path(path)
    if not full or not os.path.isfile(full):
        return f"No file {path.strip()} I am allowed to read."
    if os.path.splitext(full)[1].lower() not in _VIDEO_EXTS:
        return f"I do not transcribe {os.path.splitext(full)[1] or 'that'} files."
    import voice
    text = voice.transcribe(full)
    return text if text else "I heard no speech in that file."


def doc_pair(request):
    """'words<TAB>path' as (words, path). Round twenty: the picker sometimes skips the tab ("xyz in ~/documents/report.pdf");
    a trailing path or file name after "in" is the second half."""
    words, _, path = request.partition("\t")
    if not path:
        m = re.match(r"(.+?)\s+(?:in|from|inside)\s+((?:~/|/)?\S+\.\w{2,5})$", request.strip(), re.I)
        words, path = (m.group(1), m.group(2)) if m else (words, "")
    return words.strip(), path.strip()


def word_count(text):
    """Count the words and characters in some text, or in a document when the text is the path of one in your home folder
    ("how many words are in ~/Documents/essay.md" counted the path's own letters before 5.11.1)."""
    import util_math
    doc = _doc_text(text)[0] if re.fullmatch(r"[~/.\w-]*/[^\s]+\.\w{1,5}|[^\s]+\.\w{1,5}", text.strip().strip("'\"")) else None
    return util_math.word_count(doc if doc else text)


def find_in_document(request):
    """Find the passages of a document that mention some words. Takes 'words<TAB>path'. Up to three passages."""
    words, path = doc_pair(request)
    text, why = _doc_text(path)
    if why:
        return why
    want = _words(words)
    if not want:
        return "Tell me what to look for."
    flat = re.sub(r"\s+", " ", text)
    hits, seen = [], 0
    for m in re.finditer(r"[^.!?\n]{0,160}(?:" + "|".join(re.escape(w) for w in sorted(want)) + r")[^.!?\n]{0,160}", flat, re.I):
        if m.start() < seen:
            continue
        hits.append(m.group(0).strip())
        seen = m.end()
        if len(hits) == 3:
            break
    return " | ".join(hits) if hits else f"I do not see {words.strip()} in that document."


OLLAMA_CHAT = "http://localhost:11434/api/chat"
READER = "qwen3:1.7b"  # the same small reader ask.py uses for articles: it reads text, it does not recall


def _passages(text, question, limit=5000):
    """The parts of a long text that share the most words with a question, in reading order, up to a size limit."""
    if len(text) <= limit:
        return text
    chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if c.strip()]
    want = _words(question)
    ranked = sorted(range(len(chunks)), key=lambda i: -len(want & _words(chunks[i])))
    keep, size = [], 0
    for i in ranked:
        if size + len(chunks[i]) > limit:
            break
        keep.append(i)
        size += len(chunks[i]) + 1
    return " ".join(chunks[i] for i in sorted(keep))


def _read_and_answer(text, question):
    """Ask the local reader model one question about a text and check the answer against the text. None if it cannot say."""
    body = json.dumps({"model": READER, "stream": False, "think": False, "options": {"temperature": 0}, "messages": [
        {"role": "system", "content": "Answer the question in one short sentence using ONLY the text. If the text does not contain the answer, reply exactly UNKNOWN."},
        {"role": "user", "content": f"Text:\n{_passages(text, question)}\n\nQuestion: {question}"}]}).encode()
    try:
        req = urllib.request.Request(OLLAMA_CHAT, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            answer = json.load(r)["message"]["content"]
    except Exception:
        return "NO_MODEL"
    answer = re.sub(r"(?s)<think>.*?</think>", "", answer).strip()
    # every number and every capitalised name in the answer must be in the text or in the question: a guess is worse than a decline
    claims = re.findall(r"\d[\d,.]*\d|\d|\b[A-Z][a-z]{2,}\b", answer)
    grounded = all(c.lower().rstrip(".,") in text.lower() or c.lower() in question.lower() for c in claims[1:] or claims)
    declined = re.search(r"unknown|does not (?:contain|mention|say|provide|specify)|doesn't (?:contain|mention|say)|not (?:mentioned|stated|specified|provided)|no (?:information|mention)", answer, re.I)
    return None if not answer or declined or not grounded else answer


def ask_document(request):
    """Answer a question about a document in the home folder, from its text only. Takes 'question<TAB>path'. Needs Ollama running."""
    question, path = doc_pair(request)
    text, why = _doc_text(path)
    if why:
        return why
    if not question.strip():
        return "Ask me something about the document."
    got = _read_and_answer(text, question)
    if got == "NO_MODEL":
        return "My reader needs Ollama running with " + READER + ". These are the closest passages instead: " + find_in_document(question + "\t" + path)
    return got or "I could not find that in the document."
