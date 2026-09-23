"""Distillation: a frontier teacher writes her training set for the one job her own model does, answering from
retrieved passages. Real passages from the project docs and the fleet go out, the teacher writes a question and
a short grounded answer for each, and every pair is checked here before she trains on it: short, plain, no em
dashes, and every content word of the answer found in its passage. Pairs are wrapped in exactly the prompt chat.py
builds at inference (chat.build_prompt, three passages), and questions paired with passages that do not hold their
answer teach her to say "My notes don't cover that." instead of guessing. A tenth of the passages never reach
training: `eval` scores her on them, before and after.

    python3 distill.py passages 400     # grow data/distill/passages.jsonl to 400, append-only, for the teacher
    (the teacher writes data/distill/qa.jsonl: {"id", "q", "a"} per line, two per passage)
    python3 distill.py build            # data/distill/{train,valid,heldout}.jsonl
    python3 distill.py eval 60          # her answers on held-out prompts: answered right, declined right
"""
import glob
import json
import os
import random
import re
import sys

import prep_data

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "distill")
DECLINE = "My notes don't cover that."
PASSAGE = 800  # characters, what chat.py hands the model per retrieved passage
PER_REPO = 25  # so one busy repo cannot crowd out the rest of the fleet
NAMES = ("README.md", "WHITEPAPER.md")  # prose; CLAUDE.md and roadmap.md are terse notes that taught fragment answers
SECRET = re.compile(r"sk-[A-Za-z0-9]|ghp_|xox[bp]-|AKIA[0-9A-Z]|BEGIN [A-Z ]*KEY|api[_-]?key\s*[:=]|password\s*[:=]|token\s*[:=]", re.I)
STOP = set("a an and are as at be by for from has have how i in is it its of on or that the this to was were what "
           "when where which who why will with you your do does did not no can so if".split())


def _words(text):
    """Content words, lowercased."""
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def _passage(text):
    """Up to PASSAGE characters of a chunk, cut at the last sentence or line break so it reads whole."""
    text = text.strip()[:PASSAGE]
    cut = max(text.rfind(". "), text.rfind("\n"))
    return text[:cut + 1].strip() if cut > PASSAGE // 2 else text


def _readable(text):
    """Prose, not code, tables or secrets: mostly letters and spaces, and nothing that looks like a key."""
    letters = sum(c.isalpha() or c.isspace() for c in text)
    return len(text) >= 300 and letters / len(text) > 0.85 and not SECRET.search(text)


def passages(n, seed=0):
    """n readable passages from the project's own docs and the fleet's READMEs, whitepapers and CLAUDE.md files."""
    code = prep_data.CODE
    paths = glob.glob(f"{HERE}/*.md") + glob.glob(f"{HERE}/docs/*.md")
    for name in NAMES:
        paths += glob.glob(f"{code}/*/{name}")
    paths += glob.glob(f"{code}/*/docs/*.md")  # architecture notes and whitepapers: prose
    # a git worktree (its .git is a file, not a folder) is a copy of a repo already here: four Joshua Tree
    # worktrees once made up 229 of 400 passages
    worktree = lambda p: os.path.isfile(os.path.join(code, os.path.relpath(p, code).split(os.sep)[0], ".git"))
    paths = sorted(p for p in set(paths) if "/_external/" not in p and not p.endswith("TRAINING_EXAMPLES.md") and not worktree(p))
    found = []
    for path in paths:
        for ex in prep_data.read_chunks(path, os.path.basename(os.path.dirname(path))):
            text = _passage(ex["messages"][1]["content"])
            if _readable(text):
                found.append({"source": os.path.relpath(path, code), "text": text})
    random.Random(seed).shuffle(found)
    seen, per_repo, keep = set(), {}, []
    for p in found:  # one passage per 80-character opening, so near-duplicate docs count once, and at most PER_REPO a repo
        key, repo = p["text"][:80], p["source"].split(os.sep)[0]
        if key not in seen and per_repo.get(repo, 0) < PER_REPO:
            seen.add(key)
            per_repo[repo] = per_repo.get(repo, 0) + 1
            keep.append({"id": len(keep), **p})
        if len(keep) == n:
            break
    return keep


