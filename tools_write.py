"""Write real files: "draft an email about X" or "write a doc about the release" has the biggest local model
draft plain content, then saves it as a markdown file in the home folder, asking first. One tool, one confirmation,
same shape as new_note and new_reminder. Nothing leaves the Mac except the local-model call itself (which already
stays local, see tools_llm).
"""
from tools_research import _slug, _write_target  # her own safe-write helpers, shared so there is one home-folder rule

PROMPT = ("Write plain content for this request: {request}\n\nA few short paragraphs, plain words, no headers, "
          "no markdown formatting, no em dashes. Just the content itself, nothing about writing it.")


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
    import os
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(draft + "\n")
    return f"Wrote {full}."
