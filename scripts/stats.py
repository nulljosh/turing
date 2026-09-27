#!/usr/bin/env python3
"""Generate web/stats.json with docstring coverage, house docs status, and measured benchmarks.

Run: python3 scripts/stats.py
"""
import ast
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

# Fixed measured results from eval runs (tools and actions re-measured 2026-09-21, the rest 2026-09-20). Update these when re-running evals.
MEASURED = {
    "tools": {"before": 0, "after": 30},
    "actions_eval": "77/77",
    "knowledge_sweep": {"before": "47/65", "after": "62/65"},  # eval/basic_questions.py 2026-09-21
    "confidently_wrong": {"before": 18, "after": 0},
    "picker_unseen_percent": {"before": 6, "after": 75},  # regex router 30/463, her own picker 692/834, eval/hands.py
    "project_eval": "29/29",
    "chat_tests": "18/18",
    "faq_paraphrase": "13/16",
    "multistep_latency_seconds": {"before": "minutes (8B)", "after": 5.3},
    "hands_model_memory_gb": {"before": 7.6, "after": 3.5},
    "base_model": "Qwen2.5-0.5B-Instruct 4-bit, LoRA",
    "hands_model": "qwen3:1.7b via Ollama"
}

def count_docstrings(file_path):
    """Count functions, classes, and nested methods in a Python file, and how many have docstrings."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except Exception:
        return 0, 0

    total = 0
    documented = 0

    def visit(node):
        """Recursively count and check docstrings in AST nodes."""
        nonlocal total, documented
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            total += 1
            if ast.get_docstring(node) is not None:
                documented += 1
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return total, documented

def collect_coverage():
    """Collect docstring coverage for application, scripts, training, and test files."""
    repo_root = Path(".")
    files_coverage = {}
    total_items = 0
    total_documented = 0

    for folder in ("app", "scripts", "pixelmator", "eval", "tests", "training"):
        for py_file in sorted((repo_root / folder).glob("*.py")):
            total, documented = count_docstrings(py_file)
            if total > 0:
                files_coverage[str(py_file)] = {"total": total, "documented": documented}
                total_items += total
                total_documented += documented

    coverage_percent = (total_documented * 100 // total_items) if total_items > 0 else 0
    assert 0 <= coverage_percent <= 100, f"Coverage percent out of range: {coverage_percent}"

    return files_coverage, coverage_percent

def check_house_docs():
    """Check which house docs exist."""
    docs = {
        "README.md": Path("README.md").exists(),
        "WHITEPAPER.md": Path("WHITEPAPER.md").exists(),
        "FAQ.md": Path("docs/FAQ.md").exists(),
        "TROUBLESHOOTING.md": Path("training/TROUBLESHOOTING.md").exists(),
        "CLAUDE.md": Path("CLAUDE.md").exists(),
        "roadmap.md": Path("roadmap.md").exists(),
        "LICENSE": Path("LICENSE").exists(),
        "SECURITY.md": Path("SECURITY.md").exists(),
        "architecture.svg": Path("architecture.svg").exists(),
        "icon.svg": Path("icon.svg").exists()
    }
    return docs

def read_version():
    """Read VERSION file."""
    try:
        return Path("VERSION").read_text().strip()
    except Exception:
        return "unknown"

def check():
    """The docs rule: every function and class has a docstring. Exit 1 and name the gaps when one does not."""
    files, percent = collect_coverage()
    gaps = {f: c["total"] - c["documented"] for f, c in files.items() if c["documented"] < c["total"]}
    for f, n in sorted(gaps.items()):
        print(f"undocumented in {f}: {n}")
    print(f"docs coverage {percent}%")
    sys.exit(1 if gaps else 0)


def main():
    """Gather coverage data and write stats to web/stats.json."""
    if "--check" in sys.argv:
        check()
    os.environ.setdefault("SAMANTHA_HEADLESS", "1")
    import tools  # the tools tile counts what she really has, not a number typed here
    MEASURED["tools"]["after"] = len(tools.TOOLS)
    files_coverage, coverage_percent = collect_coverage()
    house_docs = check_house_docs()
    version = read_version()

    stats = {
        "version": version,
        "docs_coverage": {
            "percent": coverage_percent,
            "files": files_coverage,
            "house_docs": house_docs
        },
        "measured": MEASURED
    }

    output_path = Path("web/stats.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2))
    print(f"Wrote {output_path}")
    print(f"Docs coverage: {coverage_percent}%")
    print(f"Version: {version}")

if __name__ == "__main__":
    main()
