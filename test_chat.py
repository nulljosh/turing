"""Regression check for chat.py's pure logic (no model calls, no interactive
loop): clean() stripping echoed scaffold, build_prompt() history handling.
This is the one thing that was never automated, only manually eyeballed
once when the indentation bug got fixed (see roadmap.md).

Usage: ./.venv/bin/python test_chat.py
"""
from chat import clean, build_prompt, HISTORY_TURNS, project_scope, answer_turn, resolve_followup, subject_of


def test_clean_strips_echoed_user_turn():
    """Verify clean() removes user echoes from model output."""
    assert clean("The license is MIT.\nUser: what else", "q") == "The license is MIT."


def test_clean_strips_echoed_samantha_turn():
    """Verify clean() removes Samantha echoes from model output."""
    assert clean("Answer here.\nSamantha: repeat", "q") == "Answer here."


def test_clean_leaves_clean_answer_alone():
    """Verify clean() passes through answer text with no echoes."""
    assert clean("Just a plain answer.", "q") == "Just a plain answer."


def test_clean_strips_echo_at_position_zero():
    """Verify clean() catches echoes at the start of model output, not just after leading text."""
    # real bug: "idx > 0" skipped a marker found at index 0, leaking the
    # raw scaffold straight through as the "answer" when the model's
    # output starts immediately with the echo, no leading newline
    assert clean("User: what else?\nSamantha: x", "q") == ""
    assert clean("Samantha: repeating my own tag", "q") == ""


def test_build_prompt_includes_history():
    """Verify build_prompt() includes conversation history in the generated prompt."""
    history = [("What is Turing?", "The project.")]
    prompt = build_prompt(history, "ctx", "What's its first model called?")
    assert "What is Turing?" in prompt
    assert "The project." in prompt
    assert "What's its first model called?" in prompt


def test_build_prompt_caps_to_history_turns():
    """Verify build_prompt() limits history to HISTORY_TURNS and drops oldest turns."""
    history = [(f"q{i}", f"a{i}") for i in range(HISTORY_TURNS + 5)]
    prompt = build_prompt(history, "ctx", "new question")
    assert "q0" not in prompt
    assert f"q{len(history) - 1}" in prompt


def test_build_prompt_no_history_omits_section():
    """Verify build_prompt() skips the history section when empty."""
    prompt = build_prompt([], "ctx", "first question")
    assert "Recent conversation:" not in prompt


def test_scope_stays_active_across_keywordless_followup():
    """Verify project_scope() maintains context for follow-ups lacking project keywords."""
    # real bug: "How confident does a match need to be?" right after "What
    # is the FAQ matcher?" has no project keyword AND no pronoun, and got
    # answered with a Wikipedia article about an unrelated comedian. A
    # sticky topic flag catches this where pronoun-matching couldn't.
    scoped, active = project_scope("What is the FAQ matcher?", False)
    assert scoped and active
    scoped, active = project_scope("How confident does a match need to be?", active)
    assert scoped and active


def test_scope_not_active_before_any_project_question():
    """Verify project_scope() returns inactive for general knowledge questions."""
    scoped, active = project_scope("What is the capital of France?", False)
    assert not scoped and not active


def test_scope_officeholder_overrides_active_topic():
    """Verify officeholder queries break out of project scope even with active context."""
    # a live "who's the current X" lookup is a real, tested escape hatch,
    # a resumed project topic should never swallow it
    scoped, active = project_scope("What is Turing?", False)
    assert scoped and active
    scoped, active = project_scope("who's the prime minister of canada", active)
    assert not scoped and active


def test_scope_direct_keyword_match_without_prior_history():
    """Verify project_scope() recognizes project keywords in fresh questions."""
    scoped, active = project_scope("What is its first model called?", False)
    assert scoped and active


