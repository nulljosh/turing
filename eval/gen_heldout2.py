"""Blind writer script for heldout2. Not part of the tool suite; run once to emit eval/heldout2.jsonl."""
import json

from gen_heldout2_nulls import NULLS

ROWS = []

def add(text, tool, arg_hint=""):
    """Append one heldout2 row: a phrasing, the expected tool (or None), and an arg hint."""
    ROWS.append({"text": text, "tool": tool, "arg_hint": arg_hint})

# --- add_event ---
add("add lunch with sam to my calendar tomorrow at noon", "add_event", "lunch")
add("can u put dentist appt on the calender for 3pm thursday", "add_event", "dentist")
add("I need you to book a call with the accountant tomorrow at 9", "add_event", "call")
add("stick 'gym' on the calendar for 6am tmrw", "add_event", "gym")

# --- append_note ---
add("add eggs to my shopping note", "append_note", "eggs")
add("can you tack 'call mom' onto my todo note", "append_note", "call mom")
add("append milk to the groceries note pls", "append_note", "milk")
add("chuck 'renew passport' at the bottom of my errands note", "append_note", "renew passport")

# --- ask_document ---
add("what does the contract say about termination, check the pdf on my desktop", "ask_document", "termination")
add("ask the report.docx what the revenue number was", "ask_document", "revenue")
add("does my lease mention parking, look in lease.pdf", "ask_document", "parking")
add("whats the deadline in proposal.pdf", "ask_document", "deadline")

# --- base64_decode ---
add("decode this base64: aGVsbG8gd29ybGQ=", "base64_decode", "aGVsbG8gd29ybGQ=")
add("what does SGVsbG8= actually say", "base64_decode", "SGVsbG8=")
add("can u turn this b64 back into text: d29ybGQ=", "base64_decode", "d29ybGQ=")
add("un-base64 this for me: Zm9vYmFy", "base64_decode", "Zm9vYmFy")

# --- base64_encode ---
add("base64 encode 'hello world'", "base64_encode", "hello world")
add("turn the word turing into base64", "base64_encode", "turing")
add("encode my name Joshua as b64", "base64_encode", "Joshua")
add("i need 'secret token' in base64 form", "base64_encode", "secret token")

# --- battery ---
add("whats my battery at", "battery", "")
add("check battery pls", "battery", "")
add("how much charge left on this thing", "battery", "")
add("is it plugged in, battery status", "battery", "")

# --- bluetooth_status ---
add("is bluetooth on", "bluetooth_status", "")
add("whats connected over bluetooth rn", "bluetooth_status", "")
add("check bluetooth status for me", "bluetooth_status", "")
add("bluetooth on or off atm", "bluetooth_status", "")

# --- calculate ---
add("whats 15% of 80", "calculate", "15% of 80")
add("can u work out 342 * 17 for me", "calculate", "342 * 17")
add("(45+12)/3 what does that equal", "calculate", "(45+12)/3")
add("sqrt of 144 pls", "calculate", "sqrt")

# --- calendar_today ---
add("whats on my calendar today", "calendar_today", "")
add("anything happening today", "calendar_today", "")
add("check todays schedule", "calendar_today", "")
add("do i have meetings today", "calendar_today", "")

# --- calendar_tomorrow ---
add("whats on tomorrow", "calendar_tomorrow", "")
add("check my schedule for tmrw", "calendar_tomorrow", "")
add("anything on the calendar tomorrow", "calendar_tomorrow", "")
add("am i busy tomorrow", "calendar_tomorrow", "")

# --- clipboard ---
add("whats on my clipboard rn", "clipboard", "")
add("what did i just copy", "clipboard", "")
add("read the clipboard for me", "clipboard", "")
add("check whats copied", "clipboard", "")

# --- complete_reminder ---
add("mark buy milk as done", "complete_reminder", "buy milk")
add("i finished the dentist reminder, complete it", "complete_reminder", "dentist")
add("tick off 'call the bank' from reminders", "complete_reminder", "call the bank")
add("check off pick up dry cleaning", "complete_reminder", "dry cleaning")

# --- convert_image ---
add("convert cat.png to jpg", "convert_image", "cat.png to jpg")
add("turn ~/Desktop/photo.heic into a png pls", "convert_image", "photo.heic to png")
add("can u make this a webp: logo.jpg", "convert_image", "logo.jpg to webp")
add("i need beach.tiff as a pdf", "convert_image", "beach.tiff to pdf")