def check(q, a, passage):
    """Why a teacher pair is unfit to train on, or None when it is fit."""
    if not q.strip() or not a.strip():
        return "empty"
    if len(a) > 300 or a.count(". ") > 2:
        return "too long"
    if "\u2014" in a or "\u2014" in q or re.search(r"[\U0001F300-\U0001FAFF]", a):
        return "em dash or emoji"
    if re.search(r"\b(?:the )?(?:passage|context|text|document)s? (?:says|states|mentions|does)", a, re.I):
        return "talks about the passage"
    # the first teacher copied note fragments ("No deadline pinned - iOS/Mac companion app...") and asked
    # "How does Bookrank use this?": a real question names its subject, a real answer is a whole sentence
    if re.search(r"\b(?:this|that|these|those|it)\s*\?$", q.strip(), re.I) or not q.strip().endswith("?"):
        return "vague question"
    if not re.match(r"[A-Z0-9]", a.strip()) or not a.strip().endswith((".", "!")) or re.search(r" - |;|\s/\s|\|", a):
        return "not a sentence"
    missing = _words(a) - _words(passage) - _words(q)
    if len(missing) > max(1, len(_words(a)) // 5):
        return "not grounded: " + " ".join(sorted(missing)[:5])
    return None


def _prompt(question, texts):
    """The exact prompt chat.py builds for a fresh question and these retrieved passages."""
    import chat
    return chat.build_prompt([], "\n\n---\n\n".join(texts), question)


def _split(ids):
    """Which passages are held out, fixed for good in split.json: once held out, always held out, and once trained on,
    never held out, so adding passages never slides the eval onto questions she has already learned. A new passage
    is held out when its id is a multiple of 10."""
    path = os.path.join(OUT, "split.json")
    split = json.load(open(path)) if os.path.exists(path) else {"held": [], "trained": []}
    known = set(split["held"]) | set(split["trained"])
    for i in ids:
        if i not in known:
            split["held" if i % 10 == 0 else "trained"].append(i)
    with open(path, "w") as f:
        json.dump(split, f)
    return set(split["held"])


def build(seed=0, negatives=3):
    """Checked pairs into chat-format train, valid and held-out sets. One in `negatives` questions is also asked
    over three passages that do not hold its answer, with the decline as the target. Returns (kept, rejected)."""
    rnd = random.Random(seed)
    ps = {p["id"]: p for p in map(json.loads, open(os.path.join(OUT, "passages.jsonl")))}
    ids = sorted(ps)
    held = _split(ids)
    sets = {"train": [], "heldout": []}
    kept, rejected = 0, {}
    for line in open(os.path.join(OUT, "qa.jsonl")):
        try:
            qa = json.loads(line)
            p = ps[int(qa["id"])]
        except (ValueError, KeyError):
            rejected["unreadable"] = rejected.get("unreadable", 0) + 1
            continue
        why = check(qa["q"], qa["a"], p["text"])
        if why:
            rejected[why.split(":")[0]] = rejected.get(why.split(":")[0], 0) + 1
            continue
        kept += 1
        # a held-out passage never appears in a training prompt, even as a distractor, or its answer leaks into training
        pool = [i for i in ids if (p["id"] in held or i not in held) and ps[i]["source"] != p["source"]]
        others = [ps[i]["text"] for i in rnd.sample(pool, 3)]
        texts = [p["text"]] + others[:2]
        rnd.shuffle(texts)
        name = "heldout" if p["id"] in held else "train"
        sets[name].append({"messages": [{"role": "user", "content": _prompt(qa["q"], texts)},
                                        {"role": "assistant", "content": qa["a"].strip()}], "answerable": True})
        if rnd.randrange(negatives) == 0:
            sets[name].append({"messages": [{"role": "user", "content": _prompt(qa["q"], others)},
                                            {"role": "assistant", "content": DECLINE}], "answerable": False})
    rnd.shuffle(sets["train"])
    for name, rows in (("train", sets["train"]), ("valid", sets["heldout"][:40]), ("heldout", sets["heldout"])):
        with open(os.path.join(OUT, name + ".jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r if name == "heldout" else {"messages": r["messages"]}) + "\n")
    return kept, rejected


def score(answer, teacher, answerable):
    """Whether her answer passes: a held-out answerable prompt needs half the teacher's content words and no
    decline; an unanswerable one needs the decline."""
    declined = "don't cover" in answer.lower() or "do not cover" in answer.lower()
    if not answerable:
        return declined
    want = _words(teacher)
    return not declined and bool(want) and len(want & _words(answer)) / len(want) >= 0.5


def evaluate(n=60, log=print):
    """Her own model on n held-out prompts: (answered right of answerable, declined right of unanswerable)."""
    import chat
    rows = [json.loads(l) for l in open(os.path.join(OUT, "heldout.jsonl"))][:n]
    right = {True: [0, 0], False: [0, 0]}
    for r in rows:
        got = chat.clean(chat.generate(r["messages"][0]["content"], max_tokens=80), "")
        ok = score(got, r["messages"][1]["content"], r["answerable"])
        right[r["answerable"]][0] += ok
        right[r["answerable"]][1] += 1
    log(f"answered right {right[True][0]}/{right[True][1]}, declined right {right[False][0]}/{right[False][1]}")
    return right


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "passages":
        # append-only: docs change under us, so passages already handed out keep their ids and text for good
        path = os.path.join(OUT, "passages.jsonl")
        have = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
        seen = {p["text"][:80] for p in have}
        fresh = [p for p in passages(10 ** 6) if p["text"][:80] not in seen][:max(0, int(sys.argv[2]) - len(have)) if len(sys.argv) > 2 else None]
        with open(path, "a") as f:
            for i, p in enumerate(fresh):
                f.write(json.dumps({**p, "id": len(have) + i}) + "\n")
        print(f"{len(have)} kept, {len(fresh)} added -> {path}")
    elif cmd == "build":
        kept, rejected = build()
        print(f"kept {kept} pairs, rejected {sum(rejected.values())}: {rejected}")
    elif cmd == "eval":
        evaluate(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    else:
        print(__doc__)
