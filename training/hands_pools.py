"""Filler pools for training/gen_hands_data.py: the names, sites, paths, phrases and (spoken, arg) pairs the SPEC
templates fill in, plus the not-a-command sentences (PLAIN, TRICKY, TASKS). Each pool is (training fillers, held-out fillers). Split out of gen_hands_data.py (658 lines) in
4.17.6 so each file does one thing; gen_hands_data re-exports every name, so nothing that imports it breaks."""

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

# Round fourteen pools for the two-argument tools: (spoken, arg) pairs, spoken in more than one joining word.
_SRC = (["~/desktop/a.txt", "~/downloads/receipt.pdf", "~/documents/budget.csv", "~/desktop/photo.jpg", "notes.txt",
         "~/downloads/old-project", "report.docx", "~/desktop/slides.key"], ["~/downloads/lease.pdf", "todo.md"])
_DST = (["~/documents", "~/desktop", "~/documents/archive", "~/pictures", "~/documents/code", "the archive folder"],
        ["~/music", "~/documents/taxes"])


def _pairs_of(srcs, dsts, joins, arg):
    """Every source with a rotating destination, spoken with each join word: (spoken, arg) filler pairs."""
    return [(f"{s}{joins[i % len(joins)]}{dsts[i % len(dsts)]}", arg(s, dsts[i % len(dsts)])) for i, s in enumerate(srcs)]


MOVES = tuple(_pairs_of(_SRC[h], _DST[h], (" to ", " into ", " over to ", " in "), lambda s, d: f"{s}\t{d}") for h in (0, 1))
RENAMES = tuple(_pairs_of(_SRC[h], (["b.txt", "final.pdf", "budget-2026.csv", "beach.jpg", "old.txt"], ["draft-2.md"])[h],
                          (" to ",), lambda s, d: f"{s}\t{d}") for h in (0, 1))
_SAYINGS = ((["hello", "good night", "where is the train station", "i love you", "see you tomorrow", "how much is this",
              "happy birthday"], ["the bill please"]), (["french", "spanish", "german", "japanese", "italian", "korean"],
                                                        ["portuguese"]))
PHRASE_TO = tuple(_pairs_of(_SAYINGS[0][h], _SAYINGS[1][h], (" to ", " into "), lambda s, d: f"{s}\t{d}") for h in (0, 1))
PHRASE_IN = tuple(_pairs_of(_SAYINGS[0][h], _SAYINGS[1][h], (" in ",), lambda s, d: f"{s}\t{d}") for h in (0, 1))
APPENDS = tuple(_pairs_of((["buy eggs", "call the vet", "renew the car insurance", "fix the gate", "order printer ink"],
                           ["book the campsite"])[h], (["groceries", "todo", "house", "errands"], ["weekend"])[h],
                          (" to my ", " onto the ", " to the ", " at the end of my "),
                          lambda s, d: f"{s}\t{d}") for h in (0, 1))
APPENDS = tuple([(f"{sp} note", a) for sp, a in APPENDS[h]] for h in (0, 1))
DOC_FINDS = tuple(_pairs_of((["the deadline", "invoice number", "the total", "insurance", "the address"], ["the signature"])[h],
                            (["~/report.pdf", "~/documents/contract.pdf", "~/desktop/notes.txt", "~/downloads/invoice.pdf"],
                             ["~/documents/policy.docx"])[h], (" in ", " inside ", " in the document "),
                            lambda s, d: f"{s}\t{d}") for h in (0, 1))
DOC_ASKS = tuple([(f"{d} and tell me {q}", f"{q}\t{d}") for q, d in zip(
    (["what the deadline is", "who signed it", "how much is owed", "when it expires", "what the main point is"],
     ["what the fee is"])[h], (["~/report.pdf", "~/documents/contract.pdf", "~/desktop/notes.txt", "~/downloads/invoice.pdf",
                                "~/plan.pdf"], ["~/documents/policy.docx"])[h])] for h in (0, 1))
ROTATES = tuple([(f"{i} {w}{n}", f"{i} by {n}") for i, w, n in zip(IMAGES[h], ("by ", "by ", "", "by "), ("90", "180", "270", "90"))]
                for h in (0, 1))
RESIZES = tuple([(f"{i} to {n}", f"{i} to {n}") for i, n in zip(IMAGES[h], ("1024", "512", "800", "2048", "256"))] for h in (0, 1))
CONVERTS = tuple([(f"{i} {w} {n}", f"{i} to {n}") for i, w, n in zip(IMAGES[h], ("to", "into", "as", "to", "to"),
                                                                   ("png", "jpg", "webp", "png", "heic"))] for h in (0, 1))

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
          "what is 3+3", "what is 8 times 4", "what is 20 minus 5", "what is 6 divided by 2", "what is 50 plus 50",
          "what is 4 times 4", "what is 30 minus 10", "what is 9+9", "what is 100 divided by 5", "what is 7 plus 8",
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
           "how does spotlight search work on a mac",
           # round fourteen: near misses for the two-argument tools, so more tool rows never cost her abstains
           "what is base64", "why do people use base64", "what does json stand for", "is json better than xml",
           "how do i move files on a mac", "what's the difference between copy and move", "why can't i rename a file",
           "what is a good naming scheme for files", "how many languages are there", "is french hard to learn",
           "what language do they speak in brazil", "how do translators work", "what's the best note taking app",
           "should i keep notes in one file", "what is a pdf", "who invented the pdf", "why are pdfs hard to edit",
           "what makes a good contract", "what is an invoice", "how do i rotate my phone screen", "what is image resolution",
           "what's the difference between png and jpg", "why is webp smaller", "what is a heic file", "how big is 4k",
           "what does it mean to back up a file", "where do deleted files go", "what is a file extension",
           "can you read handwriting", "what does reverse mean in math", "what is a palindrome", "what's the opposite of shout",
           "how do you say no politely", "what is a document", "why is my downloads folder so big",
           "how do photographers edit photos", "is it safe to rename system files", "what's in a zip file",
           "how does copy and paste work", "what's a good password manager", "what does archive mean in email"],
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
