"""Code a feature in a project: "code dark mode in nimble" reads the project, asks the model for a plan,
then for edits to at most 3 files, shows diffs, and writes only on a yes. Phrase-routed only (NOT_FOR_MODELS);
safeguarded against credential leaks, lockfiles and projects outside ~/Documents/Code.
"""
import difflib
import os
import re
import subprocess

from tools_dev import _repo, _shell

_CRED_PATTERN = re.compile(r"^\.(env|key|pem|p8)$|^(secret|password|api_?key|token)", re.I)
_LOCK_PATTERN = re.compile(r"^(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|uv\.lock|Gemfile\.lock|go\.sum|Package\.resolved)$", re.I)

PROMPT_PLAN = ("Plan this change to the project: {request}\n\nKey context:\n{context}\n\nWrite a concise 2-3 "
               "sentence plan: what files will change and why.")

PROMPT_CODE = ("Code this plan: {plan}\n\nExisting code:\n{context}\n\nReply ONLY with whole-file replacements "
               "in this exact format, nothing else:\n\n--- filename\nfile contents\n---\n\n--- another.py\ncontent\n---")


def _safe_path(proj_path, full):
    """True if full is under proj_path, no dotfile parts, not a cred or lockfile."""
    try:
        proj = os.path.realpath(proj_path)
        real = os.path.realpath(full)
        rel = os.path.relpath(real, proj)
        if rel.startswith("..") or rel.startswith("."):
            return False
        parts = rel.split(os.sep)
        if any(p.startswith(".") for p in parts if p not in (".", "")):
            return False
        base = os.path.basename(real)
        if _CRED_PATTERN.match(base) or _LOCK_PATTERN.match(base):
            return False
        return True
    except (OSError, ValueError):
        return False


def _read_head(path, lines=10):
    """First lines of a file, or empty string."""
    try:
        with open(path, "r", errors="replace") as f:
            return "\n".join(f.read(1000).split("\n")[:lines])
    except (OSError, UnicodeDecodeError):
        return ""


def _gather_context(proj_path, request):
    """README, status, file list (capped)."""
    parts = []

    readme_path = os.path.join(proj_path, "README.md")
    if os.path.isfile(readme_path):
        head = _read_head(readme_path, lines=8)
        if head:
            parts.append(f"README:\n{head}")

    status = _shell(["git", "status", "-sb"], proj_path, timeout=5)
    if status:
        parts.append(f"Status:\n{status[:300]}")

    try:
        entries = [e for e in sorted(os.listdir(proj_path)) if not e.startswith(".") and os.path.isfile(os.path.join(proj_path, e))]
        if entries:
            parts.append(f"Files: {', '.join(entries[:15])}")
    except OSError:
        pass

    return "\n\n".join(parts)[:2000]


