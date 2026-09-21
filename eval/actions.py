"""Does Samantha's regex router recognize single-step commands correctly?

Every command has one right action. act() is a regex router, instant and
exact, not a model. This measures: for each input, WHICH tool fired, and
with WHAT argument. Mock every tool so nothing real runs. Track which tool
each case fired and what argument it got, then compare against expectations.
Failures here reveal commands that miswire or fall through to agent when
they should not.

Run: ./.venv/bin/python eval/actions.py [--verbose] [--min N]
"""
import os
import sys

os.environ["SAMANTHA_HEADLESS"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools


# (command, expected_tool_or_None, expected_arg_substring_or_None)
CASES = [
    # opening apps
    ("open chrome", "open_app", "chrome"),
    ("launch safari", "open_app", "safari"),
    ("start pixelmator", "open_app", "pixelmator"),
    ("make me a logo for turing", "make_logo", "turing"),
    ("make me a complex logo for a surf school", "make_logo", "complex a surf school"),
    ("make me an original wordless logo for turing", "make_logo", "original wordless turing"),
    ("design an abstract icon for a bakery", "make_logo", "abstract a bakery"),

    # opening sites
    ("go to hacker news", "open_url", "hacker news"),
    ("visit github.com", "open_url", "github.com"),
    ("pull up reddit", "open_url", "reddit"),
    ("browse to youtube", "open_url", "youtube"),
    ("open x.com", "open_url", "x.com"),

    # search
    ("search for mlx lora", "web_search", "mlx"),
    ("google best pizza vancouver", "web_search", "pizza"),
    ("look up qwen3", "web_search", "qwen3"),

    # tab
    ("what's in my current tab", "current_tab", None),
    ("what's on my tab", "current_tab", None),

    # screenshot
    ("take a screenshot", "screenshot", None),
    ("grab a screenshot", "screenshot", None),

    # clipboard
    ("what's on my clipboard", "clipboard", None),
    ("read my clipboard", "clipboard", None),

    # volume
    ("volume 30", "set_volume", "30"),
    ("set the volume to 50", "set_volume", "50"),
    ("mute", "set_volume", "0"),

    # battery
    ("how's my battery", "battery", None),
    ("battery level", "battery", None),
    ("what's my battery", "battery", None),

    # say
    ("say hello there", "say", "hello"),
    ("say test", "say", "test"),

    # files
    ("list the files in ~/Documents", "list_dir", "Documents"),
    ("show me the folder in ~/Desktop", "list_dir", "Desktop"),
    ("read the file ~/notes.txt", "read_file", "notes.txt"),
    ("show me the file ~/test.md", "read_file", "test.md"),

    # chrome + open url combined
    ("open chrome and go to youtube", "open_url", "youtube"),
    ("launch chrome then visit github.com", None, None),

    # negative cases: plain questions (should return None)
    ("what is turing", None, None),
    ("who is steve jobs", None, None),
    ("what is 17*23", None, None),
    ("what is the capital of japan", None, None),

    # negative cases: multi-step (agent work, not action)
    ("open chrome and poke around hacker news", None, None),
    ("go to github then tell me what tab is open", None, None),
    ("open pixelmator and read my clipboard", None, None),
    ("search for mlx lora and summarize", None, None),
    ("Summarize what Turing is in one sentence.", None, None),
    # 2026-09-20: how a person actually asks. 10 of these 16 missed before
    # tools._bare() stripped the politeness, and two fired the wrong tool.
    ("can you open chrome", "open_app", "chrome"),
    ("please open safari", "open_app", "safari"),
    ("open up spotify for me", "open_app", "spotify"),
    ("turn the volume down to 20", "set_volume", "20"),
    ("turn it up to 80", "set_volume", "80"),
    ("what's my battery at", "battery", None),
    ("how much battery do i have", "battery", None),
    ("take a screenshot please", "screenshot", None),
    ("show me what's on my clipboard", "clipboard", None),
    ("hey open github", "open_url", "github"),
    ("i want to go to youtube", "open_url", "youtube"),
    ("could you search for mlx lora", "web_search", "mlx lora"),
    # a phrase that is no app is something to look for, never a fake app name
    ("open the turing repo on github", "open_url", "turing repo"),
    ("can you tell me who alan turing was", None, None),
    # 2026-09-21: music and personal tools
    ("play some music", "music", "play"),
    ("pause the music", "music", "pause"),
    ("skip this song", "music", "next"),
    ("can you skip", "music", "next"),
    ("what's playing", "music", "playing"),
    ("what song is this", "music", "playing"),
    ("what's the weather", "weather", None),
    ("how's the weather in tokyo", "weather", "tokyo"),
    ("weather", "weather", None),
    ("set a timer for 5 minutes", "timer", "5"),
    ("set a 10 minute timer", "timer", "10"),
    ("timer 30 seconds", "timer", "0.5"),
    ("remind me to call mom", "new_reminder", "call mom"),
    ("add a reminder to buy milk", "new_reminder", "buy milk"),
    ("take a note buy milk", "new_note", "buy milk"),
    ("make a note that says the door code is 4417", "new_note", "door code"),
    ("what's on my calendar today", "calendar_today", None),
    ("what do i have today", "calendar_today", None),
    # these look like the new commands and are not
    ("what is the weather system on jupiter", None, None),
    ("what is music theory", None, None),
    ("who plays the next james bond", None, None),
]


def main():
    """Test the regex action router against known commands and expected tool firings."""
    verbose = "--verbose" in sys.argv
    minimum = None
    for i, arg in enumerate(sys.argv):
        if arg == "--min" and i + 1 < len(sys.argv):
            minimum = int(sys.argv[i + 1])

    # Mock all tools. Each returns a recorder appended to this list.
    calls = []

    def make_recorder(name):
        """Create a mock tool that records when it was called."""
        def recorder(*args, **kwargs):
            """Record this mock tool call and return ok."""
            calls.append((name, args, kwargs))
            return "ok"
        return recorder

    original_tools = {}
    for tool_name in tools.TOOLS:
        original_tools[tool_name] = getattr(tools, tool_name)
        setattr(tools, tool_name, make_recorder(tool_name))

    passed = 0
    failed = 0
    failures = []

    for cmd, expected_tool, expected_arg in CASES:
        calls.clear()
        result = tools.act(cmd)

        if expected_tool is None:
            # Expect None (no action matched, or multi-step)
            if result is None and not calls:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1
                what_fired = calls[0][0] if calls else "None"
                failures.append((cmd, expected_tool, what_fired))
        else:
            # Expect a specific tool to fire
            if not calls:
                status = "FAIL"
                failed += 1
                failures.append((cmd, expected_tool, "None"))
            else:
                tool_name, args, kwargs = calls[0]
                if tool_name == expected_tool:
                    # Check if expected_arg is in the arguments
                    if expected_arg is None:
                        status = "PASS"
                        passed += 1
                    else:
                        combined_args = " ".join(str(a) for a in args) + " " + " ".join(str(v) for v in kwargs.values())
                        if expected_arg.lower() in combined_args.lower():
                            status = "PASS"
                            passed += 1
                        else:
                            status = "FAIL"
                            failed += 1
                            failures.append((cmd, expected_tool, tool_name))
                else:
                    status = "FAIL"
                    failed += 1
                    failures.append((cmd, expected_tool, tool_name))

        if verbose or status == "FAIL":
            print(f"[{status}] {cmd}")
            if calls:
                tool_name, args, kwargs = calls[0]
                print(f"        fired: {tool_name}({args})")

    # Restore original tools
    for tool_name, original in original_tools.items():
        setattr(tools, tool_name, original)

    total = len(CASES)
    print(f"\n{passed}/{total} passed")

    if failures:
        print("\nFailing commands:")
        for cmd, expected, actual in failures:
            print(f"  {cmd!r}")
            print(f"    expected: {expected}, got: {actual}")

    if minimum is not None and passed < minimum:
        print(f"REGRESSION: {passed} passed is below the required minimum {minimum}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
