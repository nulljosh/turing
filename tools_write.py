"""Write real files: "draft an email about X" or "write a doc about the release" has the biggest local model
draft plain content, then saves it as a markdown file in the home folder, asking first. One tool, one confirmation,
same shape as new_note and new_reminder. Nothing leaves the Mac except the local-model call itself (which already
stays local, see tools_llm).

edit_last_draft remembers the path write_document just saved and rewrites it on request ("make it shorter",
"friendlier", "add a line about Friday"): the same local model edits the text, a unified diff shows exactly what
would change, and it only lands on a yes through the same confirm every writing tool waits on.

edit_file does the same to any text file inside the home folder ("edit notes.md: make it shorter"), and write_code
writes new code to disk ("write a python script that prints the date to today.py"): the model writes only the code,
the whole file is shown as a diff, and nothing lands without a yes. route() is the phrase router for all three,
kept here so tools.py stays small.
"""
import difflib
import os
import re

from tools_research import _slug, _write_target  # her own safe-write helpers, shared so there is one home-folder rule

PROMPT = ("Write plain content for this request: {request}\n\nA few short paragraphs, plain words, no headers, "
          "no markdown formatting, no em dashes. Just the content itself, nothing about writing it.")

EDIT_PROMPT = ("Rewrite the text below to do this: {instruction}\n\nKeep everything else about it the same. Plain "
               "words, no headers, no markdown formatting, no em dashes, and no notes about the rewrite itself, "
               "just the rewritten text.\n\n---\n{text}")

CODE_PROMPT = ("Write {lang} code that does this: {request}\n\nOnly the code, complete and runnable, short comments "
               "where they help, no explanation before or after it.")

_last_draft = {"path": None}  # the file write_document most recently saved, so "make it shorter" knows what "it" is


def write_document(request):
    """Draft plain content for a request ("an email to the team about the release", "a doc about X") with the
    biggest local model, and save it as a markdown file in the home folder. Asks first, like new_note."""
    request = request.strip()
    if not request:
        return 'Write what? Say it like "draft an email about the v3.1 release".'
    import tools_llm
    draft = tools_llm.ask_llm(PROMPT.format(request=request))
    draft = draft.rsplit("\n(Answered by", 1)[0].strip()
    if not draft or draft.startswith(("I could not", "The local model")):
        return f"I could not draft that: {draft or 'the local model sent back nothing'}."
    full = _write_target(f"~/Desktop/{_slug(request)}.md")
    if not full:
        return "I can only save inside your home folder."
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(draft + "\n")
    _last_draft["path"] = full
    return f"Wrote {full}."


def _land(path, new_text, name, log=None, confirm=None):
    """Show a unified diff from what is on disk (nothing, for a new file) to new_text, then write it only on a yes
    through confirm(name, args) -> bool, the one gate every writing tool waits on."""
    old = open(path).read() if os.path.exists(path) else ""
    diff = "\n".join(difflib.unified_diff(old.splitlines(), new_text.splitlines(), fromfile=path, tofile=path, lineterm=""))
    if not diff:
        return "That came back the same, nothing to change."
    if log:
        log(diff)
    if confirm and not confirm(name, (diff,)):
        return "Okay, I will not."
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(new_text)
    return f"{'Rewrote' if old else 'Wrote'} {path}."


def _rewrite(path, instruction, name, log=None, confirm=None):
    """Have the biggest local model rewrite the text at path to follow instruction, then _land it."""
    import tools_llm
    new = tools_llm.ask_llm(EDIT_PROMPT.format(instruction=instruction, text=open(path).read()))
    new = new.rsplit("\n(Answered by", 1)[0].strip()
    if not new or new.startswith(("I could not", "The local model")):
        return f"I could not rewrite that: {new or 'the local model sent back nothing'}."
    return _land(path, new + "\n", name, log, confirm)


def edit_last_draft(instruction, log=None, confirm=None):
    """Rewrite the file write_document last saved ("make it shorter", "friendlier", "add a line about Friday"): the
    biggest local model edits the text, a unified diff of the change is shown, and it writes only on a yes through
    confirm(name, args) -> bool, the same gate every writing tool waits on. Says plainly when there is no draft yet."""
    instruction = instruction.strip()
    path = _last_draft["path"]
    if not path or not os.path.exists(path):
        return "There is no draft yet: write one first, with something like \"draft an email about the release\"."
    if not instruction:
        return 'Edit it how? Say it like "make it shorter" or "add a line about Friday".'
    return _rewrite(path, instruction, "edit_last_draft", log, confirm)


