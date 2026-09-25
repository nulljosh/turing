"""tools_organizer.py: the organizer family (Reminders, Calendar, Notes past what tools_apps.py already
covers), with `_app` mocked throughout so nothing real is ever touched.

Run: python3 tests/test_organizer.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_organizer


class ListReminders(unittest.TestCase):
    """Incomplete reminders, read only."""

    def test_reads_plainly(self):
        """Whatever Reminders hands back, trimmed, is the answer."""
        with mock.patch.object(tools_organizer, "_app", return_value="Buy milk\nCall dentist (due Friday)\n"):
            self.assertEqual(tools_organizer.list_reminders(), "Buy milk\nCall dentist (due Friday)")

    def test_empty_is_plain(self):
        """No incomplete reminders is "No reminders.", never invented."""
        with mock.patch.object(tools_organizer, "_app", return_value=""):
            self.assertEqual(tools_organizer.list_reminders(), "No reminders.")

    def test_narrowed_empty_names_the_query(self):
        """A word that matches nothing names the word in its refusal."""
        with mock.patch.object(tools_organizer, "_app", return_value=""):
            self.assertEqual(tools_organizer.list_reminders("zzz"), "No reminders matching 'zzz'.")


class CompleteReminder(unittest.TestCase):
    """Marks the first incomplete match done. No match and several matches change nothing."""

    def test_no_match(self):
        """No reminder contains the text: an honest refusal, and only the find script ran."""
        with mock.patch.object(tools_organizer, "_app", return_value="") as m:
            self.assertEqual(tools_organizer.complete_reminder("buy milk"), "No reminder matching 'buy milk'.")
            m.assert_called_once()  # only the find script ran, never the completer

    def test_several_matches_lists_and_changes_nothing(self):
        """More than one match lists every one of them and completes none."""
        with mock.patch.object(tools_organizer, "_app", return_value="Buy milk\nBuy milkshake\n") as m:
            reply = tools_organizer.complete_reminder("milk")
            self.assertIn("2 reminders", reply)
            self.assertIn("Buy milk", reply)
            self.assertIn("Buy milkshake", reply)
            m.assert_called_once()

    def test_single_match_completes_it(self):
        """Exactly one match is marked completed, by its exact found name, not the loose query."""
        with mock.patch.object(tools_organizer, "_app", side_effect=["Buy milk\n", ""]) as m:
            self.assertEqual(tools_organizer.complete_reminder("buy milk"), "Completed: Buy milk.")
            self.assertEqual(m.call_count, 2)
            self.assertEqual(m.call_args[0][1], "Buy milk")  # the exact name found, not the loose query

    def test_empty_name(self):
        """No name given is an honest ask, AppleScript never called."""
        with mock.patch.object(tools_organizer, "_app", side_effect=AssertionError("called")):
            self.assertIn("Complete which reminder", tools_organizer.complete_reminder("  "))


class AddEvent(unittest.TestCase):
    """An event on the first writable calendar. No time is an honest ask."""

    def test_happy_path(self):
        """A title with a date reuses _when and lands on the calendar, one hour long."""
        with mock.patch.object(tools_organizer, "_app", return_value="") as m:
            reply = tools_organizer.add_event("lunch with sam tomorrow at noon")
        self.assertIn("Added to your calendar: lunch with sam", reply)
        self.assertIn("at 12:00 PM", reply)
        m.assert_called_once()

    def test_no_time_given_asks(self):
        """No date words in the text is an honest ask, never a guessed time."""
        with mock.patch.object(tools_organizer, "_app", side_effect=AssertionError("called")):
            reply = tools_organizer.add_event("lunch with sam")
        self.assertIn("What time", reply)
        self.assertIn("lunch with sam", reply)


class CalendarTomorrow(unittest.TestCase):
    """Same shape as calendar_today, one day out."""

    def test_reads_plainly(self):
        """Whatever Calendar hands back for tomorrow is the answer."""
        with mock.patch.object(tools_organizer, "_app", return_value="2:00 PM Dentist\n"):
            self.assertEqual(tools_organizer.calendar_tomorrow(), "2:00 PM Dentist\n")

    def test_empty_is_plain(self):
        """Nothing on the calendar tomorrow is one honest sentence."""
        with mock.patch.object(tools_organizer, "_app", return_value=""):
            self.assertEqual(tools_organizer.calendar_tomorrow(), "Nothing on the calendar tomorrow.")


class SearchNotes(unittest.TestCase):
    """Notes.app names and bodies, read only, a snippet each."""

    def test_hits_with_snippet(self):
        """A hit is the note's name and a plain-text snippet, HTML stripped."""
        with mock.patch.object(tools_organizer, "_app", return_value="Shopping || <div>eggs, milk, bread</div>\n"):
            reply = tools_organizer.search_notes("eggs")
        self.assertEqual(reply, "Shopping: eggs, milk, bread")

    def test_no_hits(self):
        """No note matches the word: an honest refusal naming it."""
        with mock.patch.object(tools_organizer, "_app", return_value=""):
            self.assertEqual(tools_organizer.search_notes("eggs"), "No notes matching 'eggs'.")

    def test_empty_query(self):
        """No word given is an honest ask, AppleScript never called."""
        with mock.patch.object(tools_organizer, "_app", side_effect=AssertionError("called")):
            self.assertIn("Search notes for what", tools_organizer.search_notes("  "))


