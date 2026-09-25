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
}
# ...and words that say the sentence is about a different tool. "say help in morse code" is morse_code, not say.
_AGAINST = {"say": r"morse|clock say", "wifi_name": r"address|\bip\b", "open_app": r"shortcut", "weather": r"\bapp\b", "web_search": r"\.(?:com|org|net|io|ca)\b"}


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

    # "words<TAB>path": both halves have to be real, and the path has to be one she was actually given
    if tool in ("find_in_document", "ask_document"):
        words, _, path = arg.partition("\t")
        return bool(words) and bool(path) and path.lower() in q_lower and words.lower() in q_lower

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