# --- convert_time ---
add("whats 3pm PST in Tokyo", "convert_time", "3pm PST in Tokyo")
add("convert 15:30 london time to new york", "convert_time", "15:30 London to New York")
add("if its 9am here whats that in sydney", "convert_time", "9am in Sydney")
add("what time is noon EST over in Berlin", "convert_time", "noon EST in Berlin")

# --- convert_units ---
add("5 km to miles pls", "convert_units", "5 km to miles")
add("how many kg is 150 lbs", "convert_units", "150 lbs to kg")
add("convert 2 cups to ml", "convert_units", "2 cups to ml")
add("whats 98.6 f in celsius", "convert_units", "98.6 f to celsius")

# --- copy_file ---
add("copy resume.pdf to the documents folder", "copy_file", "resume.pdf")
add("can u duplicate my desktop notes.txt into archive", "copy_file", "notes.txt")
add("make a copy of vacation.jpg in pictures", "copy_file", "vacation.jpg")
add("copy the invoices folder over to backup", "copy_file", "invoices")

# --- cpu_load ---
add("how busy is the cpu rn", "cpu_load", "")
add("check the processor load", "cpu_load", "")
add("is my mac struggling, check cpu", "cpu_load", "")
add("cpu load average pls", "cpu_load", "")

# --- crop_square ---
add("crop headshot.jpg to a square", "crop_square", "headshot.jpg")
add("can u make profile.png a centered square", "crop_square", "profile.png")
add("square crop this: banner.jpg", "crop_square", "banner.jpg")
add("chop event-photo.png into a square shape", "crop_square", "event-photo.png")

# --- current_date ---
add("whats todays date", "current_date", "")
add("what day is it", "current_date", "")
add("remind me what the date is", "current_date", "")
add("todays date and day of week pls", "current_date", "")

# --- current_tab ---
add("whats the tab im on in chrome", "current_tab", "")
add("what page am i currently looking at", "current_tab", "")
add("check the title of my active tab", "current_tab", "")
add("whats this chrome tab called", "current_tab", "")

# --- dark_mode ---
add("turn on dark mode", "dark_mode", "on")
add("switch to light mode pls", "dark_mode", "off")
add("toggle dark mode for me", "dark_mode", "toggle")
add("can u flip the mac into dark theme", "dark_mode", "on")

# --- date_math ---
add("whats the date 100 days from now", "date_math", "100 days from now")
add("what date was it 3 weeks ago", "date_math", "3 weeks ago")
add("2 months after january 31 2026, whats that date", "date_math", "2 months after 2026-01-31")
add("count forward 45 days from today", "date_math", "45 days from now")

# --- days_until ---
add("how many days til christmas", "days_until", "christmas")
add("days left until dec 25 2026", "days_until", "2026-12-25")
add("hows far away is halloween", "days_until", "halloween")
add("countdown to new years pls", "days_until", "new year")

# --- disk_space ---
add("how much disk space do i have left", "disk_space", "")
add("check free storage on this mac", "disk_space", "")
add("am i running out of disk space", "disk_space", "")
add("disk space check pls", "disk_space", "")

# --- do_not_disturb ---
add("turn on do not disturb", "do_not_disturb", "on")
add("switch off dnd for me", "do_not_disturb", "off")
add("enable do not disturb mode", "do_not_disturb", "on")
add("can u turn do not disturb off", "do_not_disturb", "off")

# --- enhance_image ---
add("enhance the colors on sunset.jpg", "enhance_image", "sunset.jpg")
add("can u auto improve this photo: dog.png", "enhance_image", "dog.png")
add("make wedding-pic.jpg look better automatically", "enhance_image", "wedding-pic.jpg")
add("boost contrast on old-scan.png", "enhance_image", "old-scan.png")

# --- find_file ---
add("find resume.docx for me", "find_file", "resume.docx")
add("wheres that pdf called taxes2025", "find_file", "taxes2025")
add("search for a file named budget", "find_file", "budget")
add("can u locate my presentation.pptx", "find_file", "presentation.pptx")

# --- find_in_document ---
add("find milk in the document notes.pdf", "find_in_document", "milk")
add("does contract.pdf mention 'non-compete' anywhere", "find_in_document", "non-compete")
add("search report.docx for the word revenue", "find_in_document", "revenue")
add("look for 'termination' inside lease.pdf", "find_in_document", "termination")

