import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOWBUILDER_", env_file=".env", extra="ignore")

    secret_key: str = "dev-only-secret-change-me-before-deploying-nowbuilder"
    encryption_key: str = ""  # Fernet key; required outside dev
    database_url: str = "sqlite:///./nowbuilder.db"
    cors_origins: str = "http://localhost:5173"
    # Address users open nowBuilder at (links in emails)
    public_url: str = "http://localhost:5173"
    access_token_minutes: int = 720
    environment: str = "development"

    default_ai_model: str = "claude-sonnet-5-5"
    # Optional: an address to pre-fill in Settings → ServiceNow instances → Connect. Empty = blank form.
    # Which instance nowBuilder works in is always the one connected and selected in the app.
    default_instance_url: str = ""
    # Plans deploy when the user clicks Deploy on the plan card (default). true = also deploy a plan
    # straight after it passes the checks, on Development/Test instances that allow it.
    auto_deploy: bool = False
    # Access control: active members (incl. pending invites) and connected instances per workspace
    max_members: int = 3
    max_instances: int = 2
    invite_days: int = 7
    # Platform (19 Oct 2026): emails of the nowBuilder platform admins (comma-separated). Only they see the
    # Platform page, approve new workspaces and set each workspace's plan and limits.
    platform_admins: str = ""
    # "open": a new sign-up's workspace works straight away; "approval": it waits until a platform admin
    # approves it. Empty = approval outside development, open in development.
    signup_mode: str = ""
    # Email (22 Oct 2026). Any SMTP provider (Gmail app password, Brevo, Resend, SendGrid…). With no
    # NOWBUILDER_SMTP_HOST in development, emails go to the dev outbox (/dev/outbox) instead of being sent.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_security: str = "starttls"  # starttls | ssl | none
    mail_from: str = "nowBuilder <no-reply@nowbuilder.local>"
    # New accounts confirm their email with a 6-digit code before they can use nowBuilder
    require_email_verification: bool = True
    # Where files nowBuilder keeps (encrypted) live, e.g. rollback copies (from Chunk 4)
    data_dir: str = "data"
    # Built frontend (index.html + assets) served by the backend itself when this folder exists (one service when hosted)
    static_dir: str = "static"

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        # On Render the service's own https address is in RENDER_EXTERNAL_URL: use it unless set explicitly
        hosted = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        if hosted and "NOWBUILDER_PUBLIC_URL" not in os.environ and self.public_url == "http://localhost:5173":
            self.public_url = hosted
        if hosted and hosted not in self.cors_origins:
            self.cors_origins = f"{self.cors_origins},{hosted}"

    @property
    def platform_admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.platform_admins.split(",") if e.strip()}

    @property
    def signup_needs_approval(self) -> bool:
        mode = self.signup_mode.strip().lower() or ("open" if self.environment == "development" else "approval")
        return mode == "approval"

    @property
    def dev_outbox(self) -> bool:
        """No mail server in development: keep emails in memory for /dev/outbox instead of sending."""
        return not self.smtp_host.strip() and self.environment == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
