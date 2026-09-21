"""Score a from-scratch picker exactly like eval/hands.py scores an LLM one.
Run: SAMANTHA_HEADLESS=1 ../.venv/bin/python eval.py --name exp1 [--verbose]
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["SAMANTHA_HEADLESS"] = "1"
from train import *  # noqa (sets sys.path)
sys.path.insert(0, os.path.join(REPO, "eval"))
import hands  # the real eval: cases() and its imports
import tools


class Loaded:
    def __init__(self, name):
        d = os.path.join(HERE, name)
        self.meta = json.load(open(os.path.join(d, "meta.json")))
        m = self.meta
        self.vocab, self.tools, self.ac = m["vocab"], m["tools"], m["argclasses"]
        self.allowed = m["allowed"]
        self.model = Picker(len(self.vocab) + 2, len(self.tools), len(self.ac), m["dim"], m["layers"], 4)
        self.model.load_weights(os.path.join(d, "weights.npz"))
        self.size = os.path.getsize(os.path.join(d, "weights.npz"))

    def pick(self, text):
        ids = mx.array([encode(text, self.vocab)])
        n = ids.shape[1]
        lt, la, sp = self.model(ids, ids > 0)
        lt, la, sp = np.array(lt[0]), np.array(la[0]), np.array(sp[0])
        tool = self.tools[int(lt.argmax())]
        if tool == "null":
            return {"tool": None, "arg": ""}
        ok = self.allowed.get(tool, {0})
        cls = max(ok, key=lambda c: la[c])
        arg = ""
        if cls >= 2:
            arg = self.ac[cls][1:]
        elif cls == 1:
            s, e = sp[1:, 0], sp[1:, 1]
            best, bs, be = -1e18, 0, 0
            for i in range(n - 1):
                for j in range(i, min(n - 1, i + 60)):
                    if s[i] + e[j] > best:
                        best, bs, be = s[i] + e[j], i, j
            arg = text[bs:be + 1].strip()
        return {"tool": tool, "arg": arg}


def main():
    name = flag("--name")
    P = Loaded(name)
    verbose = "--verbose" in sys.argv
    score, wrong_tool, fired, blocked, lat, misses = {}, 0, 0, 0, [], []
    for group, text, tool, arg, exact in hands.cases():
        t0 = time.time()
        got = P.pick(text)
        lat.append(time.time() - t0)
        # from here on: the same rule as eval/hands.py
        got_arg = str(got.get("arg") or "").lower().strip()
        if tool == "timer" and got.get("tool") == "timer":
            got_arg, arg = str(tools.duration(got_arg)), str(tools.duration(arg))
        ok = got.get("tool", "?") == tool and (got_arg == (arg or "").lower() if exact else (arg or "").lower() in got_arg)
        n = score.setdefault(group, [0, 0])
        n[0] += ok
        n[1] += 1
        if ok and tool and tool != "agent" and not tools._sound(tool, str(got.get("arg") or "").strip(), text):
            blocked += 1
        if not ok:
            wrong_tool += bool(got.get("tool")) and got.get("tool") != tool
            fired += bool(got.get("tool")) and got.get("tool") not in (tool, "agent") and tools._sound(got["tool"], str(got.get("arg") or "").strip(), text)
            misses.append((group, text, tool, arg, got))
            if verbose:
                print(f"  MISS [{group}] {text!r}: want {tool}({arg!r}) got {got}")
    total = sum(n[0] for n in score.values())
    for g, (p, n) in score.items():
        print(f"{g}: {p}/{n}")
    print(f"{total}/{sum(n[1] for n in score.values())} passed, {wrong_tool} picked the wrong tool, {fired} of those get past the guard in tools.do(), {blocked} right picks refused by the guard")
    m = P.meta
    print(f"params {m['params']}, file {P.size / 1e6:.2f} MB, train {m['train_minutes']:.1f} min, {1000 * sum(lat) / len(lat):.1f} ms/query, {name}")
    json.dump(misses, open(os.path.join(HERE, name, "misses.json"), "w"), indent=0, default=str)


if __name__ == "__main__":
    main()