# --- flip_coin ---
add("flip a coin for me", "flip_coin", "")
add("heads or tails, decide for us", "flip_coin", "")
add("coin flip pls", "flip_coin", "")
add("can u toss a coin to settle this", "flip_coin", "")

# --- flip_image ---
add("flip logo.png horizontally", "flip_image", "logo.png")
add("mirror this image vertically: portrait.jpg", "flip_image", "portrait.jpg vertical")
add("can u flip banner.png the other way", "flip_image", "banner.png")
add("vertical flip on photo.png pls", "flip_image", "photo.png vertical")

# --- folder_size ---
add("how big is my movies folder", "folder_size", "Movies")
add("check the size of ~/Downloads", "folder_size", "Downloads")
add("whats the total size of my photos folder", "folder_size", "photos")
add("how much space does documents take up", "folder_size", "documents")

# --- free_when ---
add("am i free thursday afternoon", "free_when", "Thursday afternoon")
add("when am i free this week", "free_when", "this week")
add("got any open slots tomorrow", "free_when", "tomorrow")
add("whens a good gap in my calendar today", "free_when", "today")

# --- git_status ---
add("git status of nimble", "git_status", "nimble")
add("check if cadence has uncommitted changes", "git_status", "cadence")
add("whats the branch status on turing", "git_status", "turing")
add("is talli ahead or behind on git", "git_status", "talli")

# --- grayscale_image ---
add("make photo.jpg black and white", "grayscale_image", "photo.jpg")
add("grayscale this pic: family.png", "grayscale_image", "family.png")
add("can u desaturate headshot.jpg", "grayscale_image", "headshot.jpg")
add("strip the color out of banner.png", "grayscale_image", "banner.png")

# --- hash_text ---
add("give me the sha256 of 'password123'", "hash_text", "password123")
add("hash the string hello world", "hash_text", "hello world")
add("what's the checksum of my api key text abc123", "hash_text", "abc123")
add("sha-256 this for me: turing", "hash_text", "turing")

# --- image_info ---
add("whats the resolution of banner.png", "image_info", "banner.png")
add("check dimensions on photo.jpg", "image_info", "photo.jpg")
add("how many layers does design.psd have", "image_info", "design.psd")
add("image info for logo.png pls", "image_info", "logo.png")

# --- ip_address ---
add("whats my ip address", "ip_address", "")
add("check this macs local ip", "ip_address", "")
add("whats my network address", "ip_address", "")
add("ip pls", "ip_address", "")

# --- is_prime ---
add("is 97 a prime number", "is_prime", "97")
add("check if 143 is prime", "is_prime", "143")
add("is 2027 prime or not", "is_prime", "2027")
add("factor 91 if its not prime", "is_prime", "91")

# --- json_pretty ---
add("pretty print this json: {\"a\":1,\"b\":2}", "json_pretty", "{\"a\":1,\"b\":2}")
add("can u tidy up this messy json string", "json_pretty", "json")
add("format this json so its readable", "json_pretty", "json")
add("indent this json blob for me", "json_pretty", "json")

# --- list_dir ---
add("list whats in my downloads folder", "list_dir", "Downloads")
add("show me the files in ~/Desktop", "list_dir", "Desktop")
add("whats inside the documents folder", "list_dir", "Documents")
add("ls the projects directory", "list_dir", "projects")

# --- list_mcp_tools ---
add("what mcp tools do you have access to", "list_mcp_tools", "")
add("list the other servers you can call", "list_mcp_tools", "")
add("show me your mcp tool list", "list_mcp_tools", "")
add("what external tools are hooked up to you", "list_mcp_tools", "")

# --- list_reminders ---
add("whats on my reminders list", "list_reminders", "")
add("show me my incomplete reminders", "list_reminders", "")
add("any reminders about groceries", "list_reminders", "groceries")
add("what do i still need to do, reminders", "list_reminders", "")

# --- list_shortcuts ---
add("what shortcuts do i have on this mac", "list_shortcuts", "")
add("show me the apple shortcuts list", "list_shortcuts", "")
add("list my shortcuts app stuff", "list_shortcuts", "")
add("what automations are set up in shortcuts", "list_shortcuts", "")

