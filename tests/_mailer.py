"""Shared in-test mailer that captures emails instead of sending them.

A single instance is installed process-wide by the autouse ``mailer`` fixture
(see ``conftest.py``) and cleared before each test. Helpers can pull the
verification / reset token straight out of the captured email body, so any test
that needs a *verified* account (login now requires it) can confirm the email
without reaching a real SMTP server.
"""

import re


class CapturingMailer:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})

    def clear(self) -> None:
        self.sent.clear()

    def _token(self, body: str) -> str | None:
        match = re.search(r"token=([\w\-]+)", body)
        return match.group(1) if match else None

    def last_token(self) -> str:
        assert self.sent, "no email was captured"
        token = self._token(self.sent[-1]["body"])
        assert token, f"no token in email body: {self.sent[-1]['body']!r}"
        return token

    def token_for(self, email: str) -> str:
        for message in reversed(self.sent):
            if message["to"] == email:
                token = self._token(message["body"])
                if token:
                    return token
        raise AssertionError(f"no captured email with a token for {email!r}")


# Process-wide instance shared by the autouse fixture and the test helpers.
capturing_mailer = CapturingMailer()
