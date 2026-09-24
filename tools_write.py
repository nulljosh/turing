"""Write real files: "draft an email about X" or "write a doc about the release" has the biggest local model
draft plain content, then saves it as a markdown file in the home folder, asking first. One tool, one confirmation,
same shape as new_note and new_reminder. Nothing leaves the Mac except the local-model call itself (which already
stays local, see tools_llm).

edit_last_draft remembers the path write_document just saved and rewrites it on request ("make it shorter",
"friendlier", "add a line about Friday"): the same local model edits the text, a unified diff shows exactly what
would change, and it only lands on a yes through the same confirm every writing tool waits on.
"""
import difflib
import os

from tools_research import _slug, _write_target  # her own safe-write helpers, shared so there is one home-folder rule

PROMPT = ("Write plain content for this request: {request}\n\nA few short paragraphs, plain words, no headers, "
          "no markdown formatting, no em dashes. Just the content itself, nothing about writing it.")

EDIT_PROMPT = ("Rewrite the text below to do this: {instruction}\n\nKeep everything else about it the same. Plain "
               "words, no headers, no markdown formatting, no em dashes, and no notes about the rewrite itself, "
               "just the rewritten text.\n\n---\n{text}")

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
    old = open(path).read()
    import tools_llm
    new = tools_llm.ask_llm(EDIT_PROMPT.format(instruction=instruction, text=old))
    new = new.rsplit("\n(Answered by", 1)[0].strip()
    if not new or new.startswith(("I could not", "The local model")):
        return f"I could not rewrite that: {new or 'the local model sent back nothing'}."
    new_text = new + "\n"
    diff = "\n".join(difflib.unified_diff(old.splitlines(), new_text.splitlines(), fromfile=path, tofile=path, lineterm=""))
    if not diff:
        return "That rewrite came back the same, nothing to change."
    if log:
        log(diff)
    if confirm and not confirm("edit_last_draft", (diff,)):
        return "Okay, I will not."
    with open(path, "w") as f:
        f.write(new_text)
    return f"Rewrote {path}."