def _find(path):
    """A file named in chat, resolved inside the home folder: as given, else on the Desktop, else at home. None if
    it is outside home or hidden."""
    for guess in (path, f"~/Desktop/{path}", f"~/{path}"):
        full = _write_target(guess)
        if full and os.path.exists(full):
            return full
    return _write_target(path if path.startswith(("~", "/")) else f"~/Desktop/{path}")


def edit_file(path, instruction, log=None, confirm=None):
    """Rewrite any text file inside the home folder to follow an instruction ("edit notes.md: make it shorter"):
    the biggest local model edits it, the diff is shown, and it lands only on a yes. Never touches a file outside
    home, a hidden one, or one that is not text."""
    full = _find(path.strip())
    if not full or not os.path.isfile(full):
        return f"I can't find {path} inside your home folder."
    try:
        open(full).read()
    except (UnicodeDecodeError, OSError):
        return f"{path} is not a text file I can edit."
    if not instruction.strip():
        return 'Edit it how? Say it like "edit notes.md: make it shorter".'
    return _rewrite(full, instruction.strip(), "edit_file", log, confirm)


def write_code(request, path, log=None, confirm=None):
    """Write new code to a file inside the home folder ("write a python script that prints the date to today.py"):
    the biggest local model writes only the code, the whole file is shown as a diff (against what is there, if
    anything), and it lands only on a yes."""
    full = _find(path.strip())
    if not full:
        return "I can only write inside your home folder."
    if not request.strip():
        return 'Write what? Say it like "write a python script that prints the date to today.py".'
    lang = {"py": "Python", "sh": "shell", "js": "JavaScript", "swift": "Swift", "html": "HTML", "css": "CSS",
            "rb": "Ruby", "go": "Go", "rs": "Rust", "c": "C"}.get(full.rsplit(".", 1)[-1].lower(), "")
    import tools_llm
    from tools_code import _extract_code
    code = _extract_code(tools_llm.ask_llm(CODE_PROMPT.format(lang=lang, request=request.strip())))
    if not code or code.startswith(("I could not", "The local model")):
        return f"I could not write that: {code or 'the local model sent back nothing'}."
    return _land(full, code + "\n", "write_code", log, confirm)


# Phrase routes, checked by tools.do ahead of the multi-step agent. Each confirms itself with a diff, so none is
# ever a model's own pick. "make it shorter" is the last draft; a name with an extension is any file.
_FILE = r"(?P<path>[~/\w.-]+\.[A-Za-z0-9]+)"
_EDIT_DRAFT = re.compile(
    r"^make (?:it|that|the draft)(?: a bit| a little)? (.+)$"
    r"|^add (?:a |another )?line(?: to (?:it|that|the draft))?(?: that says| saying| about)? (.+)$"
    r"|^(?:edit|rewrite|revise|shorten|tighten) (?:the |my |that )?(?:last )?draft(?: to)?\s*(.*)$", re.I)
_EDIT_FILE = re.compile(r"^(?:edit|rewrite|revise|change|update) (?:the file )?" + _FILE + r"(?: to|:|,)? (?P<instr>.+)$"
                        r"|^in " + _FILE.replace("path", "path2") + r",? (?P<instr2>.+)$", re.I)
_WRITE_CODE = re.compile(r"^write (?:me )?(?:a |some )?(?P<what>(?:\w+ )?(?:script|code|program|function|module|class)\b.*?) (?:to|as|into|in|at) " + _FILE + r"$"
                         r"|^write " + _FILE.replace("path", "path2") + r"(?: that| to|:)? (?P<what2>.+)$", re.I)


def route(query, log=None, confirm=None):
    """The phrase router for edit_last_draft, edit_file and write_code: the reply, or None when query is not one."""
    m = _EDIT_DRAFT.match(query)
    if m:
        instruction = next((g for g in m.groups() if g), "").strip()
        if log:
            log(f"  [edit_last_draft({instruction!r})]")
        return edit_last_draft(instruction, log=log, confirm=confirm)
    m = _EDIT_FILE.match(query)
    if m:
        path, instr = m.group("path") or m.group("path2"), m.group("instr") or m.group("instr2")
        if log:
            log(f"  [edit_file({path!r}, {instr!r})]")
        return edit_file(path, instr, log=log, confirm=confirm)
    m = _WRITE_CODE.match(query)
    if m:
        path, what = m.group("path") or m.group("path2"), m.group("what") or m.group("what2")
        if log:
            log(f"  [write_code({what!r}, {path!r})]")
        return write_code(what, path, log=log, confirm=confirm)
    return None
