"""Check the mail settings in backend/.env by sending one test email.

    python -m app.mailtest you@example.com

Prints the settings it uses (never the password) and the mail server's exact answer.
"""
import logging
import sys

from .config import get_settings
from .services import mailer


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print("Usage: python -m app.mailtest you@example.com")
        return 2
    logging.getLogger("nowbuilder.mail").setLevel(logging.ERROR)  # the answer is printed below, once
    s = get_settings()
    print(f"Host:      {s.smtp_host or '(empty: emails go to the dev outbox in development)'}")
    print(f"Port:      {s.smtp_port}  security: {s.smtp_security}")
    print(f"User:      {s.smtp_user or '(empty: nowBuilder will not sign in)'}")
    print(f"Password:  {'set (' + str(len(s.smtp_password.replace(' ', ''))) + ' characters)' if s.smtp_password else '(empty)'}")
    print(f"From:      {s.mail_from}")
    if not s.smtp_host.strip():
        print("\nSet NOWBUILDER_SMTP_HOST in backend/.env first.")
        return 1
    mail = mailer.Mail(to=sys.argv[1], kind="test", subject="nowBuilder test email",
                       text="Your nowBuilder mail settings work.", html=mailer._page("It works", "<p>Your nowBuilder mail settings work.</p>"))
    try:
        mailer.send(mail)
    except mailer.MailError as e:
        print(f"\nNot sent. {mailer.explain(e.__cause__) if e.__cause__ else e}")
        return 1
    print(f"\nSent to {sys.argv[1]}. Check the inbox (and spam).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
