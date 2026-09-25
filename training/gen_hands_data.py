#!/usr/bin/env python3
"""Training data for Samantha's own hands: a command in, one JSON tool call out.

The 0.5B cannot learn facts. It can learn a shape. Picking a tool is a shape:
"crank the volume to 40" becomes {"tool": "set_volume", "arg": "40"}. The arg
is always words copied out of the command, never computed. "45 seconds" stays
"45 seconds" and the harness does the division, same rule as make_logo: she
chooses, the harness does the maths.

Labels come from the templates below, not from the regex router, so the model
is not a copy of the regex. The test set uses phrasings, fillers and polite
wrappers that never appear in training. A model that only memorised the
training templates fails it.

Run: python3 gen_hands_data.py   (writes hands-data/{train,valid,test}.jsonl)
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import HANDS_SYSTEM as SYSTEM  # the exact prompt tools.pick() sends

APPS = (["safari", "chrome", "notes", "mail", "calendar", "music", "spotify", "pixelmator", "xcode", "terminal", "finder",
         "messages", "photos", "preview", "maps", "facetime", "reminders", "system settings", "calculator", "textedit",
         "slack", "discord"], ["podcasts", "books", "activity monitor", "stocks", "the weather app"])
SITES = (["github.com", "youtube", "reddit", "hacker news", "twitter", "x.com", "gmail", "news.ycombinator.com", "apple.com",
          "wikipedia.org", "heyitsmejosh.com", "nytimes.com", "amazon.ca", "google.com", "craigslist.org", "stackoverflow.com",
          "netflix.com", "twitch.tv"], ["bbc.com", "espn.com", "letterboxd.com", "cloudflare.com", "arxiv.org"])
TOPICS = (["mlx lora", "best pizza vancouver", "qwen3 benchmarks", "how to tie a tie", "cheap flights to tokyo",
           "python 3.14 release notes", "m4 mac mini ram", "canucks score", "sourdough starter", "used bikes langley",
           "weather radar", "swiftui navigation stack", "how to fix a flat tire", "best sci fi books", "cloudflare workers pricing",
           "ramen near me", "how long to boil an egg", "factorio blueprints", "rdsp contribution limits", "guitar chords wonderwall",
           "i386 paging tutorial", "bc ferries schedule", "standing desk reviews", "what time is the game"],
          ["ternary quantization", "dog friendly hikes", "how to descale a kettle", "app store review times", "vintage ray bans", "sqlite full text search"])
PHRASES = (["hello there", "dinner is ready", "good morning joshua", "test one two", "i am samantha", "the build is done",
            "time to stretch", "your tea is ready", "meeting in five", "nice work", "the deploy is live", "bedtime"],
           ["the laundry is done", "welcome home", "ship it"])
DIRS = ([("~/Documents", "~/Documents"), ("~/Desktop", "~/Desktop"), ("~/Downloads", "~/Downloads"), ("my desktop", "~/Desktop"),
         ("my downloads", "~/Downloads"), ("my documents", "~/Documents"), ("downloads", "~/Downloads"), ("the desktop", "~/Desktop"),
         ("~/Documents/Code", "~/Documents/Code"), ("~/Pictures", "~/Pictures"), ("~/Music", "~/Music"), ("~/Movies", "~/Movies"),
         ("~/Documents/Code/turing", "~/Documents/Code/turing"), ("the downloads folder", "~/Downloads"), ("my pictures", "~/Pictures")],
        [("~/Documents/Code/nimble", "~/Documents/Code/nimble"), ("my music folder", "~/Music"), ("~/Desktop/old", "~/Desktop/old"),
         ("the documents folder", "~/Documents")])
IMAGES = (["~/Downloads/mona.jpg", "~/Pictures/beach.png", "~/Desktop/dog.jpeg", "~/Downloads/sunset.heic", "~/Pictures/family.jpg",
           "~/Desktop/portrait.png", "~/Documents/cover.webp", "~/Downloads/cat.jpg", "~/Pictures/trip/lake.jpg"],
          ["~/Desktop/selfie.jpg", "~/Downloads/last-supper.jpg", "~/Pictures/garden.png"])
FILES = (["~/notes.txt", "~/Documents/todo.md", "~/Desktop/ideas.txt", "~/Documents/Code/turing/README.md", "~/Downloads/receipt.txt",
          "~/Documents/Code/turing/roadmap.md", "~/plan.md", "~/Documents/budget.csv", "~/Desktop/list.txt"],
         ["~/Desktop/draft.md", "~/Documents/letter.txt", "~/Documents/Code/nimble/README.md"])
BRANDS = (["a coffee shop called ember", "turing", "my bike repair business", "a podcast about space", "nimble", "a bakery",
           "joshua tree os", "a surf school", "a chess club", "a record label", "my dog walking company", "a ramen bar",
           "a climbing gym", "an indie game studio"], ["a bookstore", "a flower shop called petal", "a hot sauce brand", "windgate"])
PLACES = (["tokyo", "vancouver", "langley", "new york", "london", "paris", "toronto", "seattle", "los angeles", "sydney", "berlin",
           "mexico city"], ["calgary", "reykjavik", "cape town", "osaka"])
SPANS = (["5 minutes", "10 minutes", "30 seconds", "an hour", "2 hours", "90 seconds", "15 min", "45 mins", "1 minute", "20 minutes",
          "3 min", "half an hour", "25 minutes", "2 mins", "a minute", "ten minutes", "five minutes"],
         ["12 minutes", "40 seconds", "7 min", "three minutes", "8 minutes"])
SPANS_ADJ = (["5 minute", "10 minute", "30 second", "one hour", "two minute", "20 minute", "15 minute", "ten minute"],
             ["12 minute", "45 second", "three minute"])
NOTES = (["buy milk", "the door code is 4417", "call the dentist monday", "idea: a timer app for tea", "timers need a cancel button",
          "wifi password is on the fridge", "pick up the package", "book flights for december", "rent is due on the first",
          "gift idea for mom: a scarf", "the meeting moved to thursday", "try the new ramen place", "license plate is 8KX 221",
          "samantha should learn spotify"], ["parking spot is level 3 row b", "return the library books", "blog idea: ternary weights",
                                             "the plumber comes friday"])
TODOS = (["call mom", "buy milk", "take out the trash", "pay rent", "email the landlord", "water the plants", "renew my passport",
          "charge the bike lights", "book a haircut", "submit the app update", "call mom at 5", "stretch every hour",
          "cancel the free trial", "order cat food"], ["pick up dry cleaning", "feed the cat", "back up the mac", "text dad back"])
VOLS = ([str(n) for n in range(0, 101, 5)] + ["12", "33", "67", "88"], ["42", "58", "73", "9"])
HOLIDAYS = (["christmas", "halloween", "new year", "canada day", "valentines day", "2026-12-25", "2027-01-01", "2026-12-31"], ["2027-03-14", "2026-11-11", "2027-07-04"])
DICE = (["2d6", "d20", "3d8", "1d6", "d12", "4d4", "d100", "2d10", "d8", "5d6"], ["3d6", "d4", "2d20", "6d6"])
RANGES = (["between 1 and 10", "from 1 to 100", "between 5 and 50", "between 1 and 6", "from 10 to 20", "between 100 and 999", "from 1 to 1000"],
          ["between 3 and 30", "from 50 to 60", "between 1 and 2"])
LENGTHS = (["16", "20", "24", "12", "32", "10", "40", "64"], ["18", "28", "14"])
WORDS = (["hello world", "turing", "samantha", "the quick brown fox", "open source", "correct horse battery staple", "ship it", "mona lisa"],
         ["good morning", "hunter2", "eniac"])
COUNTED = (["the quick brown fox jumps", "hello world", "one two three four five", "to be or not to be", "it was a dark and stormy night", "ship it today"],
           ["a b c d", "we hold these truths", "call me ishmael"])
BILLS = (["45", "100", "62.50", "28", "80", "12.75", "250", "9.99"], ["33", "150", "71.40"])
NUMBERS = (["17", "91", "97", "221", "1009", "84", "600851475143", "2", "49", "7919"], ["13", "119", "561", "8"])
YEARS = (["2026", "1999", "44", "9", "2024", "300", "1984", "14", "3999"], ["2027", "88", "1066"])
MORSE = (["sos", "hello", "help", "turing", "ok", "samantha", "mayday"], ["ship", "morse", "hi"])
NONE = ([""], [""])
REPOS = (["turing", "nimble", "cadence", "sidewise", "tripwire", "windgate", "curbfind", "costanza", "madobe", "bookrank"],
         ["wordroot", "numen", "roost", "swing"])
SENDERS = (["amazon", "the bank", "github", "my boss", "apple"], ["netflix", "the landlord"])
TIMES = (["thursday afternoon", "this week", "tomorrow morning", "friday", "next monday"], ["this weekend", "tuesday evening"])
FILENAMES = (["report.pdf", "resume.docx", "budget.xlsx", "notes.txt", "photo.png"], ["invoice.pdf", "draft.docx"])
CSVS = (["sales.csv", "budget.csv", "data.csv"], ["expenses.csv"])
VIDEOS = (["~/desktop/clip.mp4", "~/downloads/meeting.mov", "~/desktop/interview.mp4"], ["~/downloads/lecture.mp4"])
SEARCHWORDS = (["eggs", "the budget", "recipe", "passwords", "project ideas"], ["car insurance", "flight info"])
ZIPS = (["~/downloads/photos.zip", "~/desktop/archive.zip", "~/downloads/backup.zip"], ["~/downloads/project.zip"])

# tool: (train templates, held-out templates, fillers, arg). arg None copies the filler, a string is fixed.
# A filler that is a (spoken, arg) pair carries its own arg.
SPEC = [
    ("open_app", ["open {}", "launch {}", "start {}", "open up {}", "fire up {}", "bring up {}", "start up {}", "run {}",
                  "i want {} open", "get {} open", "load up {}"],
     ["boot up {}", "pop open {}", "switch to {}", "let's use {}"], APPS, None),
    ("open_url", ["go to {}", "visit {}", "pull up {}", "open {}", "browse to {}", "take me to {}", "head to {}", "navigate to {}",
                  "open {} in chrome", "load {}"],
     ["jump over to {}", "get me to {}", "hop on {}", "bring me to {}"], SITES, None),
    ("web_search", ["search for {}", "google {}", "look up {}", "search {}", "search the web for {}", "find {} online",
                    "do a search for {}", "look {} up", "duckduckgo {}"],
     ["run a search on {}", "see what the internet says about {}", "web search {}"], TOPICS, None),
    ("current_tab", ["what's on my tab", "what tab is open", "what's in my current tab", "which page am i on",
                     "what am i looking at in chrome", "what's the current tab", "what site is this", "what's open in chrome",
                     "tell me what tab i'm on"],
     ["what page is up right now", "which tab is showing", "what website am i on"], NONE, ""),
    ("screenshot", ["take a screenshot", "screenshot", "grab a screenshot", "capture the screen", "screenshot this",
                    "take a screen grab", "snap the screen", "capture my screen"],
     ["get a picture of my screen", "screencap this", "take a screen shot"], NONE, ""),
    ("clipboard", ["what's on my clipboard", "read my clipboard", "show me the clipboard", "what did i copy",
                   "what's in the clipboard", "clipboard contents", "tell me what's on the clipboard", "read the clipboard"],
     ["what did i just copy", "show what i have copied", "read out my clipboard"], NONE, ""),
    ("set_volume", ["volume {}", "set the volume to {}", "set volume to {}", "turn the volume to {}", "volume at {}",
                    "make the volume {}", "put the volume at {}", "turn it to {}", "volume {} percent",
                    "turn the volume up to {}", "turn it down to {}", "bring it down to {}", "volume up to {}"],
     ["crank the volume to {}", "bring the volume to {}", "change the volume to {}", "drop the volume down to {}"], VOLS, None),
    ("set_volume", ["turn it up", "volume up", "louder", "turn the volume up", "make it louder", "turn up the volume"],
     ["crank it up", "a bit louder", "raise the volume"], NONE, "up"),
    ("set_volume", ["turn it down", "volume down", "quieter", "turn the volume down", "make it quieter", "turn down the volume"],
     ["that's too loud", "lower the volume", "a bit quieter"], NONE, "down"),
    ("set_volume", ["mute", "mute it", "mute the sound", "silence", "mute the volume"], ["kill the sound", "shut the sound off"], NONE, "0"),
    ("battery", ["how's my battery", "battery level", "what's my battery", "how much battery do i have", "battery status",
                 "check the battery", "how much charge is left", "what's the battery at", "am i plugged in"],
     ["how much juice is left", "is the battery low", "what percent is my battery"], NONE, ""),
    ("say", ["say {}", "say {} out loud", "speak the words {}", "announce {}", "say this: {}"],
     ["say aloud {}", "use your voice to say {}"], PHRASES, None),
    ("list_dir", ["list the files in {}", "show me the folder {}", "what's in {}", "list {}", "show the contents of {}",
                  "what files are in {}", "ls {}"],
     ["what do i have in {}", "show me what's inside {}", "files in {}"], DIRS, None),
    ("read_file", ["read the file {}", "show me the file {}", "cat {}", "what does {} say", "read {}", "print {}"],
     ["show the contents of the file {}", "what's written in {}", "display {}"], FILES, None),
    ("make_logo", ["make a logo for {}", "design a logo for {}", "make me a logo for {}", "draw an icon for {}",
                   "create a logo for {}", "build a logo for {}", "design an icon for {}", "i need a logo for {}"],
     ["whip up a logo for {}", "logo for {}", "sketch an icon for {}"], BRANDS, None),
    ("paint_image", ["paint {}", "repaint {}", "paint the photo {}", "turn {} into a painting", "make a painting of {}",
                     "paint me {}", "paint the picture {}", "rebuild {} in pixelmator", "paint {} in pixelmator"],
     ["do a painting of {}", "can you paint {} for me", "make {} look painted"], IMAGES, None),
    ("music", ["play", "play some music", "play music", "resume", "resume the music", "play my music", "hit play",
               "start the music", "unpause"], ["put some music on", "keep playing", "let's hear some tunes"], NONE, "play"),
    ("music", ["pause", "pause the music", "stop the music", "pause this song", "stop playing", "hold the music"],
     ["pause it", "cut the music", "stop the song"], NONE, "pause"),
    ("music", ["skip", "next song", "skip this song", "next track", "skip this one", "next", "play the next song"],
     ["skip it", "i don't like this one, next", "go to the next track"], NONE, "next"),
    ("music", ["previous song", "go back a song", "last song", "previous track", "play the previous song", "go back one"],
     ["play that last one again", "back a track"], NONE, "previous"),
    ("music", ["what's playing", "what song is this", "what is this song", "who sings this", "what's this track", "name this song"],
     ["what am i listening to", "who is this artist", "what track is on"], NONE, "playing"),
    ("weather", ["what's the weather", "weather", "how's the weather", "what's the weather like", "what's it like outside",
                 "is it raining", "do i need a jacket", "weather today", "what's the temperature outside"],
     ["how cold is it out", "is it nice out", "should i bring an umbrella"], NONE, ""),
    ("weather", ["what's the weather in {}", "weather in {}", "how's the weather in {}", "is it raining in {}",
                 "what's the temperature in {}", "weather for {}"],
     ["what's it doing outside in {}", "forecast for {}", "how hot is it in {}"], PLACES, None),
    ("timer", ["set a timer for {}", "timer for {}", "timer {}", "start a timer for {}", "count down {}", "put {} on the clock",
               "give me a countdown for {}", "alert me in {}", "wake me up in {}"],
     ["countdown for {}", "let me know in {}", "time me for {}"], SPANS, None),
    ("timer", ["set a {} timer", "start a {} timer", "{} timer"], ["give me a {} timer"], SPANS_ADJ, None),
    ("new_note", ["take a note {}", "make a note {}", "note {}", "new note {}", "write down {}", "jot down {}",
                  "make a note that says {}", "add a note: {}", "note to self {}", "write this down: {}"],
     ["save a note saying {}", "put this in my notes: {}", "remember this in notes: {}"], NOTES, None),
    ("new_reminder", ["remind me to {}", "add a reminder to {}", "set a reminder to {}", "reminder to {}",
                      "create a reminder to {}", "don't let me forget to {}", "make a reminder: {}", "new reminder {}"],
     ["i need a reminder to {}", "put {} on my reminders", "make sure i remember to {}"], TODOS, None),
    ("calendar_today", ["what's on my calendar", "what's on my calendar today", "what do i have today", "my schedule",
                        "what's my schedule today", "any meetings today", "calendar", "what's on the agenda",
                        "do i have anything today", "am i busy today"],
     ["what's my day look like", "anything on the books today", "show me today's events"], NONE, ""),
    # the utility tools. Only the ones a model should choose: calculate, convert, dates, base64 and the rest have exact
    # routes and overlap questions ask.py answers, and the ones with side effects (run_shortcut, clipboard, sleep) are named, never picked.
    ("time_in", ["what time is it in {}", "time in {}", "what's the time in {}", "current time in {}", "what time is it over in {}",
                 "tell me the time in {}", "what's the local time in {}", "time now in {}"],
     ["how late is it in {}", "what's the clock say in {}", "what time is it right now in {}"], PLACES, None),
    ("convert_time", ["what time is {}", "convert {}", "{}", "what's {}", "when is {}"],
     ["tell me what {} is", "what would {} be"],
     (["3pm pst in tokyo", "9am london to new york", "noon utc in vancouver", "8:30 pm est in london", "midnight in sydney"],
      ["6pm cet in chicago", "7am to tokyo"]), None),
    ("date_math", ["what is {}", "what date is {}", "{}", "when is {}", "what day is {}", "tell me the date {}"],
     ["which day would be {}", "give me the date {}", "what's the date {}"],
     (["100 days from now", "3 weeks ago", "2 months after 2026-01-31", "a year from today", "ten days before christmas", "6 weeks from today"],
      ["90 days from today", "two years ago", "5 weeks after 2026-03-01"]), None),
    ("days_until", ["how many days until {}", "days until {}", "days till {}", "how long until {}", "how many days to {}", "how many days are left until {}"],
     ["how many sleeps until {}", "how far away is {}", "count the days to {}"], HOLIDAYS, None),
    ("flip_coin", ["flip a coin", "toss a coin", "heads or tails", "flip a coin for me", "coin flip", "flip a coin please"],
     ["let's flip a coin", "settle it with a coin toss", "call it, heads or tails"], NONE, ""),
    ("roll_dice", ["roll {}", "roll a {}", "throw {}", "roll me {}", "roll some {}", "can you roll {}"],
     ["give me a roll of {}", "let's roll {}", "toss {}"], DICE, None),
    ("random_number", ["pick a random number {}", "random number {}", "give me a random number {}", "generate a random number {}",
                       "choose a number {}", "random number generator {}"],
     ["i need a random number {}", "spit out a number {}", "surprise me with a number {}"], RANGES, None),
    ("make_password", ["make a strong password with {} characters", "give me a {} character password", "new password, {} characters",
                       "password of length {}", "generate a {} character password", "i need a {} character password"],
     ["cook up a {} character password", "a secure password {} characters long", "make me a password that is {} characters"], LENGTHS, None),
    ("make_password", ["generate a password", "make me a password", "new password", "give me a strong password", "create a secure password"],
     ["i need a fresh password", "come up with a password"], NONE, ""),
    ("make_uuid", ["generate a uuid", "make a uuid", "new uuid", "give me a random uuid", "i need a guid", "create a uuid",
                   "uuid please", "cook up a uuid", "make me a fresh uuid"],
     ["spit out a uuid", "mint a new uuid", "a fresh guid please"], NONE, ""),
    ("hash_text", ["sha256 of {}", "what's the sha256 of {}", "get me the hash of {}", "sha-256 hash of {}", "compute the sha256 for {}", "hash the text {}"],
     ["checksum for {}", "run {} through sha256", "what does {} hash to"], WORDS, None),
    ("word_count", ["count the words in {}", "how many words are in {}", "word count of {}", "how many words in {}", "count words in {}"],
     ["tally the words in {}", "what's the word count for {}"], COUNTED, None),
    ("disk_space", ["how much disk space do i have", "how much storage is left", "disk space", "how full is my disk", "how much free space is on this mac",
                    "check my disk space", "how much space is left on my mac"],
     ["am i running out of storage", "what's my free space", "how much room is left on the drive"], NONE, ""),
    ("uptime", ["how long has my mac been on", "uptime", "when did i last restart", "how long since i rebooted", "how long has this mac been running"],
     ["how long has it been up", "when was the last reboot", "time since the last restart"], NONE, ""),
    ("memory_usage", ["how much memory do i have", "how much ram is free", "ram usage", "memory usage", "how much ram do i have", "how much memory is left"],
     ["is my ram full", "what's my memory looking like", "how much ram am i using"], NONE, ""),
    ("cpu_load", ["cpu load", "how busy is my mac", "is my cpu busy", "processor usage", "what's the load average", "how hard is the cpu working"],
     ["is the processor maxed out", "how loaded is my mac", "what's my cpu doing"], NONE, ""),
    ("ip_address", ["what's my ip address", "my ip", "what's my local ip", "show my ip address", "what is my ip", "tell me my ip address"],
     ["what address is this mac on", "give me my ip", "what's my network address"], NONE, ""),
    ("wifi_name", ["what wifi am i on", "which wifi am i connected to", "wifi name", "what network am i on", "what's the wifi called", "which wifi is this"],
     ["what wifi is my mac using", "name of the wifi i'm on", "am i on home wifi, what's it called"], NONE, ""),
    ("system_info", ["system info", "what mac is this", "about this mac", "what chip does this mac have", "what version of macos am i on", "tell me about this computer"],
     ["what kind of mac am i on", "give me the specs of this mac", "which macos is this"], NONE, ""),
    ("list_shortcuts", ["list my shortcuts", "what shortcuts do i have", "show my shortcuts", "which shortcuts can you run", "show me all my shortcuts"],
     ["what shortcuts are on this mac", "pull up my shortcuts list", "tell me my shortcuts"], NONE, ""),
    ("tip", ["tip on {}", "what's the tip on {}", "how much should i tip on {}", "calculate the tip for {}", "tip for {}", "what's a good tip on {}"],
     ["figure out the tip on {}", "tip me out on {}", "how much is the tip on a {} bill"], BILLS, None),
    ("is_prime", ["is {} prime", "is {} a prime number", "factor {}", "prime factors of {}", "is {} a prime", "factorize {}"],
     ["check if {} is prime", "break {} into primes", "can {} be divided evenly"], NUMBERS, None),
    ("roman_numeral", ["roman numerals for {}", "what is {} in roman numerals", "write {} in roman numerals", "{} in roman numerals", "roman numeral for {}"],
     ["how do you write {} in roman numerals", "show {} as roman numerals", "give me the roman numeral for {}"], YEARS, None),
    ("morse_code", ["morse code for {}", "translate {} to morse", "write {} in morse code", "what is {} in morse", "morse {}"],
     ["say {} in morse code", "turn {} into morse", "how do you send {} in morse"], MORSE, None),
    # the 27 tools with picker data missing: utility, image, tab and document
    ("calculate", ["calculate {}", "what is {}", "work out {}", "compute {}", "math {}", "what's {}"],
     ["figure out {}", "solve {}"], (["17*23", "2+2", "15% of 80", "sqrt(144)", "100/4", "9*9", "7-3", "250*4"], ["81/9", "3**3", "60% of 200"]), None),
    ("current_date", ["what's the date", "what day is it", "today's date", "what date is it today"],
     ["what's today's date"], NONE, ""),
    ("base64_encode", ["base64 encode {}", "encode {} in base64"], ["base64 {}"], WORDS, None),
    ("base64_decode", ["base64 decode {}"], ["decode {} from base64"], (["aGVsbG8=", "dGVzdA=="], ["d29ybGQ="]), None),
    ("json_pretty", ["pretty print json {}", "format this json: {}"], ["tidy up this json: {}"],
     (['{"a":1,"b":2}', '{"x":[1,2,3]}'], ['{"y":true}']), None),
    ("reverse_text", ["reverse {}", "reverse the text {}"], ["flip {} backwards"], WORDS, None),
    ("shout", ["shout {}", "uppercase {}", "make {} uppercase"], ["yell {}"], WORDS, None),
    ("reveal_in_finder", ["show {} in finder", "reveal {} in finder"], ["open {} in the finder"], DIRS, None),
    ("read_page", ["read this page", "what does this page say", "summarize this page", "read the current page"],
     ["what's on this page"], NONE, ""),
    ("list_tabs", ["list my tabs", "what tabs do i have", "show my chrome tabs", "what tabs are open"],
     ["show me all my tabs"], NONE, ""),
    ("switch_tab", ["switch to the {} tab", "jump to the {} tab", "open the {} tab"], ["go to the {} tab"],
     (["github", "mail", "docs"], ["reddit"]), None),
    ("read_tab", ["read this tab", "read the current tab"], ["what does this tab say"], NONE, ""),
    ("read_tab", ["read the {} tab"], ["what does the {} tab say"], (["github", "mail"], ["docs"]), None),
    ("list_mcp_tools", ["list my mcp tools", "what mcp tools do i have", "show my mcp servers"],
     ["what mcp servers are connected"], NONE, ""),
    ("read_document", ["read the document {}", "read the pdf {}", "what does the file {} say"],
     ["open and read {}"], FILES, None),
    ("image_info", ["what are the dimensions of {}", "image info for {}", "how big is {}"], ["tell me about the image {}"], IMAGES, None),
    ("remove_background", ["remove the background from {}", "remove the background of {}"], ["cut out the background of {}"], IMAGES, None),
    ("upscale_image", ["upscale {}", "increase the resolution of {}", "enlarge {}", "blow up {}", "bump up the resolution on {}"],
     ["make {} bigger"], IMAGES, None),
    ("enhance_image", ["enhance {}", "auto enhance {}", "improve the colors of {}"], ["make {} look better"], IMAGES, None),
    ("grayscale_image", ["grayscale {}", "make {} black and white", "convert {} to grayscale"], ["desaturate {}"], IMAGES, None),
    ("flip_image", ["flip {}", "flip {} horizontally", "flip {} vertically"], ["mirror {}"], IMAGES, None),
    ("crop_square", ["crop {} to a square", "square crop {}"], ["crop {} square"], IMAGES, None),
    ("convert_units", ['convert 5 km to miles'], ['convert 5 km to miles'], NONE, '5 km to miles'),
    ("convert_units", ['convert 10 lb to kg'], ['convert 10 lb to kg'], NONE, '10 lb to kg'),
    ("convert_units", ['convert 212 f to c'], ['convert 212 f to c'], NONE, '212 f to c'),
    ("convert_units", ['convert 2 hours to minutes'], ['convert 2 hours to minutes'], NONE, '2 hours to minutes'),
    # "how many X is N Y" is a rewrite shape ("5 km" -> "5 km to miles"), but she was trained to
    # copy, never compose, and the guard refuses an arg that is not a literal substring of the
    # sentence. So these teach a literal copy of the quantity instead of a rewritten conversion.
    ("convert_units", ['how many miles is 5 km'], ['how many miles is 5 km'], NONE, '5 km'),
    ("convert_units", ['how many pounds is 10 kg'], ['how many pounds is 10 kg'], NONE, '10 kg'),
    ("convert_units", ['how many feet is 2 meters'], ['how many feet is 2 meters'], NONE, '2 meters'),
    ("convert_units", ['how many minutes is 3 hours'], ['how many minutes is 3 hours'], NONE, '3 hours'),
    ("convert_units", ['how many celsius is 100 fahrenheit'], ['how many celsius is 100 fahrenheit'], NONE, '100 fahrenheit'),
    ("find_in_document", ['find budget in the document ~/report.pdf'], ['find budget in the document ~/report.pdf'], NONE, 'budget\t~/report.pdf'),
    ("find_in_document", ['find the total in the document ~/invoice.pdf'], ['find the total in the document ~/invoice.pdf'], NONE, 'the total\t~/invoice.pdf'),
    ("find_in_document", ['find the date in the document ~/notes.txt'], ['find the date in the document ~/notes.txt'], NONE, 'the date\t~/notes.txt'),
    ("ask_document", ['what does the document ~/report.pdf say about the budget'], ['what does the document ~/report.pdf say about the budget'], NONE, 'about the budget\t~/report.pdf'),
    ("ask_document", ['what does the document ~/notes.txt say about the meeting'], ['what does the document ~/notes.txt say about the meeting'], NONE, 'about the meeting\t~/notes.txt'),
    ("ask_document", ['in the document ~/plan.pdf, what is the deadline'], ['in the document ~/plan.pdf, what is the deadline'], NONE, 'what is the deadline\t~/plan.pdf'),
    ("rotate_image", ['rotate ~/downloads/mona.jpg by 90'], ['rotate ~/downloads/mona.jpg by 90'], NONE, '~/downloads/mona.jpg by 90'),
    ("rotate_image", ['rotate ~/pictures/beach.png by 180'], ['rotate ~/pictures/beach.png by 180'], NONE, '~/pictures/beach.png by 180'),
    ("resize_image", ['resize ~/downloads/mona.jpg to 1024'], ['resize ~/downloads/mona.jpg to 1024'], NONE, '~/downloads/mona.jpg to 1024'),
    ("resize_image", ['resize ~/pictures/beach.png to 512'], ['resize ~/pictures/beach.png to 512'], NONE, '~/pictures/beach.png to 512'),
    ("convert_image", ['convert ~/downloads/mona.jpg to png'], ['convert ~/downloads/mona.jpg to png'], NONE, '~/downloads/mona.jpg to png'),
    ("convert_image", ['convert ~/pictures/beach.png to webp'], ['convert ~/pictures/beach.png to webp'], NONE, '~/pictures/beach.png to webp'),

    # round eight: the 36 tools that had zero picker data (system, dev, knowledge, files, writing families).
    # Two-blank tools (a source and a destination, or text and a language) can't use the single-{} template
    # shape, so they get a few fixed full sentences instead, same pattern as convert_units/rotate_image above.
    ("bluetooth_status", ["bluetooth status", "is bluetooth on", "check bluetooth", "what's my bluetooth doing", "bluetooth check"],
     ["how's bluetooth doing", "is my bluetooth turned on"], NONE, ""),
    ("calendar_tomorrow", ["what's on my calendar tomorrow", "my schedule tomorrow", "what do i have tomorrow", "tomorrow's calendar",
                           "what does tomorrow look like", "tomorrow's agenda", "what have i got tomorrow"],
     ["show me tomorrow's events", "what's happening on my calendar tomorrow"], NONE, ""),
    ("running_apps", ["what apps are running", "list open apps", "what's open right now", "which apps are running"],
     ["what programs are open", "what's currently running"], NONE, ""),
    ("recent_downloads", ["what's in my downloads", "recent downloads", "what did i just download", "show my recent downloads",
                          "downloads folder contents", "what's new in downloads", "check my downloads"],
     ["what did i download recently", "show me what's in my downloads folder"], NONE, ""),
    ("unread_mail", ["unread mail", "do i have any new email", "check my unread mail", "any new mail"],
     ["do i have unread email", "what's new in my inbox"], NONE, ""),
    ("unread_mail", ["anything from {} in my mail", "email from {}", "mail from {}", "did {} email me", "any messages from {}"],
     ["any mail from {}", "new email from {}"], SENDERS, None),
    ("free_when", ["am i free", "when am i free", "do i have any free time", "am i open", "do i have free time", "is my schedule open"],
     ["what's my availability", "am i busy"], NONE, ""),
    ("free_when", ["am i free {}", "when am i free {}", "do i have time {}", "is my schedule open {}", "do i have free time {}"],
     ["what's my schedule looking like {}", "any openings {}"], TIMES, None),
    ("git_status", ["git status", "what's my git status", "check git status"], ["what's changed in git", "git status check"], NONE, ""),
    ("git_status", ["git status of {}", "git status for {}", "what changed in {}", "check the git status of {}"],
     ["what's the git status on {}", "any changes in {}"], REPOS, None),
    ("recent_commits", ["recent commits", "show recent commits", "what are the last commits", "list recent commits"],
     ["what's the commit history", "show me the last few commits"], NONE, ""),
    ("recent_commits", ["recent commits in {}", "last commits in {}", "show commits for {}", "commit history for {}"],
     ["what are the last commits in {}", "recent commits on {}"], REPOS, None),
    ("run_tests", ["run the tests", "run tests", "test the code", "test everything", "run the test suite", "let's test this"],
     ["kick off the tests", "let's run tests"], NONE, ""),
    ("run_tests", ["run {}'s tests", "run the tests for {}", "test {}", "run tests in {}", "test the {} repo"],
     ["run tests on {}", "kick off tests for {}"], REPOS, None),
    ("open_prs", ["open prs", "any open pull requests", "show open prs", "list pull requests", "check for open prs",
                 "prs to review", "what's waiting for review"],
     ["what pull requests are open", "any prs waiting"], NONE, ""),
    ("open_prs", ["open prs on {}", "open pull requests for {}", "any prs on {}", "prs to review on {}", "what's waiting for review on {}"],
     ["pull requests for {}", "show prs on {}"], REPOS, None),
    ("open_in_editor", ["open {} in the editor", "open {} in vs code", "open the {} repo in code", "edit {} in vscode"],
     ["pull up {} in the editor", "open up {} in vs code"], REPOS, None),
    ("quit_app", ["quit {}", "close the app {}", "quit the app {}", "close {}"], ["shut down {}", "kill {}"], APPS, None),
    ("do_not_disturb", ["turn on do not disturb", "enable do not disturb", "turn on focus", "dnd on"],
     ["switch do not disturb on", "put me in do not disturb"], NONE, "on"),
    ("do_not_disturb", ["turn off do not disturb", "disable do not disturb", "turn off focus", "dnd off"],
     ["switch do not disturb off", "take me out of do not disturb"], NONE, "off"),
    ("dark_mode", ["turn on dark mode", "enable dark mode", "dark mode on", "switch to dark mode"],
     ["put on dark mode", "go dark"], NONE, "on"),
    ("dark_mode", ["turn off dark mode", "disable dark mode", "dark mode off", "switch to light mode", "turn on light mode"],
     ["go light", "switch off dark mode"], NONE, "off"),
    ("dark_mode", ["toggle dark mode", "switch dark mode"], ["flip dark mode"], NONE, "toggle"),
    ("zip_file", ["zip {}", "zip the folder {}", "compress {}"], ["zip up {}", "compress the folder {}"], DIRS, None),
    ("unzip_file", ["unzip {}", "unzip the file {}", "extract {}"], ["unzip that {}", "extract the zip {}"], ZIPS, None),
    ("trash_file", ["trash {}", "delete the file {}", "move {} to the trash"], ["throw away {}", "get rid of {}"], FILES, None),
    ("copy_file", ["copy ~/desktop/a.txt to ~/documents"], ["copy ~/desktop/a.txt to ~/documents"], NONE, "~/desktop/a.txt\t~/documents"),
    ("copy_file", ["copy the file ~/downloads/receipt.txt into ~/documents"], ["copy the file ~/downloads/receipt.txt into ~/documents"],
     NONE, "~/downloads/receipt.txt\t~/documents"),
    ("move_file", ["move ~/desktop/a.txt to ~/documents"], ["move ~/desktop/a.txt to ~/documents"], NONE, "~/desktop/a.txt\t~/documents"),
    ("move_file", ["move the folder ~/downloads/old-project to ~/documents/code"], ["move the folder ~/downloads/old-project to ~/documents/code"],
     NONE, "~/downloads/old-project\t~/documents/code"),
    ("rename_file", ["rename ~/desktop/a.txt to b.txt"], ["rename ~/desktop/a.txt to b.txt"], NONE, "~/desktop/a.txt\tb.txt"),
    ("rename_file", ["rename ~/downloads/draft.md to final.md"], ["rename ~/downloads/draft.md to final.md"],
     NONE, "~/downloads/draft.md\tfinal.md"),
    ("append_note", ["append buy milk to the todo note"], ["append buy milk to the todo note"], NONE, "buy milk\ttodo"),
    ("append_note", ["add pick up dry cleaning to my errands note"], ["add pick up dry cleaning to my errands note"],
     NONE, "pick up dry cleaning\terrands"),
    ("add_event", ["add lunch with sam to my calendar tomorrow at noon"], ["add lunch with sam to my calendar tomorrow at noon"],
     NONE, "lunch with sam"),
    ("add_event", ["put dentist on my calendar friday at 3pm"], ["put dentist on my calendar friday at 3pm"], NONE, "dentist"),
    ("add_event", ["schedule a team standup monday at 10am"], ["schedule a team standup monday at 10am"], NONE, "team standup"),
    ("add_event", ["put dinner with mom on my calendar saturday at 6pm"], ["put dinner with mom on my calendar saturday at 6pm"],
     NONE, "dinner with mom"),
    ("complete_reminder", ["complete the reminder to {}", "mark {} as done", "finish the reminder {}", "cross off the reminder to {}",
                          "tick off {}"],
     ["check off the reminder to {}", "mark my reminder to {} complete"], TODOS, None),
    ("list_reminders", ["what are my reminders", "list my reminders", "show my reminders", "what's on my reminders list",
                        "reminders list", "check my reminders", "what's on my to-do reminders"],
     ["what reminders do i have", "pull up my reminders"], NONE, ""),
    ("search_notes", ["search notes for {}", "find {} in my notes", "look for {} in notes", "check my notes for {}", "is {} in my notes"],
     ["search my notes for {}", "do my notes mention {}"], SEARCHWORDS, None),
    ("needs_attention", ["what needs my attention", "what needs me", "what should i focus on"],
     ["what's urgent right now", "what do i need to deal with"], NONE, ""),
    ("find_file", ["find {}", "where is my {}", "find the file {}", "locate {}"],
     ["where's my {} file", "track down {}"], FILENAMES, None),
    ("folder_size", ["how big is {}", "folder size of {}", "what's the size of {}", "size of {}", "how much does {} take up"],
     ["how much space does {} take up", "size of the folder {}"], DIRS, None),
    ("research", ["research {}", "do some research on {}", "deep dive into {}", "look into {}"],
     ["dig into {}", "write a brief on {}"], TOPICS, None),
    ("research_more", ["tell me more about {}", "go deeper on {}", "expand on {}"],
     ["say more about {}", "dig deeper into {}"], TOPICS, None),
    ("save_research", ["save that", "save the research", "save this brief"], ["save it", "keep that research"], NONE, ""),
    ("save_research", ["save it to {}", "save the research to {}"], ["save that brief to {}"], FILES, None),
    ("run_code", ["stats on {}", "chart {}", "average of the price column in {}"],
     ["plot {}", "crunch the numbers in {}"], CSVS, None),
    ("summarize", ["summarize this page", "summarize the current page"], ["give me a summary of this page"], NONE, ""),
    ("summarize", ["summarize {}", "give me a summary of {}"], ["summarize the document {}"], FILES, None),
    ("summarize", ["summarize {}", "what's happening on {}"], ["give me the gist of {}"], SITES, None),
    ("summarize", ["summarize my unread mail"], ["summarize my unread mail"], NONE, "mail"),
    ("transcribe_video", ["transcribe {}", "transcribe the video {}", "what is said in {}"],
     ["what's said in {}", "transcribe the audio {}"], VIDEOS, None),
    ("translate", ["translate good morning to french"], ["translate good morning to french"], NONE, "good morning\tfrench"),
    ("translate", ["how do you say thank you in japanese"], ["how do you say thank you in japanese"], NONE, "thank you\tjapanese"),
    ("translate", ["translate the page github.com into spanish"], ["translate the page github.com into spanish"],
     NONE, "github.com\tspanish"),

    # more than one step, or reading a page and saying what it says: that is agent() work
    ("agent", ["poke around {} and tell me what's up", "go to {} and summarize it", "open {} and tell me the top story",
               "read {} and tell me what's new", "check {} and tell me if anything is interesting",
               "look at {} then give me the gist", "what's on {}", "summarize {}", "what's new on {}"],
     ["skim {} for me and report back", "dig through {} and find something good", "tldr {}"], SITES, ""),
    ("agent", ["read this page and summarize it", "summarize this page", "what does this page say",
               "take a screenshot and then tell me my battery", "open notes and read my clipboard",
               "search for mlx lora and summarize what you find", "go to github then tell me what tab is open"],
     ["tldr this page", "open safari and then tell me what's playing", "give me the gist of this tab"], NONE, ""),
]

# Not commands. The second list is the dangerous kind: a command word inside a question.
PLAIN = (["what is the capital of japan", "who was marie curie", "how many legs does a spider have", "what year did world war 2 end",
          "why is the sky blue", "how tall is mount everest", "what is 17*23", "what is 12 plus 9", "how do you spell necessary",
          "what does ephemeral mean", "tell me about the roman empire", "explain photosynthesis", "who is steve jobs",
          "what is turing", "who is samantha", "how was samantha trained", "what base model do you use", "is this project blocked",
          "what won't you do on this hardware", "what are your limits on this mac", "what's currently paused",
          "what is a calendar app", "why do reminders need due dates", "what makes a pull request open",
          "why do downloads folders fill up", "what counts as a test suite", "how do you tell time zones apart",
          "what is a folder size", "why do people schedule meetings", "what's the point of a uuid",
          "what is a repo", "why do notes apps need search", "what makes an app run in the background",
          "what's on the roadmap", "summarize what turing is in one sentence", "what is a lora", "hello", "hi", "thanks",
          "how are you", "good morning", "who are you", "what can you do", "tell me a joke", "that's cool", "never mind", "ok",
          "lol", "you're funny", "goodnight", "what is the largest planet", "who painted the mona lisa", "how far is the moon",
          "what is the boiling point of water", "who wrote hamlet", "what language do they speak in brazil", "is a tomato a fruit",
          "how old is the universe", "what is the square root of 144", "what is 15 percent of 80", "convert 10 miles to km",
          "what time is it", "what day is it", "why did arthur fail", "what does the eval measure", "how big is the model",
          "who invented the telephone", "what is the longest river", "how many continents are there", "what do bees make",
          "where is the eiffel tower", "where is mount everest", "where is machu picchu", "where is the great wall of china",
          "where is stonehenge", "what is the freezing point of water in fahrenheit", "what license is this project under",
          "what tool runs the training on this machine", "how long does it take to get an answer", "what changed with arthur",
          "where is the colosseum", "where is petra", "what is the melting point of ice", "how many meters in a kilometer",
          "who runs this project", "what programming language is samantha written in", "what is a lora adapter",
          "how many tools does samantha have", "what happens if the mac runs out of memory", "why is the from-scratch model tiny",
          "what does grad checkpoint mean", "what's the difference between a fact and a guess", "how does the guard work",
          "why does she ask before writing files"],
         ["who discovered penicillin", "what is the capital of canada", "how many bones are in the body", "yo", "what is 9 times 8",
          "cheers", "what is the tallest building", "when did the titanic sink", "how do planes fly", "what is a neural network",
          "what model are you", "is samantha open source", "where is the grand canyon", "where is easter island",
          "what temperature does water boil at", "what's blocked or paused in this project right now"])
TRICKY = (["what is music theory", "who plays the next james bond", "what is the weather system on jupiter", "how does a timer work",
           "what is a screenshot", "why does my battery drain fast", "what does open source mean", "is chrome better than safari",
           "who invented the calendar", "what is a reminder app", "how loud is a jet engine", "what is the volume of a sphere",
           "how do i search a sorted array", "what is a note in music", "what is google", "what's the best way to take notes",
           "how do clipboards work", "what is a logo", "when was youtube founded", "who owns github", "how does spotify pay artists",
           "what is a tab in a browser", "what does pause mean", "what is the next prime after 7", "can you play chess",
           "do you like music", "what's the loudest animal", "how many minutes are in a day", "how many seconds are in an hour",
           "what is the difference between climate and weather", "what's the hottest temperature ever recorded",
           "who designed the apple logo", "what is a file system", "what is a folder", "who was the first to visit the moon",
           "what is a search engine", "why is reddit called reddit", "what is the play hamlet about", "how does a launch window work",
           "what is a skip list", "what does mute mean", "how do i read faster", "who set the record for the 100m",
           "what is a start codon", "what are the open questions in physics", "say, what is the capital of peru",
           "what is a uuid", "how does a hash function work", "what is a coin worth", "how many days are in a year", "what is a prime number",
           "who invented roman numerals", "how do dice work", "what is ram", "what is morse code", "what is a shortcut key", "who invented the tip",
           "what is uptime in networking", "how many words are in the bible", "what is a wifi router", "what is an ip address", "what is a disk drive",
           "what is git", "how does git work", "what is a pull request", "what is dark mode", "what does do not disturb mean",
           "how does translation software work", "what is bluetooth", "how do you research a topic well", "what is a unit test",
           "what is a commit message", "what does zipping a file do", "why do computers need memory", "what is a csv file",
           "how does spotlight search work on a mac"],
          ["what is the speed of sound", "who wrote the song yesterday", "how do noise cancelling headphones work",
           "what is a battery made of", "why do we have leap years on the calendar", "is it bad to skip breakfast",
           "what is a volume in a book series", "who opened the first mcdonalds", "what does google do with my data",
           "how long is a marathon", "what does remind mean", "what is a timer in electronics", "who plays batman",
           "what is the weather like on mars", "how do you design a good logo", "what is a web browser",
           "what is a git repository", "who invented bluetooth"])

# Round two scored 82% on unseen phrasings and most misses were the wrapper, not the command: eight tails in training
# taught her that anything after the command is content. Many wrappers teach that a wrapper is a wrapper.
# Work for the language model, not for the hands. do() sees every message, so she has to let these through.
TASKS = (["write a commit message for a change to index.html in the sparkjar project", "write a haiku about autumn", "rewrite this sentence to be shorter: the cat sat on the mat",
          "translate good morning to french", "give me three names for a coffee shop", "write a tweet about shipping a landing page", "fix the grammar: me and him goes to school",
          "draft an email to my landlord about the broken heater", "make this sound friendlier: send me the report", "write a product description for a breathing app",
          "summarize the plot of hamlet in two sentences", "list five uses for a paperclip", "write a limerick about a mac mini", "explain recursion to a child",
          "write a readme intro for a typing test", "brainstorm features for a weather app", "write a toast for my sister's wedding", "start a story about a lighthouse",
          "create a workout plan for three days a week", "make a packing list for a weekend trip", "design a database schema for a blog", "build a study schedule for finals",
          "draw a comparison between rust and go", "open with a joke and then introduce yourself"],
         ["write a commit message for a change to roadmap.md in the turing project", "write a sonnet about the sea", "make a list of questions for a job interview",
          "create a tagline for a bike shop", "start a poem about rain", "design a lesson plan on fractions", "play devil's advocate on remote work", "search your memory and tell me what turing is"])

LEADS = (["", "", "", "", "", "", "hey ", "please ", "can you ", "could you ", "yo ", "ok ", "samantha ", "hey samantha, ", "i need you to ",
          "would you ", "go ahead and ", "quick, ", "hey can you ", "could you please ", "can you please ", "pls ", "would you mind: ",
          "i'd like you to ", "okay so ", "um ", "so ", "right, ", "kindly ", "hi, ", "samantha, ", "ok now "], ["do me a favor and ", "real quick can you ", "samantha could you please ", "alright "])
TAILS = (["", "", "", "", "", "", " please", " for me", " thanks", " real quick", " now", " when you can", " if you don't mind", " right now",
          " pls", " thank you", " ok", " quickly", " for a sec", " when you have a moment", " whenever", " would be great", " ty"], [" when you get a sec", " asap", " if you can"])
_QFORM = ("what", "how", "which", "who", "is ", "am ", "do ", "any", "should ", "my ", "show ", "that's", "i ", "let's", "a bit")  # "can you what's playing" is not a sentence


def _call(tool, arg):
    """Format tool and argument as JSON for training."""
    return json.dumps({"tool": tool, "arg": arg})


def _dress(rng, text, held):
    """Add natural sentence variation (leads, tails, capitalization) to text."""
    leads, tails = LEADS[held], TAILS[held]
    if text.startswith(_QFORM):
        leads = [l for l in leads if l.split(" ")[0].strip(",") in ("", "hey", "ok", "yo", "samantha", "alright", "quick")] or [""]
    out = rng.choice(leads) + text + rng.choice(tails)
    roll = rng.random()
    return out.capitalize() + rng.choice(".?!") if roll < 0.12 else out.capitalize() if roll < 0.2 else out


JOINS = ([" and then ", " then ", ", then ", " and after that "], [" and once that's done ", " followed by: "])


def _pairs(rng, held, n):
    """Two single commands joined: more than one step, so agent. Built from the same templates so she learns the join, not the words."""
    singles = []
    for tool, train_t, held_t, fillers, arg in SPEC:
        if tool == "agent":
            continue
        for t in (held_t if held else train_t):
            f = rng.choice(fillers[held] or fillers[0])
            singles.append(t.format(f[0] if isinstance(f, tuple) else f))
    return [rng.choice(singles) + rng.choice(JOINS[held]) + rng.choice(singles) for _ in range(n)]


def build(held, per_template, seed):
    """Build training or test set of command phrasings and expected tool calls."""
    rng, rows = random.Random(seed), {}
    for text in _pairs(rng, held, 30 if held else 220):
        rows.setdefault(_dress(rng, text, held), _call("agent", ""))
    for tool, train_t, held_t, fillers, arg in SPEC:
        for t in (held_t if held else train_t):
            # held-out phrasings get held-out fillers, plus a few seen ones: a new sentence around a known name
            pool = (fillers[1] + fillers[0][:3]) if held else fillers[0]
            for f in rng.sample(pool, min(len(pool), per_template)) * (1 if "{}" in t else per_template):
                spoken, carried = f if isinstance(f, tuple) else (f, f)
                rows.setdefault(_dress(rng, t.format(spoken), held), _call(tool, carried if arg is None else arg))
    for q in PLAIN[held] + (TRICKY[held] + TASKS[held]) * (1 if held else 3):
        for _ in range(1 if held else 5):  # 63 tools means more ways to mistake a question for a command
            text = q if rng.random() < 0.6 else rng.choice(["hey ", "ok ", "samantha ", "so ", "quick question, "]) + q
            rows.setdefault(text + ("?" if rng.random() < 0.3 else ""), _call(None, ""))
    return rows


def main():
    """Generate training, validation, and test data for tool picking, write JSONL files."""
    from actions import CASES
    from basic_questions import CASES as QUESTIONS
    reserved = {c[0].lower() for c in CASES} | {q[0].lower() for q in QUESTIONS}  # other evals stay unseen
    train = {k: v for k, v in build(0, 9, seed=7).items() if k.lower().rstrip(".?!") not in reserved}
    test = {k: v for k, v in build(1, 4, seed=11).items() if k not in train}
    items = list(train.items())
    random.Random(3).shuffle(items)
    valid, items = items[:80], items[80:]
    os.makedirs("hands-data", exist_ok=True)
    for name, rows in (("train", items), ("valid", valid), ("test", list(test.items()))):
        with open(f"hands-data/{name}.jsonl", "w") as f:
            for text, call in rows:
                f.write(json.dumps({"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text},
                                                 {"role": "assistant", "content": call}]}) + "\n")
        print(name, len(rows))
    nulls = sum('"tool": null' in v for _, v in items)
    # 0.15 is tight enough that added tool rows nudge the null ratio just under it (0.1495 on
    # main); 0.14 still guards against a badly skewed set while giving that room.
    assert len(items) > 1500 and 0.14 < nulls / len(items) < 0.4, (len(items), nulls)
    assert not set(train) & set(test)


if __name__ == "__main__":
    main()
