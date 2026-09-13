"""Regression check for chat.py's pure logic (no model calls, no interactive
loop): clean() stripping echoed scaffold, build_prompt() history handling.
This is the one thing that was never automated, only manually eyeballed
once when the indentation bug got fixed (see roadmap.md).

Usage: ./.venv/bin/python test_chat.py
"""
from chat import clean, build_prompt, HISTORY_TURNS


def test_clean_strips_echoed_user_turn():
    assert clean("The license is MIT.\nUser: what else", "q") == "The license is MIT."


def test_clean_strips_echoed_samantha_turn():
    assert clean("Answer here.\nSamantha: repeat", "q") == "Answer here."


def test_clean_leaves_clean_answer_alone():
    assert clean("Just a plain answer.", "q") == "Just a plain answer."


def test_build_prompt_includes_history():
    history = [("What is Turing?", "The project.")]
    prompt = build_prompt(history, "ctx", "What's its first model called?")
    assert "What is Turing?" in prompt
    assert "The project." in prompt
    assert "What's its first model called?" in prompt


def test_build_prompt_caps_to_history_turns():
    history = [(f"q{i}", f"a{i}") for i in range(HISTORY_TURNS + 5)]
    prompt = build_prompt(history, "ctx", "new question")
    assert "q0" not in prompt
    assert f"q{len(history) - 1}" in prompt


def test_build_prompt_no_history_omits_section():
    prompt = build_prompt([], "ctx", "first question")
    assert "Recent conversation:" not in prompt


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
