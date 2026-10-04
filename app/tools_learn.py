"""Learning tools: explain a codebase and give a lesson on a topic.

explain_codebase(project): reads a project's README, CLAUDE.md and folder list, then explains it plainly.
"explain this codebase to me", "walk me through turing".

teach_me(topic): a short lesson on a topic from Wikipedia and the library, plus two quiz questions,
using the local model. "teach me X", "give me a lesson on X".
"""
import os
import re


def _repo(name=""):
    """Resolve a repo name to its real path under ~/Documents/Code, matched case-insensitively by folder name.
    Blank is this repo, turing. Returns (path, None) or (None, an honest sentence)."""
    name = (name or "").strip().strip("'\"")
    CODE_DIR = os.path.realpath(os.path.expanduser("~/Documents/Code"))
    _THIS_REPO = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if not name:
        return _THIS_REPO, None
    try:
        entries = os.listdir(CODE_DIR)
    except OSError:
        entries = []
    match = next((e for e in entries if e.lower() == name.lower()), None) or \
        next((e for e in entries if name.lower() in e.lower()), None)
    if not match:
        return None, f"No repo called {name!r} under ~/Documents/Code."
    path = os.path.realpath(os.path.join(CODE_DIR, match))
    rel = os.path.relpath(path, CODE_DIR)
    if rel.startswith("..") or os.sep in rel or not os.path.isdir(os.path.join(path, ".git")):
        return None, f"{match} is not a git repo under ~/Documents/Code I can work with."
    return path, None


def explain_codebase(project):
    """Explain a codebase by reading its README, CLAUDE.md and file listing. Read only, local files only."""
    project = (project or "").strip()
    path, err = _repo(project)
    if err:
        return err

    parts = []

    # Read README.md
    readme_path = os.path.join(path, "README.md")
    readme_text = ""
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, "r") as f:
                readme_text = f.read()[:3000]  # cap at 3000 chars
        except (OSError, UnicodeDecodeError):
            pass

    # Read CLAUDE.md
    claude_path = os.path.join(path, "CLAUDE.md")
    claude_text = ""
    if os.path.isfile(claude_path):
        try:
            with open(claude_path, "r") as f:
                claude_text = f.read()[:3000]  # cap at 3000 chars
        except (OSError, UnicodeDecodeError):
            pass

    # Get folder listing (skip dot entries)
    folder_list = []
    try:
        entries = sorted(os.listdir(path))
        folder_list = [e for e in entries if not e.startswith(".") and os.path.isdir(os.path.join(path, e))][:15]
    except OSError:
        pass

    if not readme_text and not claude_text and not folder_list:
        return f"Could not read the structure of {os.path.basename(path)}."

    # Build the context to send to the model
    context = ""
    if readme_text:
        context += f"README.md:\n{readme_text}\n\n"
    if claude_text:
        context += f"CLAUDE.md:\n{claude_text}\n\n"
    if folder_list:
        context += f"Main folders: {', '.join(folder_list)}\n\n"

    # Total length cap before handing to model
    if len(context) > 5000:
        context = context[:5000]

    # Hand to local model with a prompt
    import tools_llm
    prompt = f"Explain this codebase in plain words, a few sentences: what it does, how it is organized, and what the key files are.\n\n{context}"
    reply = tools_llm.ask_llm(prompt)

    # Check if it's a successful reply (contains the marker that ask_llm adds)
    if not reply or "\n(Answered by" not in reply:
        # Model unavailable or failed; give a fallback
        if readme_text:
            return f"**{os.path.basename(path)}**\n\n{readme_text[:400]}...\n\nRun `ask llm explain this codebase` to get a full explanation."
        return f"I could not explain {os.path.basename(path)}: the local model is not ready. Start oMLX or Ollama, then ask again."

    # Strip the model attribution line
    reply = reply.rsplit("\n(Answered by", 1)[0].strip()
    return reply


def teach_me(topic):
    """Teach a lesson on a topic from Wikipedia and the library, then ask two quiz questions. Read only."""
    topic = (topic or "").strip().rstrip("?.!")
    if not topic:
        return 'Teach you about what? Say it like "teach me the history of printing".'

    # Gather sources (same as research)
    import tools_research
    found = tools_research.sources(topic)
    if not found:
        return f"I could not find sources on {topic}. The web may be unreachable; try again in a minute."

    # Build the lesson prompt
    import tools_llm
    numbered = "\n\n".join(f"[{i}] {name}\n{text}" for i, (name, text) in enumerate(found, 1))
    prompt = (f"Write a short lesson on {topic} (3-4 sentences) using ONLY the sources below. "
              f"After the lesson, write exactly two multiple-choice quiz questions on it, with 4 options each (a, b, c, d) "
              f"and put the correct answer in brackets like [b].\n\n{numbered}")

    reply = tools_llm.ask_llm(prompt)

    if not reply or "\n(Answered by" not in reply:
        # Model unavailable; give a fallback
        if found:
            sample = found[0][1][:300]
            return f"I could not write a lesson (the local model is not ready), but here is a passage:\n\n{sample}...\n\nStart oMLX or Ollama, then ask again."
        return "I could not write a lesson (the local model is not ready). Start oMLX or Ollama, then ask again."

    # Strip the attribution line
    reply = reply.rsplit("\n(Answered by", 1)[0].strip()
    return reply


TOOLS = (explain_codebase, teach_me)

_I = re.I
# (pattern, tool name, what to hand it)
ROUTES = (
    (re.compile(r"^(?:explain|walk me through) (?:the |this )?codebase(?: (?:of|for) (.+?))?(?:\s+to me)?$", _I),
     "explain_codebase", lambda m: m.group(1) or ""),
    (re.compile(r"^explain (?:the |this )?([a-z0-9 _-]+)(?: codebase)?$", _I),
     "explain_codebase", lambda m: m.group(1)),
    (re.compile(r"^(?:teach me|give me a lesson on|teach me about) (.+)$", _I),
     "teach_me", lambda m: m.group(1)),
)
