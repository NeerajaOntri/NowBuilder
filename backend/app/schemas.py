from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator



class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------

class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("can't be blank")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(_Out):
    id: str
    email: str
    first_name: str
    last_name: str
    is_platform_admin: bool = False
    email_verified: bool = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- ServiceNow instances ----------

InstanceType = Literal["Development", "Test", "Production"]
AuthMethod = Literal["basic", "oauth"]


class InstanceCreateIn(BaseModel):
    """Basic: username + password. OAuth: the same plus an Application Registry client id/secret
    (password grant); nowBuilder keeps the refresh token and renews access tokens itself."""

    name: str = Field(min_length=1, max_length=80, description="Friendly name shown in nowBuilder")
    instance_type: InstanceType
    url: str = Field(min_length=3, max_length=255, description="https://<name>.service-now.com, or just <name>")
    auth_method: AuthMethod = "basic"
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)
    client_id: str = Field(default="", max_length=255)
    client_secret: str = Field(default="", max_length=400)
    auto_deploy: bool | None = Field(default=None, description="Omit for the server default (NOWBUILDER_AUTO_DEPLOY)")


class InstanceUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1, max_length=255)
    client_id: str | None = Field(default=None, max_length=255)
    client_secret: str | None = Field(default=None, min_length=1, max_length=400)
    auto_deploy: bool | None = None
    instance_type: InstanceType | None = None


class InstanceOut(_Out):
    id: str
    name: str
    instance_type: InstanceType
    url: str
    auth_method: AuthMethod
    username: str
    client_id: str
    release: str | None
    user_display_name: str | None
    roles: list | None
    is_admin: bool
    auto_deploy: bool = True
    status: str
    status_message: str | None
    last_checked_at: datetime | None
    created_at: datetime
    is_selected: bool = False


# ---------- AI provider ----------

class AIProviderIn(BaseModel):
    provider: str = Field(default="anthropic", min_length=1, max_length=80)   # any name; known ones fill the base URL
    model: str = Field(min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=1, max_length=400, description="Omit to keep the saved key")
    base_url: str | None = Field(default=None, max_length=300)


class AIProviderOut(BaseModel):
    provider: str
    provider_name: str = ""          # as the admin typed it
    kind: str = "anthropic"
    base_url: str | None = None
    model: str
    api_key_masked: str
    verified: bool
    verified_at: datetime | None
    status_message: str | None
    updated_at: datetime | None = None
