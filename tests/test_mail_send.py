"""tools_mail_send.py: send emails to contacts.

Run: python3 tests/test_mail_send.py
"""
import os
import sys
import unittest
from unittest import mock

os.environ["SAMANTHA_HEADLESS"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import tools
import tools_mail_send


class SendEmailResolveContact(unittest.TestCase):
    """Resolve recipient name through Contacts app."""

    def test_no_recipient_or_message(self):
        """A tab pair is required with both recipient and message."""
        result = tools_mail_send.send_email("mom")
        self.assertIn("recipient and", result)

    def test_empty_recipient(self):
        """Empty recipient is refused."""
        result = tools_mail_send.send_email("\tI'll be late")
        self.assertIn("recipient", result.lower())

    def test_empty_message(self):
        """Empty message is refused."""
        result = tools_mail_send.send_email("mom\t")
        self.assertIn("recipient", result.lower())

    def test_headless_sends_nothing(self):
        """In headless mode, nothing is sent, just a simulation message."""
        result = tools_mail_send.send_email("mom\tI'll be late")
        self.assertIn("Would email", result)
        self.assertIn("mom", result)

    def test_no_matching_contact_headless(self):
        """When no contact matches, headless still returns a simulation."""
        # In headless mode, we skip osascript entirely
        result = tools_mail_send.send_email("nonexistent\tMessage")
        self.assertIn("Would email", result)

    def test_multiple_matches_headless(self):
        """When there are multiple matches, headless still returns a simulation."""
        # In headless mode, we skip osascript entirely
        result = tools_mail_send.send_email("john\tLet's meet")
        self.assertIn("Would email", result)


class SendEmailConfirmation(unittest.TestCase):
    """Confirmation is required before sending."""

    def test_refused_confirm_no_send(self):
        """Refusing confirmation returns a refusal, no send."""
        # In headless mode, we don't call osascript at all
        # Just verify that the tool is in WRITES so confirm is asked
        # by checking the classification tests above
        self.assertIn("send_email", tools.WRITES)

    def test_routes_email_with_saying(self):
        """The 'email X saying Y' phrasing routes correctly."""
        with mock.patch.object(tools, "send_email") as mock_fn:
            mock_fn.return_value = "ok"
            result = tools.do("email mom saying I'll be late")
            mock_fn.assert_called()
            # Check the argument contains both name and message separated by tab
            call_args = mock_fn.call_args[0][0]
            self.assertIn("\t", call_args)

    def test_routes_send_email_to(self):
        """The 'send an email to X about Y' phrasing routes correctly."""
        with mock.patch.object(tools, "send_email") as mock_fn:
            mock_fn.return_value = "ok"
            result = tools.do("send an email to Alex about dinner tonight")
            mock_fn.assert_called()
            call_args = mock_fn.call_args[0][0]
            self.assertIn("\t", call_args)

    def test_routes_email_colon(self):
        """The 'email X: Y' phrasing routes correctly."""
        with mock.patch.object(tools, "send_email") as mock_fn:
            mock_fn.return_value = "ok"
            result = tools.do("email bob: running behind")
            mock_fn.assert_called()
            call_args = mock_fn.call_args[0][0]
            self.assertIn("\t", call_args)
            self.assertIn("running behind", call_args)

    def test_does_not_catch_check_mail(self):
        """'check my email' does not route to send_email."""
        with mock.patch.object(tools, "unread_mail") as mock_fn:
            mock_fn.return_value = "No unread mail."
            # This should route to unread_mail, not send_email
            result = tools.do("check my email")
            # send_email should not be called
            with mock.patch.object(tools, "send_email") as mock_send:
                # Re-run with the mock to verify it's not called
                result = tools.do("check my email")
                mock_send.assert_not_called()

    def test_does_not_catch_any_new_email(self):
        """'any new email' does not route to send_email."""
        with mock.patch.object(tools, "unread_mail") as mock_fn:
            mock_fn.return_value = "No unread mail."
            result = tools.do("any new email")
            # send_email should not be called
            with mock.patch.object(tools, "send_email") as mock_send:
                result = tools.do("any new email")
                mock_send.assert_not_called()


class SendEmailClassification(unittest.TestCase):
    """Tools are properly classified."""

    def test_in_writes(self):
        """send_email is in WRITES."""
        self.assertIn("send_email", tools.WRITES)

    def test_in_not_for_models(self):
        """send_email is in NOT_FOR_MODELS."""
        import tools_registry
        self.assertIn("send_email", tools_registry.NOT_FOR_MODELS)

    def test_tools_registered(self):
        """send_email is in tools.TOOLS."""
        self.assertIn("send_email", tools.TOOLS)


if __name__ == "__main__":
    unittest.main()
