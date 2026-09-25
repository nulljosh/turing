"""Wires the organizer/system/dev tool families into TOOLS, plus the WRITES and
NOT_FOR_MODELS classifications and the soundness guard that keeps a model's tool pick
honest. Split from tools.py for size (CLAUDE.md, File size). register_families() mutates
the caller's own TOOLS dict and globals() (tools.py's), not this module's, so a moved
name still lives on the tools module and eval/actions.py can keep patching it there.
"""
import re

import tools_dev
import tools_organizer
import tools_system
from tools_apps import _MUSIC, duration

FAMILIES = (tools_organizer, tools_system, tools_dev)


def register_families(tools_dict, tools_globals):
    """Add every organizer/system/dev tool to TOOLS and to the caller's globals."""
    for mod in FAMILIES:
        tools_dict.update({f.__name__: f for f in mod.TOOLS})
        tools_globals.update({f.__name__: f for f in mod.TOOLS})


# These fire something with a side effect the user did not see coming (a Shortcut can send a
# message, a clipboard write loses what was there, the screen goes dark). Only a command that
# names them runs them, never a model's own choice. The real fix is the harness asking first.
NOT_FOR_MODELS = {"ask_llm", "see_screen", "see_image", "see_camera", "click_text", "type_text", "press_key", "run_shortcut", "copy_to_clipboard", "sleep_display", "call_mcp_tool", "close_tab", "remember", "recall", "forget", "read_screen", "ask_screen",
                   "edit_last_draft", "edit_file", "write_code"}  # her memory is private: only her own commands and the harness touch it. edit_last_draft needs the in-process path it just wrote, and confirms itself with the diff, so it is phrase-routed only, never a model's own pick or MCP

# Tools that leave something behind or send something out: a note, a reminder, a file on the
# Desktop, a Shortcut, the clipboard, a dark screen. The harness asks before any of these run.
WRITES = {"ask_llm", "see_screen", "see_image", "see_camera", "click_text", "type_text", "press_key", "ask_screen", "read_screen", "remember", "forget", "close_tab", "call_mcp_tool", "new_note", "new_reminder", "make_logo", "paint_image", "run_shortcut", "copy_to_clipboard", "sleep_display", "save_research", "write_document", "run_code",
          "remove_background", "upscale_image", "enhance_image", "grayscale_image", "rotate_image", "flip_image",
          "resize_image", "crop_square", "convert_image", "move_file", "copy_file", "rename_file", "zip_file", "unzip_file", "trash_file",
          "complete_reminder", "add_event", "append_note", "quit_app", "do_not_disturb", "run_tests"}