# --- list_tabs ---
add("what tabs do i have open in chrome", "list_tabs", "")
add("list all my browser tabs", "list_tabs", "")
add("how many chrome tabs are open rn", "list_tabs", "")
add("show me whats open in the browser", "list_tabs", "")

# --- make_logo ---
add("make me a logo for turing", "make_logo", "turing")
add("design a simple icon for my app called flow", "make_logo", "flow")
add("i need a complex logo for a coffee brand", "make_logo", "coffee")
add("can u draw an icon for my startup, keep it minimal", "make_logo", "startup")

# --- make_password ---
add("generate a password for me, 16 characters", "make_password", "16")
add("i need a random password 24 chars long", "make_password", "24")
add("make me a strong password pls", "make_password", "")
add("give me a throwaway password, like 12 chars", "make_password", "12")

# --- make_uuid ---
add("give me a random uuid", "make_uuid", "")
add("generate a uuid for this record", "make_uuid", "")
add("i need a unique id, make one", "make_uuid", "")
add("uuid pls", "make_uuid", "")

# --- memory_usage ---
add("how much ram do i have free", "memory_usage", "")
add("check memory usage on this mac", "memory_usage", "")
add("is my ram maxed out", "memory_usage", "")
add("memory status pls", "memory_usage", "")

# --- morse_code ---
add("write 'sos help' in morse code", "morse_code", "sos help")
add("morse code this for me: hello", "morse_code", "hello")
add("can u turn turing into morse", "morse_code", "turing")
add("translate 'call now' to morse", "morse_code", "call now")

# --- move_file ---
add("move resume.pdf to the documents folder", "move_file", "resume.pdf")
add("can u relocate vacation.jpg into pictures", "move_file", "vacation.jpg")
add("shift the invoices folder over to archive", "move_file", "invoices")
add("move old-notes.txt out of desktop into notes", "move_file", "old-notes.txt")

# --- music ---
add("play music", "music", "play")
add("pause the music", "music", "pause")
add("skip to the next song", "music", "next")
add("go back to the previous track", "music", "previous")

# --- needs_attention ---
add("whats needing my attention today", "needs_attention", "")
add("what do i need to deal with", "needs_attention", "")
add("anything urgent i should know about", "needs_attention", "")
add("catch me up on whats pending", "needs_attention", "")

# --- new_note ---
add("make a note called grocery list", "new_note", "grocery list")
add("take a note: buy milk", "new_note", "buy milk")
add("create a new note titled meeting ideas", "new_note", "meeting ideas")
add("jot down a note about the roadmap", "new_note", "roadmap")

# --- new_reminder ---
add("remind me tomorrow at 9am to call mom", "new_reminder", "call mom")
add("set a reminder to buy milk in 20 minutes", "new_reminder", "buy milk")
add("i need a reminder to pay rent on the 1st", "new_reminder", "pay rent")
add("remind me to pick up dry cleaning friday", "new_reminder", "dry cleaning")

# --- open_app ---
add("open spotify for me", "open_app", "spotify")
add("launch photoshop", "open_app", "photoshop")
add("can u open the calculator app", "open_app", "calculator")
add("fire up slack pls", "open_app", "slack")

# --- open_in_editor ---
add("open the nimble repo in vs code", "open_in_editor", "nimble")
add("can u pull up cadence in my editor", "open_in_editor", "cadence")
add("open turing folder in the code editor", "open_in_editor", "turing")
add("launch talli in vscode for me", "open_in_editor", "talli")

# --- open_prs ---
add("whats open on prs for nimble", "open_prs", "nimble")
add("check pull requests on cadence", "open_prs", "cadence")
add("any open prs in turing rn", "open_prs", "turing")
add("show me the pr list for talli", "open_prs", "talli")

# --- open_url ---
add("open google.com for me", "open_url", "google.com")
add("go to hacker news", "open_url", "hacker news")
add("pull up github in chrome", "open_url", "github")
add("open the site nimble.heyitsmejosh.com", "open_url", "nimble.heyitsmejosh.com")

# --- paint_image ---
add("paint mona.jpg out of little squares", "paint_image", "mona.jpg")
add("can u repaint this photo as a mosaic: cat.png", "paint_image", "cat.png")
add("turn sunset.jpg into a bunch of colored squares", "paint_image", "sunset.jpg")
add("do the square painting thing to portrait.png", "paint_image", "portrait.png")