class AppendNote(unittest.TestCase):
    """Appends to the first matching note by name. No match never creates one."""

    def test_no_matching_note_refuses(self):
        """No note contains the name: an honest refusal, and it is never created."""
        with mock.patch.object(tools_organizer, "_app", return_value="") as m:
            reply = tools_organizer.append_note("eggs\tshopping")
        self.assertIn("No note matching 'shopping'", reply)
        self.assertIn("never create", reply)
        m.assert_called_once()  # only the find script ran, never the append

    def test_matching_note_appends(self):
        """The first matching note by name gets the line appended."""
        with mock.patch.object(tools_organizer, "_app", side_effect=["Shopping list\n", ""]) as m:
            reply = tools_organizer.append_note("eggs\tshopping")
        self.assertEqual(reply, "Added to Shopping list: eggs")
        self.assertEqual(m.call_count, 2)

    def test_missing_content_or_name(self):
        """No content or no note name is an honest ask, AppleScript never called."""
        with mock.patch.object(tools_organizer, "_app", side_effect=AssertionError("called")):
            self.assertIn("Append what", tools_organizer.append_note("\tshopping"))
            self.assertIn("Append what", tools_organizer.append_note("eggs\t"))


class Routing(unittest.TestCase):
    """Every organizer phrasing reaches its tool end to end through tools.do."""

    def test_list_reminders(self):
        """"What are my reminders" routes to list_reminders."""
        with mock.patch.object(tools, "list_reminders", return_value="Buy milk"):
            self.assertEqual(tools.do("what are my reminders", confirm=lambda n, a: True), "Buy milk")

    def test_complete_reminder(self):
        """"Complete the reminder to buy milk" routes to complete_reminder on a yes."""
        with mock.patch.object(tools, "complete_reminder", return_value="Completed: Buy milk."):
            self.assertEqual(tools.do("complete the reminder to buy milk", confirm=lambda n, a: True), "Completed: Buy milk.")

    def test_complete_reminder_asks_first(self):
        """A no through confirm never runs complete_reminder."""
        with mock.patch.object(tools, "complete_reminder", side_effect=AssertionError("ran without a yes")):
            self.assertEqual(tools.do("complete the reminder to buy milk", confirm=lambda n, a: False), "Okay, I will not.")

    def test_add_event(self):
        """"Add ... to my calendar ..." routes to add_event on a yes."""
        with mock.patch.object(tools, "add_event", return_value="Added to your calendar: lunch"):
            self.assertEqual(tools.do("add lunch with sam to my calendar tomorrow at noon", confirm=lambda n, a: True),
                              "Added to your calendar: lunch")

    def test_calendar_tomorrow(self):
        """"What's on my calendar tomorrow" routes to calendar_tomorrow."""
        with mock.patch.object(tools, "calendar_tomorrow", return_value="Nothing on the calendar tomorrow."):
            self.assertEqual(tools.do("what's on my calendar tomorrow", confirm=lambda n, a: True), "Nothing on the calendar tomorrow.")

    def test_search_notes(self):
        """"Search notes for eggs" routes to search_notes, never web_search."""
        with mock.patch.object(tools, "search_notes", return_value="Shopping: eggs"):
            self.assertEqual(tools.do("search notes for eggs", confirm=lambda n, a: True), "Shopping: eggs")

    def test_append_note(self):
        """"Add eggs to my shopping note" routes to append_note on a yes."""
        with mock.patch.object(tools, "append_note", return_value="Added to Shopping list: eggs"):
            self.assertEqual(tools.do("add eggs to my shopping note", confirm=lambda n, a: True), "Added to Shopping list: eggs")

    def test_writes_are_classified(self):
        """The three writers ask first, same as new_note and new_reminder."""
        self.assertTrue({"complete_reminder", "add_event", "append_note"} <= tools.WRITES)


if __name__ == "__main__":
    unittest.main()