# A pick with no argument to check (disk_space, uptime...) or a loose one needs evidence in the sentence: some word that
# is really about that tool. Round four confused ip_address with wifi_name and let "let me know in 10 minutes" write a note.
_EVIDENCE = {
    "disk_space": r"disk|storage|space|drive|room|full", "uptime": r"\bup\b|uptime|restart|reboot|been on|running|booted",
    "current_tab": r"\btab\b|page|site|browser|chrome|safari|article|reading|looking at", "list_tabs": r"\btabs\b",
    "memory_usage": r"memory|\bram\b", "cpu_load": r"cpu|processor|load|busy|maxed|working|doing", "ip_address": r"\bip\b|address",
    "wifi_name": r"wi-?fi|network", "system_info": r"system|\bmac\b|macos|chip|computer|specs|about this", "list_shortcuts": r"shortcut",
    "flip_coin": r"coin|heads|tails", "make_uuid": r"uuid|guid", "time_in": r"time|clock|late", "days_until": r"\bday|sleeps|until|till|far away|count",
    "roll_dice": r"roll|dice|\bdie\b|\bd\d|throw|toss", "random_number": r"random|number", "make_password": r"password",
    "hash_text": r"hash|sha|checksum", "word_count": r"word", "tip": r"\btip", "is_prime": r"prime|factor|divid", "roman_numeral": r"roman",
    "morse_code": r"morse", "new_note": r"note|jot|write|remember|save|down", "say": r"\bsay|speak|announce|voice|aloud|out loud|words",
    "free_when": r"\bfree\b|\bbusy\b|availab|do i have time|when am i|\bschedule\b",
    # Round eight covered 36 tools with zero picker training data; their evidence predates them (round-eight
    # gap). Words come from each tool's own docstring/templates, never copied out of eval/actions.py verbatim.
    "bluetooth_status": r"bluetooth", "calendar_tomorrow": r"tomorrow",
    "running_apps": r"running|open apps|apps open|what's open|apps are open",
    "recent_downloads": r"download", "unread_mail": r"mail|email|inbox",
    "git_status": r"status|changed|dirty|\bdiff\b|\bbranch\b", "recent_commits": r"commit",
    "run_tests": r"\btest", "open_prs": r"\bprs?\b|pull request",
    "open_in_editor": r"editor|vscode|vs code|in code", "quit_app": r"quit|close|shut down|\bkill\b",
    "dark_mode": r"dark|\blight\b|appearance|theme", "do_not_disturb": r"disturb|\bdnd\b|focus|silence|quiet",
    "zip_file": r"\bzip\b|compress", "unzip_file": r"unzip|extract", "trash_file": r"trash|delete|throw away|get rid of",
    "copy_file": r"\bcopy\b|duplicate", "move_file": r"\bmove\b|relocate", "rename_file": r"rename|new name|call it",
    "append_note": r"\bnote\b", "add_event": r"calendar|event|schedule",
    "complete_reminder": r"remind|done|finish|complete|check off|\bmark\b", "list_reminders": r"reminder",
    "search_notes": r"\bnotes?\b", "needs_attention": r"attention|needs me|focus on|deal with|need to handle|urgent",
    "find_file": r"find|locate|where(?:'s| is)", "folder_size": r"\bbig\b|\bsize\b|\bspace\b|take up",
    "research": r"research|deep dive|look into|dig into|investigate", "research_more": r"\bmore\b|deeper|expand|further|continue|again",
    "summarize": r"summar", "transcribe_video": r"transcribe|said in|captions|subtitles",
    "translate": r"translat|how do you say", "write_document": r"draft|write (?:a |an )?(?:doc|document|email|memo|file)|compose",
    # Round ten: resize_image and read_file had no evidence at all, so any wrong pick with its
    # argument copied verbatim (list_dir/read_file's own guard, or resize_image's default check,
    # never required a word about the tool itself) passed the guard automatically. "make it bigger"
    # with no number is upscale_image, not resize_image; "crunch the numbers in X" is run_code,
    # not read_file's own words.
    "resize_image": r"resize|resolution|\bsize\b|\d",
    "read_file": r"\bread\b|\bcat\b|\bshow\b|\bprint\b|display|\bsay\b|contents|written",
}
# ...and words that say the sentence is about a different tool. "say help in morse code" is morse_code, not say.
_AGAINST = {"say": r"morse|clock say", "wifi_name": r"address|\bip\b", "weather": r"\bapp\b", "web_search": r"\.(?:com|org|net|io|ca)\b",
            # "close the github tab" is close_tab, not quit_app. "extract the zip" is unzip_file, not zip_file.
            # "summarize my unread mail" is summarize, not unread_mail.
            "quit_app": r"\btab\b", "zip_file": r"\bextract\b|\bunzip\b", "unread_mail": r"\bsummar",
            # Round ten: open_app had zero _AGAINST, so any single shared word ("tests", the arg
            # itself, "finder") let it fire on a sentence that is really about a different tool.
            # These are phrases, not bare words, so "open mail"/"open finder"/"open tests" (real
            # app opens, if such an app existed) still pass; only the multi-word context that marks
            # the sentence as being about mail, Finder-reveal, a browser tab or the test suite blocks it.
            "open_app": r"\bnew email\b|\bunread mail\b|\bmail from\b|\bemail from\b|\bin (?:the )?finder\b|\btab\b|\btests?\b|test suite",
            # "write a brief on X" / "do my notes mention X" are research/search_notes, not new_note:
            # new_note's own evidence regex matches bare "write" or "note", which both leak into these.
            "new_note": r"\bbrief\b|\bresearch\b|\bmention\b|\bsearch\b.{0,20}\bnotes?\b|\bfind\b.{0,20}\bnotes?\b|\blook for\b.{0,20}\bnotes?\b"}