# --- quit_app ---
add("quit spotify", "quit_app", "spotify")
add("close photoshop for me", "quit_app", "photoshop")
add("kill slack pls, its frozen", "quit_app", "slack")
add("can u shut down chrome", "quit_app", "chrome")

# --- random_number ---
add("give me a random number between 1 and 100", "random_number", "1 100")
add("pick a random number for me", "random_number", "")
add("random number between 5 and 20 pls", "random_number", "5 20")
add("roll a random int 1 to 10", "random_number", "1 10")

# --- read_document ---
add("read me the pdf on my desktop called notes.pdf", "read_document", "notes.pdf")
add("whats in contract.docx", "read_document", "contract.docx")
add("open up and read lease.pdf for me", "read_document", "lease.pdf")
add("can u read the rtf file called draft.rtf", "read_document", "draft.rtf")

# --- read_file ---
add("read the file config.txt", "read_file", "config.txt")
add("whats inside notes.md", "read_file", "notes.md")
add("open and read script.py for me", "read_file", "script.py")
add("can u show me whats in log.txt", "read_file", "log.txt")

# --- read_page ---
add("whats this page say, hacker news", "read_page", "hacker news")
add("read the article at example.com/api", "read_page", "example.com/api")
add("what does the current chrome tab say", "read_page", "")
add("check what nimble.heyitsmejosh.com says", "read_page", "nimble.heyitsmejosh.com")

# --- read_tab ---
add("read the current tab rendered as it looks", "read_tab", "")
add("what does the front tab actually show, its a js site", "read_tab", "")
add("read the js-heavy tab im on", "read_tab", "")
add("can u read tab 2 fully rendered", "read_tab", "2")

# --- recent_commits ---
add("show me the last commits on nimble", "recent_commits", "nimble")
add("whats the recent commit history for cadence", "recent_commits", "cadence")
add("recent commits in turing pls", "recent_commits", "turing")
add("check the last few commits on talli", "recent_commits", "talli")

# --- recent_downloads ---
add("what did i just download", "recent_downloads", "")
add("show me recent downloads", "recent_downloads", "")
add("whats new in my downloads folder", "recent_downloads", "")
add("check the latest files i grabbed off the net", "recent_downloads", "")

# --- remove_background ---
add("remove the background from headshot.jpg", "remove_background", "headshot.jpg")
add("can u cut out the bg on product.png", "remove_background", "product.png")
add("strip background out of logo.png", "remove_background", "logo.png")
add("make the background transparent on portrait.jpg", "remove_background", "portrait.jpg")

# --- rename_file ---
add("rename notes.txt to journal.txt", "rename_file", "notes.txt journal.txt")
add("can u call resume.pdf resume-final.pdf instead", "rename_file", "resume.pdf resume-final.pdf")
add("change the name of img001.png to vacation.png", "rename_file", "img001.png vacation.png")
add("rename draft.docx to proposal-v2.docx", "rename_file", "draft.docx proposal-v2.docx")

# --- research ---
add("research the history of the printing press", "research", "printing press")
add("can u dig into how vaccines work and give me a brief", "research", "vaccines")
add("look into the history of jazz for me", "research", "jazz")
add("research the docs at example.com/api", "research", "example.com/api")

# --- research_more ---
add("tell me more about that last thing you found", "research_more", "")
add("go deeper on that topic pls", "research_more", "")
add("expand on what you just researched", "research_more", "")
add("dig further into that same subject", "research_more", "")

# --- resize_image ---
add("resize banner.png to 1024 pixels", "resize_image", "banner.png 1024")
add("shrink photo.jpg down to 500px max side", "resize_image", "photo.jpg 500")
add("can u make logo.png smaller, like 256", "resize_image", "logo.png 256")
add("resize wallpaper.jpg to 2000", "resize_image", "wallpaper.jpg 2000")

# --- reveal_in_finder ---
add("show me resume.pdf in finder", "reveal_in_finder", "resume.pdf")
add("reveal the downloads folder in finder", "reveal_in_finder", "Downloads")
add("open finder to where notes.txt lives", "reveal_in_finder", "notes.txt")
add("can u pop up the projects folder in finder", "reveal_in_finder", "projects")

# --- reverse_text ---
add("reverse the word hello", "reverse_text", "hello")
add("flip this text backwards: turing", "reverse_text", "turing")
add("can u reverse 'good morning' for me", "reverse_text", "good morning")
add("write samantha backwards", "reverse_text", "samantha")

