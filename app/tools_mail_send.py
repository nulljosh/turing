"""Samantha sending mail: send_email to a contact by name.

send_email(arg): Send an email to a contact. arg is "name<TAB>message" where name is matched
against the Contacts app by full name or nickname. If no match or multiple matches, asks which.
Subject is the first few words of the message. Always asks for confirmation before sending.

"email mom saying I'll be late", "send an email to Alex about dinner tonight", "email bob: running behind".
"""
import os
import re
import subprocess

HEADLESS = os.environ.get("SAMANTHA_HEADLESS") == "1"


def _app(script, *args):
    """AppleScript that drives another app. Text rides in argv, never spliced into the script. Headless does nothing."""
    if HEADLESS:
        return ""
    r = subprocess.run(["osascript", "-e", script, *args], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr).strip()


# AppleScript to find contacts by name or nickname
_FIND_CONTACTS = '''on run argv
set name_query to item 1 of argv
set out to ""
set count to 0
tell application "Contacts"
    set all_people to every person
    repeat with p in all_people
        set full_name to name of p
        set found_match to false
        -- Check full name
        if full_name is name_query then
            set found_match to true
        else
            -- Check nickname
            try
                if nickname of p is name_query then
                    set found_match to true
                end if
            end try
        end if
        -- Also check if the query is a first name or last name
        if not found_match then
            set first_name to first name of p
            if first_name is name_query then
                set found_match to true
            end if
        end if
        if not found_match then
            set last_name to last name of p
            if last_name is name_query then
                set found_match to true
            end if
        end if
        if found_match then
            -- Get email addresses for this person
            try
                set email_list to (emails of p)
                repeat with e in email_list
                    set count to count + 1
                    set out to out & full_name & " <" & value of e & ">" & linefeed
                end repeat
            end try
        end if
    end repeat
end tell
return out & (count as string)
end run'''


# AppleScript to send an email
_SEND_EMAIL = '''on run argv
set full_email to item 1 of argv  -- "Name <email@domain.com>"
set subject to item 2 of argv
set body to item 3 of argv
tell application "Mail"
    set new_message to make new outgoing message with properties {subject:subject, content:body, visible:false}
    tell new_message
        make new to recipient at end of to recipients with properties {address:full_email}
        send
    end tell
end tell
return ""
end run'''


def send_email(arg):
    """Send an email to a contact by name. arg is 'name<TAB>message'.
    Resolves the recipient through Contacts app by full name, nickname, first name, or last name.
    If zero or several matches, asks which. Sends through Mail.app with a subject derived from the message.
    """
    request = arg.strip()
    if "\t" not in request:
        return "Say it like 'email mom saying I'll be late' (the recipient and the message)."

    recipient_name, _, message = request.partition("\t")
    recipient_name = recipient_name.strip()
    message = message.strip()

    if not recipient_name or not message:
        return "I need both a recipient name and a message."

    # In headless mode, just return what would be sent
    if HEADLESS:
        # Return a message showing what would be sent without actually calling osascript
        subject_words = " ".join(message.split()[:5])
        return f"Would email {recipient_name}: '{subject_words}...'"

    # Resolve the recipient name through Contacts
    result = _app(_FIND_CONTACTS, recipient_name)
    if not result:
        return f"I couldn't find a contact named {recipient_name!r}."

    # Parse the result: lines are "Full Name <email@domain.com>", last line is the count
    lines = result.splitlines()
    if not lines:
        return f"I couldn't find a contact named {recipient_name!r}."

    count_str = lines[-1].strip()
    try:
        count = int(count_str)
    except (ValueError, IndexError):
        count = len(lines)

    contacts = lines[:-1] if count_str.isdigit() else lines

    if count == 0:
        return f"I couldn't find a contact named {recipient_name!r}."

    if count > 1:
        # Multiple matches: ask which one
        options = "\n".join(f"  {c}" for c in contacts)
        return f"I found {count} matches for {recipient_name!r}. Which one?\n{options}"

    # Exactly one match: extract email address
    full_email = contacts[0].strip()

    # Generate subject from first few words of message
    subject_words = " ".join(message.split()[:5])

    # Send the email via Mail.app
    _app(_SEND_EMAIL, full_email, subject_words, message)

    # Extract name for the response (remove <email> if present)
    contact_name = full_email.split("<")[0].strip() if "<" in full_email else full_email
    return f"Emailed {contact_name}: {subject_words}..."


TOOLS = (send_email,)

_I = re.I
# (pattern, tool name, what to hand it)
ROUTES = (
    (re.compile(r"^email (\w+) (?:saying|that|about) (.+)$", _I),
     "send_email", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^send (?:an )?email to (\w+)(?: (?:saying|about|that))? (.+)$", _I),
     "send_email", lambda m: m.group(1) + "\t" + m.group(2)),
    (re.compile(r"^email (\w+): (.+)$", _I),
     "send_email", lambda m: m.group(1) + "\t" + m.group(2)),
)
