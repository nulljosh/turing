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
    ("search google for mlx lora", "web_search", "mlx lora"),
    ("google search for dogs", "web_search", "dogs"),
    ("search youtube for lofi hip hop", "open_url", "youtube.com/results?search_query=lofi+hip+hop"),
    ("go to youtube and search lofi", "open_url", "youtube.com/results?search_query=lofi"),
    ("search wireless mice on amazon", "open_url", "amazon.com/s?k=wireless+mice"),
    ("whats the weather", "weather", None),
    ("look up the weather in vancouver", "weather", "vancouver"),
    ("what tabs do i have open", "list_tabs", None),

    ("read github.com/nulljosh/turing", "read_page", "github.com/nulljosh/turing"),
    ("what does news.ycombinator.com say", "read_page", "news.ycombinator.com"),
    ("read the file ~/notes.txt", "read_file", "notes.txt"),

    ("what is 100 days from now", "date_math", "100 days from"),
    ("what time is 3pm pst in tokyo", "convert_time", "3pm pst in tokyo"),
    ("ask claude why is the sky blue", "ask_llm", "claude\twhy is the sky blue"),
    ("log me into gmail", None, None),
    ("log into gmail and check my email", None, None),
    ("walk me through checkout", None, None),
    ("research the history of the printing press", "research", "the history of the printing press"),
    ("save that", "save_research", ""),
    ("save it to ~/Desktop/notes.md", "save_research", "~/Desktop/notes.md"),
    ("draft an email about the v3.1 release", "write_document", "the v3.1 release"),
    ("write a doc about the roadmap", "write_document", "the roadmap"),
    ("draft me a file for the meeting notes", "write_document", "the meeting notes"),
    ("write a note about the meeting", "new_note", "about the meeting"),  # "note" stays with new_note, never write_document
    ("do some research on kinship", "research", "kinship"),
    ("deep dive into mitochondria", "research", "mitochondria"),
    ("write me a brief on the silk road", "research", "the silk road"),
    ("stats on sales.csv", "run_code", "sales.csv"),
    ("average of the price column in sales.csv", "run_code", "sales.csv"),
    ("chart sales.csv", "run_code", "sales.csv"),
    ("plot column price of sales.csv", "run_code", "sales.csv"),
    ("look at my screen", "see_screen", ""),
    ("look at my screen and tell me what's wrong with this chart", "see_screen", "tell me what's wrong with this chart"),
    ("what do you see", "see_screen", ""),
    ("what's in ~/Desktop/cat.png", "see_image", "\t~/Desktop/cat.png"),
    ("look at ~/Pictures/trip.jpg and tell me where this is", "see_image", "tell me where this is\t~/Pictures/trip.jpg"),
    ("what's on my screen", "read_screen", ""),
    ("click Sign in", "click_text", "Sign in"),
    ("click on the Submit button", "click_text", "Submit"),
    ("tap \"Next\"", "click_text", "Next"),
    ("press return", "press_key", "return"),
    ("hit the tab key", "press_key", "tab"),
    ("press Continue", "click_text", "Continue"),
    ("type hello world", "type_text", "hello world"),
    ("claude, explain monads simply", "ask_llm", "claude\texplain monads simply"),
    ("have claude write a haiku about turing", "ask_llm", "claude\twrite a haiku about turing"),
    ("ask qwen what is a monad", "ask_llm", "qwen\twhat is a monad"),
    ("ask llama3.1:8b to name three rivers", "ask_llm", "llama3.1:8b\tname three rivers"),
    ("ask an llm why the sky is blue", "ask_llm", "an llm\twhy the sky is blue"),
    ("gemma, what is 2 to the 10th", "ask_llm", "gemma\twhat is 2 to the 10th"),
    ("convert 3pm pst to tokyo", "convert_time", "3pm pst to tokyo"),
    ("15:30 london to new york", "convert_time", "15:30 london to new york"),
    ("convert 5 km to miles", "convert_units", "5 km to miles"),
    ("what day of the week was july 4 1976", "date_math", "weekday july 4 1976"),
    ("how many days between 2026-01-01 and christmas", "date_math", "between 2026-01-01 and christmas"),
    ("3 weeks ago", "date_math", "3 weeks ago"),

    # photos, exact, no model needed
    ("make ~/Desktop/cat.png black and white", "grayscale_image", "~/Desktop/cat.png"),
    ("remove the background from ~/Desktop/cat.jpg", "remove_background", "~/Desktop/cat.jpg"),
    ("rotate the photo ~/a.png by 180", "rotate_image", "~/a.png by 180"),
    ("flip ~/a.png vertically", "flip_image", "~/a.png vertical"),
    ("resize ~/a.png to 500", "resize_image", "~/a.png to 500"),
    ("convert ~/a.png to jpg", "convert_image", "~/a.png to jpg"),
    ("crop ~/a.png to a square", "crop_square", "~/a.png"),
    ("upscale ~/a.heic", "upscale_image", "~/a.heic"),

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
    ("unread mail", "unread_mail", ""),
    ("do i have any new email", "unread_mail", ""),
    ("anything from the bank in my mail today", "unread_mail", "the bank"),
    ("email from amazon", "unread_mail", "amazon"),
    ("what needs my attention", "needs_attention", None),
    ("what needs me", "needs_attention", None),
    ("am i free", "free_when", None),
    ("am i free thursday afternoon", "free_when", "thursday afternoon"),
    ("when am i free this week", "free_when", "this week"),
    ("do i have time thursday afternoon", "free_when", "thursday afternoon"),
    ("transcribe the video ~/Desktop/clip.mp4", "transcribe_video", "~/Desktop/clip.mp4"),
    ("summarize ~/Desktop/report.pdf", "summarize", "~/Desktop/report.pdf"),
    ("summarize this page", "summarize", ""),
    ("summarize my unread mail", "summarize", "mail"),
    ("summarize https://example.com/post", "summarize", "https://example.com/post"),
    ("summarize what turing is in one sentence", None, None),
    ("translate good morning to french", "translate", "good morning\tfrench"),
    ("translate the page github.com into spanish", "translate", "github.com\tspanish"),
    ("how do you say thank you in japanese", "translate", "thank you\tjapanese"),
    ("translate 5 km to miles", None, None),
    ("find report.pdf", "find_file", "report.pdf"),
    ("where is my resume.docx", "find_file", "resume.docx"),
    ("what's in my downloads", "recent_downloads", None),
    ("what did i just download", "recent_downloads", None),
    ("how big is ~/Documents", "folder_size", "~/Documents"),
    ("find milk in document ~/notes.pdf", "find_in_document", "milk"),
    ("find sign in on my screen", "read_screen", "sign in"),
    ("move ~/Desktop/a.txt to ~/Documents", "move_file", "~/Desktop/a.txt\t~/Documents"),
    ("copy the file ~/Desktop/a.txt into ~/Documents", "copy_file", "~/Desktop/a.txt\t~/Documents"),
    ("rename ~/Desktop/a.txt to b.txt", "rename_file", "~/Desktop/a.txt\tb.txt"),
    ("zip ~/Desktop/photos", "zip_file", "~/Desktop/photos"),
    ("unzip ~/Downloads/a.zip", "unzip_file", "~/Downloads/a.zip"),
    ("trash ~/Desktop/a.txt", "trash_file", "~/Desktop/a.txt"),
    ("delete the file ~/Desktop/a.txt", "trash_file", "~/Desktop/a.txt"),
    ("move on to the next song", None, None),
    ("delete my account", None, None),
    ("summarize github.com", "summarize", "github.com"),
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