# --- roll_dice ---
add("roll 2d6 for me", "roll_dice", "2d6")
add("roll a d20", "roll_dice", "d20")
add("can u roll like 4 dice with 8 sides each", "roll_dice", "4d8")
add("dice roll pls, 3d6", "roll_dice", "3d6")

# --- roman_numeral ---
add("whats 44 in roman numerals", "roman_numeral", "44")
add("write 2026 as a roman numeral", "roman_numeral", "2026")
add("convert 9 into roman numerals", "roman_numeral", "9")
add("roman numeral for 1999 pls", "roman_numeral", "1999")

# --- rotate_image ---
add("rotate photo.jpg by 90 degrees", "rotate_image", "photo.jpg 90")
add("can u spin banner.png 180", "rotate_image", "banner.png 180")
add("turn logo.png sideways, 270 degrees", "rotate_image", "logo.png 270")
add("rotate this pic pls: img.png", "rotate_image", "img.png")

# --- run_code ---
add("stats on ~/Desktop/sales.csv", "run_code", "sales.csv")
add("whats the average of the price column in sales.csv", "run_code", "price")
add("chart sales.csv for me", "run_code", "sales.csv")
add("plot column price of sales.csv", "run_code", "price")

# --- run_tests ---
add("run turings tests", "run_tests", "turing")
add("can u run the test suite for nimble", "run_tests", "nimble")
add("test cadence and tell me if it passes", "run_tests", "cadence")
add("run the tests on talli pls", "run_tests", "talli")

# --- running_apps ---
add("what apps are open right now", "running_apps", "")
add("show me whats running", "running_apps", "")
add("which apps do i have open", "running_apps", "")
add("check running apps pls", "running_apps", "")

# --- save_research ---
add("save that research to a file", "save_research", "")
add("can u write that brief to my desktop", "save_research", "")
add("save the last thing you researched", "save_research", "")
add("put that research into a doc", "save_research", "")

# --- say ---
add("say 'good morning' out loud", "say", "good morning")
add("can u speak this text: dinner is ready", "say", "dinner is ready")
add("read this out loud for me: time to wake up", "say", "time to wake up")
add("say happy birthday out loud", "say", "happy birthday")

# --- screenshot ---
add("take a screenshot for me", "screenshot", "")
add("can u grab a screenshot of my screen", "screenshot", "")
add("screenshot this pls", "screenshot", "")
add("capture whats on screen rn", "screenshot", "")

# --- search_notes ---
add("search my notes for eggs", "search_notes", "eggs")
add("do i have a note about the mortgage", "search_notes", "mortgage")
add("find notes mentioning turing", "search_notes", "turing")
add("check notes for anything about the wedding", "search_notes", "wedding")

# --- set_volume ---
add("turn the volume up", "set_volume", "up")
add("set volume to 40", "set_volume", "40")
add("can u turn it down a bit", "set_volume", "down")
add("crank the volume to 100", "set_volume", "100")

# --- shout ---
add("shout this: we did it", "shout", "we did it")
add("make this all caps: hello there", "shout", "hello there")
add("can u shout 'lets go'", "shout", "lets go")
add("uppercase this text for me: good news", "shout", "good news")

# --- summarize ---
add("summarize the pdf report.pdf", "summarize", "report.pdf")
add("give me a quick summary of this page", "summarize", "")
add("summarize my unread mail", "summarize", "")
add("can u boil down notes.txt into a few sentences", "summarize", "notes.txt")

# --- switch_tab ---
add("switch to tab 2", "switch_tab", "2")
add("go to the gmail tab", "switch_tab", "gmail")
add("bring the hacker news tab to front", "switch_tab", "hacker news")
add("switch to tab 1.3", "switch_tab", "1.3")

# --- system_info ---
add("whats my mac running, macos version", "system_info", "")
add("check my system info", "system_info", "")
add("what chip does this mac have", "system_info", "")
add("give me the specs on this machine", "system_info", "")

# --- time_in ---
add("whats the time in tokyo", "time_in", "Tokyo")
add("current time in london pls", "time_in", "London")
add("what time is it right now here", "time_in", "")
add("check the time over in sydney", "time_in", "Sydney")

