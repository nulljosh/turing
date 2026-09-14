"""Regression check for chat.py's pure logic (no model calls, no interactive
loop): clean() stripping echoed scaffold, build_prompt() history handling.
This is the one thing that was never automated, only manually eyeballed
once when the indentation bug got fixed (see roadmap.md).

Usage: ./.venv/bin/python test_chat.py
"""
from chat import clean, build_prompt, HISTORY_TURNS, project_scope


def test_clean_strips_echoed_user_turn():
    assert clean("The license is MIT.\nUser: what else", "q") == "The license is MIT."


def test_clean_strips_echoed_samantha_turn():
    assert clean("Answer here.\nSamantha: repeat", "q") == "Answer here."


def test_clean_leaves_clean_answer_alone():
    assert clean("Just a plain answer.", "q") == "Just a plain answer."


def test_clean_strips_echo_at_position_zero():
    # real bug: "idx > 0" skipped a marker found at index 0, leaking the
    # raw scaffold straight through as the "answer" when the model's
    # output starts immediately with the echo, no leading newline
    assert clean("User: what else?\nSamantha: x", "q") == ""
    assert clean("Samantha: repeating my own tag", "q") == ""


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


def test_scope_stays_active_across_keywordless_followup():
    # real bug: "How confident does a match need to be?" right after "What
    # is the FAQ matcher?" has no project keyword AND no pronoun, and got
    # answered with a Wikipedia article about an unrelated comedian. A
    # sticky topic flag catches this where pronoun-matching couldn't.
    scoped, active = project_scope("What is the FAQ matcher?", False)
    assert scoped and active
    scoped, active = project_scope("How confident does a match need to be?", active)
    assert scoped and active


def test_scope_not_active_before_any_project_question():
    scoped, active = project_scope("What is the capital of France?", False)
    assert not scoped and not active


def test_scope_officeholder_overrides_active_topic():
    # a live "who's the current X" lookup is a real, tested escape hatch,
    # a resumed project topic should never swallow it
    scoped, active = project_scope("What is Turing?", False)
    assert scoped and active
    scoped, active = project_scope("who's the prime minister of canada", active)
    assert not scoped and active


def test_scope_direct_keyword_match_without_prior_history():
    scoped, active = project_scope("What is its first model called?", False)
    assert scoped and active


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