def test_officeholder_outage_admits_it_instead_of_answering_from_faq():
    """Verify answer_turn() reports network failure for officeholder lookups, not cached fallback."""
    # A dead Wikidata used to look identical to "not an officeholder
    # question", so the question fell through and FAQ.md answered with its
    # own description of this feature. Stays offline: the stub makes every
    # request fail, so this never touches the network.
    import ask
    real = ask.http_json
    ask.http_json = lambda url, timeout=8, on_error=None: on_error
    try:
        answer, _, _ = answer_turn("who is the current prime minister of canada", [], False)
        assert answer == ask.LOOKUP_FAILED, answer
    finally:
        ask.http_json = real


def test_officeholder_empty_result_is_not_treated_as_an_outage():
    """Verify empty officeholder results are treated as not-found, not network failure."""
    # the other half of the same distinction: a request that succeeds and
    # simply finds no office must still fall through normally, or every
    # "who is ..." question would start claiming the network is down
    import ask
    real = ask.http_json
    ask.http_json = lambda url, timeout=8, on_error=None: {"search": []}
    try:
        assert ask.current_officeholder("who is the wizard of oz") == (None, None)
    finally:
        ask.http_json = real


def test_topic_switch_breaks_out_of_a_sticky_project_topic():
    """Verify general knowledge questions can break the project topic state."""
    # real bug: the sticky flag had no exit except a who-query, so "what is
    # turing" then "what is the capital of japan" answered "the project."
    scoped, active = project_scope("What is Turing?", False)
    assert scoped and active
    scoped, active = project_scope("what is the capital of japan", active)
    assert not scoped and not active
    # and the conversation can come back to the project afterwards
    scoped, active = project_scope("what is samantha", active)
    assert scoped and active


def test_topic_switch_does_not_break_a_keywordless_project_followup():
    """Verify shared vocabulary keeps project topic active even without explicit keywords."""
    # the case the sticky flag exists for must survive: this follow-up has
    # no project keyword, but shares "match" with the project vocabulary
    scoped, active = project_scope("What is the FAQ matcher?", False)
    assert scoped and active
    scoped, active = project_scope("How confident does a match need to be?", active)
    assert scoped and active


def test_pronoun_followup_resolves_to_last_general_knowledge_subject():
    """Verify resolve_followup() substitutes pronouns with their known subject."""
    # real bug: "who is steve jobs" answered correctly, then "what company
    # did he found" returned the 1997 slasher film "I Know What You Did Last
    # Summer", because nothing said who "he" was
    assert subject_of("who is steve jobs") == "steve jobs"
    resolved = resolve_followup("what company did he found", "steve jobs")
    assert resolved == "what company did steve jobs found", resolved


def test_pronoun_followup_without_a_subject_is_untouched():
    """Verify resolve_followup() leaves pronouns alone when no subject is known."""
    assert resolve_followup("what company did he found", None) == "what company did he found"


def test_followup_without_a_pronoun_is_untouched():
    """Verify resolve_followup() passes through questions lacking pronouns."""
    assert resolve_followup("what is the capital of france", "steve jobs") == "what is the capital of france"


def test_alan_turing_is_a_person_not_the_project_faq():
    """Verify a question about Alan Turing skips FAQ.md, which would answer with the project's own blurb."""
    import ask
    with __import__("unittest.mock").mock.patch.object(ask, "general_knowledge", return_value=("Alan Turing was a mathematician.", "Wikipedia: Alan Turing")):
        answer, sources = ask.ask("who was alan turing")
    assert answer == "Alan Turing was a mathematician." and sources == ["Wikipedia: Alan Turing"]


def test_an_answer_that_only_echoes_the_question_is_not_an_answer():
    """Verify the reader guard: a pronoun swapped for "the" adds no information (an album called What Color Is Your Sky)."""
    import ask
    kw = lambda s: set(ask._keywords(s))
    assert not (kw("What Color Is Your Sky") - kw("what color is the sky") - ask._ECHO_FILLER)
    assert kw("The sky looks blue because of Rayleigh scattering") - kw("what color is the sky") - ask._ECHO_FILLER


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
