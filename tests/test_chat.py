"""Regression check for chat.py's pure logic (no model calls, no interactive
loop): clean() stripping echoed scaffold, build_prompt() history handling.
This is the one thing that was never automated, only manually eyeballed
once when the indentation bug got fixed (see roadmap.md).

Usage: ./.venv/bin/python tests/test_chat.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    import ask, ask_web
    dead = lambda url, timeout=8, on_error=None: on_error
    # the officeholder lookup lives in ask_web, the encyclopedia fallback in ask: both see the outage
    with __import__("unittest.mock").mock.patch.object(ask_web, "http_json", dead), \
         __import__("unittest.mock").mock.patch.object(ask, "http_json", dead):
        answer, _, _ = answer_turn("who is the current prime minister of canada", [], False)
    assert answer == ask.LOOKUP_FAILED, answer


def test_officeholder_empty_result_is_not_treated_as_an_outage():
    """Verify empty officeholder results are treated as not-found, not network failure."""
    # the other half of the same distinction: a request that succeeds and
    # simply finds no office must still fall through normally, or every
    # "who is ..." question would start claiming the network is down
    import ask, ask_web
    with __import__("unittest.mock").mock.patch.object(ask_web, "http_json", lambda url, timeout=8, on_error=None: {"search": []}):
        assert ask.current_officeholder("who is the wizard of oz") == (None, None)


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


def test_small_talk_answers_without_a_model_and_leaves_commands_alone():
    """Verify a greeting or "what can you do" gets a real reply, and a command that starts like one still reaches the tools."""
    import ask, tools
    assert ask.local_answer("hi")[0].startswith("Hi.")
    assert ask.local_answer("Hello there!")[1] == "small talk"
    assert f"{len(tools.TOOLS)} tools" in ask.local_answer("what can you do?")[0]
    assert "web search" in ask.local_answer("list your tools")[0] and ask.small_talk("tell me about your tools")
    for command in ("hey calculate 8 + 8", "help me find a file", "thanks for nothing, who is alan turing"):
        assert ask.small_talk(command) is None


def test_a_missing_model_is_a_reply_not_a_crash():
    """Verify a project question the model must write is answered honestly when the model is not installed."""
    import chat
    mock = __import__("unittest.mock").mock
    with mock.patch.object(chat, "search", return_value=[{"text": "ctx"}]), mock.patch.object(chat, "try_extract", return_value=None), \
         mock.patch.object(chat, "faq_match", return_value=None), \
         mock.patch.object(chat, "_model", side_effect=OSError("answer model unavailable: no weights")):
        answer, _, _ = chat.answer_turn("write a commit message for the turing picker", [], True)
    assert answer == chat.MODEL_DOWN


def test_replies_stream_and_stop_at_echoed_scaffold():
    """Verify generate() hands out words as they come, never shows a half-written User: marker, and stops at the echo."""
    import sys, types
    import chat
    mock = __import__("unittest.mock").mock
    pieces = ["Train", "ing runs", " on the", " Mac.", "\nUs", "er: and", " more"]
    fake = types.ModuleType("mlx_lm")
    fake.stream_generate = lambda model, tok, prompt, max_tokens, **kw: (types.SimpleNamespace(text=p) for p in pieces)
    tok = types.SimpleNamespace(apply_chat_template=lambda msgs, **kw: msgs[0]["content"])
    got = []
    with mock.patch.dict(sys.modules, {"mlx_lm": fake}), mock.patch.object(chat, "_model", return_value=(None, tok)), \
            mock.patch.object(chat, "REPETITION", 0):
        text = chat.generate("p", on_text=got.append)
    assert "".join(got) and "User" not in "".join(got) and "Us" not in "".join(got)[-3:]
    assert "Training runs on the Mac.".startswith("".join(got))
    assert chat.clean(text, "q") == "Training runs on the Mac."


def test_replies_stop_after_two_sentences():
    """Verify generation stops after two sentences, where her lessons end and invention begins."""
    import sys, types
    import chat
    mock = __import__("unittest.mock").mock
    pieces = ["Roost uses Supabase.", " It has no backend.", " So the filter state resets", " on every navigation."]
    fake = types.ModuleType("mlx_lm")
    fake.stream_generate = lambda model, tok, prompt, max_tokens, **kw: (types.SimpleNamespace(text=p) for p in pieces)
    tok = types.SimpleNamespace(apply_chat_template=lambda msgs, **kw: msgs[0]["content"])
    with mock.patch.dict(sys.modules, {"mlx_lm": fake}), mock.patch.object(chat, "_model", return_value=(None, tok)), \
            mock.patch.object(chat, "SENTENCES", 2), mock.patch.object(chat, "REPETITION", 0):
        assert chat.generate("p") == "Roost uses Supabase. It has no backend."


def test_a_broken_tool_through_ask_is_a_reply():
    """Verify ask.py and serve.py, which reach the tools through local_answer, report a missing command instead of crashing."""
    import ask
    mock = __import__("unittest.mock").mock
    with mock.patch("subprocess.run", side_effect=FileNotFoundError(2, "No such file", "osascript")):
        answer, source = ask.local_answer("set the volume to 30")
    assert answer == "I tried that, but it did not work: osascript is not on this machine." and source == "tools"


def test_any_failure_in_the_answer_chain_keeps_the_chat_alive():
    """Verify safe_turn turns an unexpected error into a reply and keeps the conversation state."""
    import chat
    mock = __import__("unittest.mock").mock
    with mock.patch.object(chat, "answer_turn", side_effect=RuntimeError("boom")):
        answer, topic, subject = chat.safe_turn("anything", [], True, "steve jobs")
    assert "boom" in answer and topic is True and subject == "steve jobs"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"[PASS] {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