def _extract_blocks(text):
    """Extract (filename, content) from "--- name\ncontent\n---" blocks."""
    edits = []
    pattern = re.compile(r"^---\s*([^\n]+)\n(.*?)\n^---", re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(text):
        edits.append((m.group(1).strip(), m.group(2).rstrip()))
    return edits


def _plan(proj_path, request):
    """Ask the model for a plan. Returns plan text or None."""
    try:
        import tools_llm
    except ImportError:
        return None

    context = _gather_context(proj_path, request)
    prompt = PROMPT_PLAN.format(request=request, context=context)
    reply = tools_llm.ask_llm(prompt)

    if not reply or "\n(Answered by" not in reply:
        return None

    plan = reply.rsplit("\n(Answered by", 1)[0].strip()
    if plan.startswith(("I could not", "The local model")):
        return None
    return plan


def _edits(proj_path, request, plan):
    """Ask the model for edits. Returns (raw_reply, [(filename, content), ...]) or (None, [])."""
    try:
        import tools_llm
    except ImportError:
        return None, []

    context_parts = []
    try:
        for entry in sorted(os.listdir(proj_path))[:10]:
            full = os.path.join(proj_path, entry)
            if os.path.isfile(full) and _safe_path(proj_path, full) and not entry.startswith("."):
                head = _read_head(full, lines=5)
                if head:
                    context_parts.append(f"{entry}:\n{head}")
    except OSError:
        pass

    context = "\n\n".join(context_parts)[:1500]
    prompt = PROMPT_CODE.format(plan=plan, context=context or "(no files shown)")
    reply = tools_llm.ask_llm(prompt)

    if not reply or "\n(Answered by" not in reply:
        return None, []

    text = reply.rsplit("\n(Answered by", 1)[0].strip()
    if text.startswith(("I could not", "The local model")):
        return None, []

    return text, _extract_blocks(text)


def route(query, log=None, confirm=None):
    """Router for "code X in Y" / "add X to Y". Phrase-routed only: shows plan and diffs, asks once."""
    m = re.match(r"^(?:code|add) (?P<what>.+) (?:in|to) (?P<proj>\S+)$", query, re.I)
    if not m:
        return None

    what, proj = m.group("what"), m.group("proj")

    if confirm is not None and not confirm("code", (f"{what} in {proj}",)):  # Law 3: a no runs nothing, so ask before reading anything
        return "Okay, I will not."

    # Resolve project (exact match required)
    path, err = _repo(proj)
    if err:
        return err

    # Step 1: Ask for plan
    plan = _plan(path, what)
    if not plan:
        return "Could not plan: the local model is not ready."

    if log:
        log(f"Plan: {plan}")

    # Step 2: Ask for edits
    reply, edits = _edits(path, what, plan)
    if not reply:
        return "Could not generate edits: the local model is not ready."

    if not edits:
        return "The model did not return any edits in the expected format."

    # Step 3: Validate edits (safety checks)
    if len(edits) > 3:
        return f"Too many files ({len(edits)}); only 3 allowed."

    full_edits = []
    for fname, content in edits:
        full = os.path.realpath(os.path.join(path, fname.lstrip("/")))

        if not _safe_path(path, full):
            return f"Cannot write {fname}: outside project or protected."

        # Refuse dirty files
        status = _shell(["git", "status", "--porcelain", full], path, timeout=5)
        if status.strip() and not status.strip().startswith("??"):
            return f"{fname} has uncommitted changes."

        full_edits.append((fname, full, content))

    # Step 4: Show diffs
    diffs = []
    for fname, full, content in full_edits:
        old = open(full).read() if os.path.exists(full) else ""
        diff = "\n".join(difflib.unified_diff(
            old.splitlines(), content.splitlines(),
            fromfile=fname, tofile=fname, lineterm=""
        ))
        if diff:
            diffs.append(diff)
            if log:
                log(diff)

    if not diffs:
        return "No changes to make."

    # Step 5: Ask for confirmation (gate, same as write_code)
    if os.environ.get("SAMANTHA_HEADLESS") != "1" and confirm is None:
        return f"Plan:\n{plan}\n\nChanges:\n{diffs[0][:200]}...\n\n(Needs confirmation)"

    if not confirm("code", (diffs[0][:100] + "...",)):
        return "Okay, I will not."

    # Step 6: Write the files
    changed = []
    for fname, full, content in full_edits:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        changed.append(full)

    # Step 7: Run tests (optional, best-effort)
    test_ok = True
    test_out = ""
    if os.path.isdir(os.path.join(path, "tests")) or os.path.isfile(os.path.join(path, "package.json")):
        for argv in (["python3", "-m", "pytest", "-q"], ["npm", "test"]):
            try:
                out = _shell(argv, path, timeout=120)
                test_out = out
                test_ok = out.find("fail") < 0 and out.find("FAIL") < 0
                break
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
                pass

    if not test_ok:
        undo = f"Wrote: {', '.join(changed)}\nUndo: git checkout -- " + " ".join(changed)
        return f"Tests failed:\n{test_out}\n\n{undo}"

    return f"Wrote {len(changed)} file(s)." + (f" {test_out}" if test_out else "")


def code(query, log=None, confirm=None):
    """The "code" tool: phrase-routed only ("code X in Y"), so it is registered for the harness's write gate and never picked by a model."""
    return route(query, log=log, confirm=confirm) or 'Say it like "code a retry in turing".'