# --- timer ---
add("set a timer for 5 minutes", "timer", "5")
add("start a 90 second timer", "timer", "90 seconds")
add("can u time half an hour for me", "timer", "half an hour")
add("timer for 10 mins pls", "timer", "10")

# --- tip ---
add("whats a 20 percent tip on 85 bucks", "tip", "20 percent on 85")
add("work out the tip on a 42 dollar bill", "tip", "42")
add("calculate 15 18 and 20 percent tips on 60", "tip", "60")
add("how much should i tip on a $130 check", "tip", "130")

# --- transcribe_video ---
add("what is said in the video clip.mp4", "transcribe_video", "clip.mp4")
add("transcribe the audio file interview.m4a", "transcribe_video", "interview.m4a")
add("can u tell me whats spoken in meeting.mov", "transcribe_video", "meeting.mov")
add("what do people say in lecture.mp4", "transcribe_video", "lecture.mp4")

# --- translate ---
add("how do you say thank you in japanese", "translate", "thank you")
add("translate good morning to french", "translate", "good morning")
add("can u put 'where is the bathroom' into spanish", "translate", "where is the bathroom")
add("translate the page github.com into german", "translate", "github.com")

# --- trash_file ---
add("trash the file old-draft.txt", "trash_file", "old-draft.txt")
add("can u delete junk.png, send it to trash", "trash_file", "junk.png")
add("move oldbackup.zip to the trash", "trash_file", "oldbackup.zip")
add("get rid of duplicate.jpg pls", "trash_file", "duplicate.jpg")

# --- unread_mail ---
add("whats in my unread mail", "unread_mail", "")
add("anything from the bank in my inbox", "unread_mail", "bank")
add("check unread emails pls", "unread_mail", "")
add("do i have any unread mail from amazon", "unread_mail", "amazon")

# --- unzip_file ---
add("unzip archive.zip for me", "unzip_file", "archive.zip")
add("can u extract photos.zip", "unzip_file", "photos.zip")
add("unpack project.zip pls", "unzip_file", "project.zip")
add("open up backup.zip into a folder", "unzip_file", "backup.zip")

# --- upscale_image ---
add("upscale this photo: old-pic.jpg", "upscale_image", "old-pic.jpg")
add("can u increase the resolution on logo.png", "upscale_image", "logo.png")
add("make thumbnail.jpg bigger and sharper", "upscale_image", "thumbnail.jpg")
add("blow up small-photo.png in quality", "upscale_image", "small-photo.png")

# --- uptime ---
add("how long has this mac been on", "uptime", "")
add("whats my uptime", "uptime", "")
add("when did i last restart this thing", "uptime", "")
add("check system uptime pls", "uptime", "")

# --- weather ---
add("whats the weather like today", "weather", "")
add("check the weather in vancouver", "weather", "Vancouver")
add("is it gonna rain in london", "weather", "London")
add("weather in tokyo pls", "weather", "Tokyo")

# --- web_search ---
add("search the web for best pizza in vancouver", "web_search", "best pizza in vancouver")
add("how tall is mount everest", "web_search", "how tall is everest")
add("look up the population of japan", "web_search", "population of japan")
add("google who won the world series in 2025", "web_search", "world series 2025")

# --- word_count ---
add("how many words is this paragraph", "word_count", "")
add("count the words in this text: the quick brown fox", "word_count", "the quick brown fox")
add("whats the character count on my draft", "word_count", "")
add("word count this for me pls", "word_count", "")

# --- write_document ---
add("draft an email to the team about the release", "write_document", "release")
add("write a doc about the roadmap for me", "write_document", "roadmap")
add("can u draft a note explaining the new pricing", "write_document", "pricing")
add("write up a doc about our q3 plans", "write_document", "q3 plans")

# --- zip_file ---
add("zip up the invoices folder", "zip_file", "invoices")
add("can u compress notes.txt into a zip", "zip_file", "notes.txt")
add("make a zip of my photos folder", "zip_file", "photos")
add("archive project into a zip file pls", "zip_file", "project")

TOOL_COUNT = len({r["tool"] for r in ROWS})
print(f"tool rows: {len(ROWS)} across {TOOL_COUNT} tools", flush=True)


for t in NULLS:
    add(t, None, "")

with open("eval/heldout2.jsonl", "w") as f:
    for r in ROWS:
        f.write(json.dumps(r) + "\n")

print(f"total rows written: {len(ROWS)}")
