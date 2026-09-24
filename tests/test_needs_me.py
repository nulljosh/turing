"""tools_apps.py's two cross-source abilities: needs_attention (unread mail, today's calendar and due
reminders, ranked into three lines by the local model) and free_when (the calendar's open gaps for a day or
the week). AppleScript rides through _app(), mocked throughout, so this passes on Linux CI with no Mail,
Calendar or Reminders to reach, and never invents a meeting that is not in the mocked source text.

Run: python3 tests/test_needs_me.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tools
import tools_apps


class DueReminders(unittest.TestCase):
    """_due_reminders reads Reminders through _app, read only, and is never a guess."""

    def test_empty_is_plain(self):
        """No AppleScript output is "Nothing due.", never invented."""
        with mock.patch.object(tools_apps, "_app", return_value=""):
            self.assertEqual(tools_apps._due_reminders(), "Nothing due.")

    def test_real_output_passes_through(self):
        """Whatever Reminders hands back, trimmed, is the answer."""
        with mock.patch.object(tools_apps, "_app", return_value="Pay rent (overdue)\nCall dentist (today)\n"):
            self.assertEqual(tools_apps._due_reminders(), "Pay rent (overdue)\nCall dentist (today)")


class NeedsAttention(unittest.TestCase):
    """needs_attention combines mail, calendar and reminders and asks the local model to rank them."""

    def test_all_empty_never_calls_the_model(self):
        """Nothing anywhere is one honest sentence; the model is never asked, nothing is invented."""
        with mock.patch.object(tools_apps, "unread_mail", return_value="No unread mail."), \
                mock.patch.object(tools_apps, "calendar_today", return_value="Nothing on the calendar today."), \
                mock.patch.object(tools_apps, "_due_reminders", return_value="Nothing due."), \
                mock.patch("tools_llm.ask_llm", side_effect=AssertionError("model should not be called")):
            self.assertEqual(tools_apps.needs_attention(),
                              "Nothing needs your attention: no unread mail, nothing on the calendar today, and no reminders due.")

    def test_some_content_asks_the_model_and_strips_attribution(self):
        """Real content from any one source reaches the model, and its self-naming is stripped, same as summarize."""
        with mock.patch.object(tools_apps, "unread_mail", return_value="Boss || Budget due Friday"), \
                mock.patch.object(tools_apps, "calendar_today", return_value="Nothing on the calendar today."), \
                mock.patch.object(tools_apps, "_due_reminders", return_value="Nothing due."), \
                mock.patch("tools_llm.ask_llm", return_value="Reply to your boss about the budget.\nNothing on the "
                           "calendar.\nNo reminders due.\n(Answered by Qwen on this Mac, not by me.)") as ask:
            result = tools_apps.needs_attention()
        self.assertEqual(result, "Reply to your boss about the budget.\nNothing on the calendar.\nNo reminders due.")
        prompt = ask.call_args[0][0]
        self.assertIn("Boss || Budget due Friday", prompt)
        self.assertIn("invent nothing", prompt)

    def test_route(self):
        """"What needs my attention" and "what needs me" both reach it, with no argument."""
        self.assertEqual(tools.plan("what needs my attention"), [("needs_attention", ())])
        self.assertEqual(tools.plan("what needs me"), [("needs_attention", ())])

    def test_read_only(self):
        """No write, no confirm: it is never in WRITES or NOT_FOR_MODELS."""
        self.assertNotIn("needs_attention", tools.WRITES)
        self.assertNotIn("needs_attention", tools.NOT_FOR_MODELS)


class FreeWhen(unittest.TestCase):
    """free_when reads the calendar's gaps for a day or the week, business hours, and never invents a meeting."""

    def test_empty_calendar_is_free_all_day(self):
        """Nothing on the calendar is free the whole business day, said plainly."""
        with mock.patch.object(tools_apps, "_app", return_value=""):
            self.assertEqual(tools_apps.free_when(""), "Today: free 9:00 AM to 6:00 PM.")

    def test_fully_booked_business_hours(self):
        """An event spanning the whole 9-to-6 window is booked solid."""
        with mock.patch.object(tools_apps, "_app", return_value="32400 64800\n"):  # 9am to 6pm, in seconds since midnight
            self.assertEqual(tools_apps.free_when(""), "Today: booked solid.")

    def test_a_gap_between_two_meetings(self):
        """A real gap between two events comes back as the one open window."""
        busy = "32400 36000\n39600 64800\n"  # 9-10am and 11am-6pm busy: free 10 to 11
        with mock.patch.object(tools_apps, "_app", return_value=busy):
            self.assertEqual(tools_apps.free_when(""), "Today: free 10:00 AM to 11:00 AM.")

    def test_named_weekday_scopes_the_right_day(self):
        """A named weekday's busy block lands on that day, not today, however many days out it is."""
        from datetime import date, timedelta
        today = date.today()
        offset = (list(tools_apps._WEEKDAYS).index("thursday") - today.weekday()) % 7
        start, end = offset * 86400 + 9 * 3600, offset * 86400 + 10 * 3600  # 9-10am on the target day
        with mock.patch.object(tools_apps, "_app", return_value=f"{start} {end}\n"):
            result = tools_apps.free_when("thursday morning")
        label = "Today" if offset == 0 else "Tomorrow" if offset == 1 else "Thursday"
        self.assertEqual(result, f"{label}: free 10:00 AM to 12:00 PM.")

    def test_this_week_lists_every_remaining_weekday(self):
        """"This week" covers every business day left in it, weekends skipped, never today's list alone."""
        from datetime import date, timedelta
        today = date.today()
        days = [today + timedelta(days=n) for n in range(7 - today.weekday()) if (today + timedelta(days=n)).weekday() < 5]
        if not days:
            days = [today + timedelta(days=n) for n in range(7 - today.weekday(), 14 - today.weekday()) if (today + timedelta(days=n)).weekday() < 5]
        with mock.patch.object(tools_apps, "_app", return_value=""):
            result = tools_apps.free_when("this week")
        self.assertEqual(result.count("free 9:00 AM to 6:00 PM."), len(days))

    def test_route(self):
        """The Siri-style phrasings all reach free_when, with the trailing day or range as its argument."""
        self.assertEqual(tools.plan("am i free"), [("free_when", ("",))])
        self.assertEqual(tools.plan("am i free thursday afternoon"), [("free_when", ("thursday afternoon",))])
        self.assertEqual(tools.plan("when am i free this week"), [("free_when", ("this week",))])
        self.assertEqual(tools.plan("do i have time thursday afternoon"), [("free_when", ("thursday afternoon",))])

    def test_read_only(self):
        """No write, no confirm: it is never in WRITES or NOT_FOR_MODELS."""
        self.assertNotIn("free_when", tools.WRITES)
        self.assertNotIn("free_when", tools.NOT_FOR_MODELS)


if __name__ == "__main__":
    unittest.main()