def _sound(tool, arg, query):
    """Is this pick safe to run? She was trained to copy her argument out of
    the sentence, never to compose one. So an argument that is not in the
    sentence is a guess, and a guess does not get to touch the Mac."""
    import tools  # here, not at the top: tools.py imports this module as it loads
    q_lower = query.lower()

    if tool in _EVIDENCE and not re.search(_EVIDENCE[tool], q_lower):
        return False
    if tool in _AGAINST and re.search(_AGAINST[tool], q_lower):
        return False

    if tool == "set_volume":
        # "mute" and "kill the sound" mean 0, and no digit appears in the sentence
        silent = arg == "0" and re.search(r"\b(?:mute|silen\w+|(?:sound|volume|audio) off|kill the (?:sound|volume|audio))\b", query, re.I)
        return arg in ("up", "down") or bool(silent) or (arg.isdigit() and arg in query)
    if tool == "music":
        # arg must be an exact command, not a loose phrase
        return arg in _MUSIC or arg == "playing"
    if tool == "timer":
        return duration(arg) is not None and arg.lower() in q_lower
    if tool in ("list_dir", "read_file"):
        return bool(arg)

    # "words<TAB>path": both halves have to be real, and the path has to be one she was actually given.
    # Same shape for the round-eight file/note/translate tools, which also copy two pieces out of the
    # sentence joined by a tab: source<TAB>destination, content<TAB>note name, text<TAB>language.
    if tool in ("find_in_document", "ask_document", "copy_file", "move_file", "rename_file", "translate"):
        a, _, b = arg.partition("\t")
        return bool(a) and bool(b) and a.lower() in q_lower and b.lower() in q_lower

    # append_note is the same content<TAB>note-name shape, but round nine showed a wrapper phrasing
    # ("append call bob to the note todo") where the model folds the note name into the copied text
    # instead of splitting on tab. Recover the trailing "note <name>" / "to the <name> note" phrasing
    # from the sentence itself rather than trusting an unsplit argument.
    if tool == "append_note":
        a, _, b = arg.partition("\t")
        if not b:
            m = re.search(r"\bnote (\w[\w ]*)$", q_lower) or re.search(r"to (?:the |my )?(\w[\w ]*?) note\b", q_lower)
            b = m.group(1).strip() if m else ""
        return bool(a) and bool(b) and a.lower() in q_lower and b.lower() in q_lower

    # zip_file/folder_size copy a path she resolves against the home folder ("~/Documents"), but the
    # sentence usually names the folder in plain words ("the documents folder", "my music folder"), not
    # the resolved path itself. Real evidence is the path's own last component showing up in the words.
    if tool in ("zip_file", "folder_size"):
        if not arg:
            return False
        base = arg.rstrip("/").rsplit("/", 1)[-1].lower()
        return bool(base) and (arg.lower() in q_lower or base in q_lower)

    # dark_mode/do_not_disturb take "on", "off" or (dark_mode only) "toggle": a guess at direction is not
    # a copy, so the sentence has to say which way, not just that the tool is on topic.
    if tool == "dark_mode":
        a = arg.lower()
        if a == "toggle":
            return bool(re.search(r"toggle|flip|switch\b", q_lower))
        if a == "off":
            return bool(re.search(r"\boff\b|\blight\b|disable|turn down", q_lower))
        if a == "on":
            return bool(re.search(r"\bon\b|\bdark\b|enable", q_lower))
        return False
    if tool == "do_not_disturb":
        a = arg.lower()
        if a == "off":
            return bool(re.search(r"\boff\b|out of|disable|turn off|end focus|\bstop\b", q_lower))
        if a == "on":
            return bool(re.search(r"\bon\b|enable|turn on|start focus|\benter\b", q_lower))
        return False

    # add_event's argument is the event title, which the model sometimes pads with the time phrase
    # ("dentist at 3pm"), so it is not always a contiguous substring of the sentence. Every real word in
    # it still has to show up somewhere in the sentence, just not necessarily next to each other.
    if tool == "add_event":
        words = [w for w in re.findall(r"[a-z0-9]+", arg.lower()) if w not in ("at", "on", "to", "the", "a", "an", "my", "calendar")]
        return bool(words) and all(w in q_lower for w in words)

    # An app or a site with no name is never a real command.
    if not arg and tool in ("open_app", "open_url"):
        return False

    # "notes" is the app, not something to write down.
    if tool == "new_note" and len(arg.split()) == 1 and arg.lower() in tools.TOOLS:
        return False

    # Reject say() if arg looks like a timer duration
    if tool == "say" and duration(arg) is not None:
        return False  # "say 8 minutes" is likely a mispicked timer

    # Reject new_reminder() if query says "notes" not "remind"
    if tool == "new_reminder" and re.search(r"\bnotes?\b", q_lower) and not re.search(r"\b(?:remind|reminder)\b", q_lower):
        return False  # picked reminder when user said "notes"

    # Reject web_search for multi-step queries (dig through, poke around)
    if tool == "web_search" and re.search(r"\b(?:dig through|poke around|find something)\b", q_lower):
        return False  # this is agent work, not a simple search

    # Reject open_url() if arg looks like an app name
    if tool == "open_url":
        if arg.lower() in ("chrome", "safari", "firefox"):
            return False  # these are apps, not URLs
        if tools._url(arg) is None and " " not in arg.strip():
            return False  # one word that is no site. A phrase is something to look for, open_url searches it

    # Default: arg must appear in the query (lowercased)
    return tool in tools.TOOLS and arg.lower() in q_lower
