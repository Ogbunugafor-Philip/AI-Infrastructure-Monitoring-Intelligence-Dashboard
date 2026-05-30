"""
Pydantic schemas for server registration & management, with strict input
validation that mirrors the route-handler checks.

Validation rules:
  * ip_address  - must parse as a valid IPv4 or IPv6 address
  * ssh_port    - integer in [1, 65535]
  * ssh_username- safe charset only ([A-Za-z0-9._-], 1-32 chars); blocks shell
                  metacharacters / injection vectors
  * ssh_key     - must be a parseable PEM/OpenSSH private key when provided
  * password    - must be non-empty when auth method is "password"
  * key-only    - cannot combine ssh_key_only_mode with password auth

Sensitive fields (password, key) are NEVER echoed back. Output schemas expose a
masked placeholder instead.
"""
from __future__ import annotations

import ipaddress
import re
import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from models.enums import ServerStatus, SSHAuthMethod

MASK = "••••••••"

# Linux-style username: starts with a letter/underscore, then word chars/.-
_USERNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]{0,31}$")
_PEM_RE = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
    re.DOTALL,
)


# --------------------------------------------------------------------------- #
# Reusable validators                                                          #
# --------------------------------------------------------------------------- #
def validate_ip(value: str) -> str:
    """Return the normalized string form of a valid IPv4/IPv6 address."""
    value = (value or "").strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise ValueError("Must be a valid IPv4 or IPv6 address")


def validate_username(value: str) -> str:
    value = (value or "").strip()
    if not _USERNAME_RE.match(value):
        raise ValueError(
            "SSH username must be 1-32 chars, start with a letter/underscore, "
            "and contain only letters, digits, '.', '_' or '-'"
        )
    return value


def validate_pem_key(value: str) -> str:
    """Validate that the value is a parseable PEM/OpenSSH private key."""
    value = (value or "").strip()
    if not _PEM_RE.search(value):
        raise ValueError("SSH key must be a PEM-format private key block")
    # Deep validation: attempt to actually parse the key material.
    try:
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            load_ssh_private_key,
        )

        data = value.encode("utf-8")
        try:
            load_pem_private_key(data, password=None)
        except Exception:
            # OpenSSH-format keys (-----BEGIN OPENSSH PRIVATE KEY-----)
            load_ssh_private_key(data, password=None)
    except Exception:
        raise ValueError("SSH key is not a valid/parseable private key")
    return value


def validate_whitelist(value: str | None) -> str | None:
    """Validate a comma-separated list of IPs / CIDR ranges (if provided)."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    cleaned: list[str] = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            # Accept both single addresses and CIDR networks.
            if "/" in item:
                ipaddress.ip_network(item, strict=False)
            else:
                ipaddress.ip_address(item)
        except ValueError:
            raise ValueError(f"Invalid IP/CIDR in whitelist: {item!r}")
        cleaned.append(item)
    return ",".join(cleaned) if cleaned else None


# --------------------------------------------------------------------------- #
# Input schemas                                                                #
# --------------------------------------------------------------------------- #
class ServerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    ip_address: str
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_username: str
    ssh_auth_method: SSHAuthMethod
    ssh_password: str | None = Field(default=None, max_length=4096)
    ssh_key: str | None = Field(default=None, max_length=32768)
    ssh_key_only_mode: bool = False
    allowed_ip_whitelist: str | None = None

    _v_ip = field_validator("ip_address")(validate_ip)
    _v_user = field_validator("ssh_username")(validate_username)
    _v_wl = field_validator("allowed_ip_whitelist")(validate_whitelist)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Server name must not be empty")
        return v

    @model_validator(mode="after")
    def _check_auth_consistency(self) -> "ServerCreate":
        if self.ssh_auth_method == SSHAuthMethod.password:
            if self.ssh_key_only_mode:
                raise ValueError(
                    "Cannot use password auth while ssh_key_only_mode is enabled"
                )
            if not self.ssh_password or not self.ssh_password.strip():
                raise ValueError("ssh_password is required for password auth")
        elif self.ssh_auth_method == SSHAuthMethod.key:
            if not self.ssh_key or not self.ssh_key.strip():
                raise ValueError("ssh_key is required for key auth")
            validate_pem_key(self.ssh_key)
        return self


class ServerUpdate(BaseModel):
    """Partial update. Credential fields, if supplied, are re-encrypted."""
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    ip_address: str | None = None
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    ssh_username: str | None = None
    ssh_auth_method: SSHAuthMethod | None = None
    ssh_password: str | None = Field(default=None, max_length=4096)
    ssh_key: str | None = Field(default=None, max_length=32768)
    ssh_key_only_mode: bool | None = None
    allowed_ip_whitelist: str | None = None
    status: ServerStatus | None = None

    @field_validator("ip_address")
    @classmethod
    def _v_ip(cls, v: str | None) -> str | None:
        return validate_ip(v) if v is not None else None

    @field_validator("ssh_username")
    @classmethod
    def _v_user(cls, v: str | None) -> str | None:
        return validate_username(v) if v is not None else None

    @field_validator("allowed_ip_whitelist")
    @classmethod
    def _v_wl(cls, v: str | None) -> str | None:
        return validate_whitelist(v)

    @field_validator("ssh_key")
    @classmethod
    def _v_key(cls, v: str | None) -> str | None:
        return validate_pem_key(v) if v else v


class TestConnectionRequest(BaseModel):
    """
    Test an SSH connection — either for an existing server (by id) or for
    not-yet-registered inline credentials (used by the registration form).
    """
    model_config = ConfigDict(extra="forbid")

    server_id: uuid.UUID | None = None
    ip_address: str | None = None
    ssh_port: int | None = Field(default=22, ge=1, le=65535)
    ssh_username: str | None = None
    ssh_auth_method: SSHAuthMethod | None = None
    ssh_password: str | None = Field(default=None, max_length=4096)
    ssh_key: str | None = Field(default=None, max_length=32768)
    ssh_key_only_mode: bool = False

    @field_validator("ip_address")
    @classmethod
    def _v_ip(cls, v: str | None) -> str | None:
        return validate_ip(v) if v is not None else None

    @field_validator("ssh_username")
    @classmethod
    def _v_user(cls, v: str | None) -> str | None:
        return validate_username(v) if v is not None else None

    @model_validator(mode="after")
    def _check(self) -> "TestConnectionRequest":
        if self.server_id is None:
            # Inline test requires the full connection tuple.
            missing = [
                f for f in ("ip_address", "ssh_username", "ssh_auth_method")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(
                    "Provide server_id, or all of: " + ", ".join(missing)
                )
            if self.ssh_auth_method == SSHAuthMethod.password:
                if self.ssh_key_only_mode:
                    raise ValueError("key-only mode forbids password auth")
                if not self.ssh_password:
                    raise ValueError("ssh_password required for password auth")
            elif self.ssh_auth_method == SSHAuthMethod.key:
                if not self.ssh_key:
                    raise ValueError("ssh_key required for key auth")
                validate_pem_key(self.ssh_key)
        return self


class RevealCredentialsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dashboard_password: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Output schemas (sensitive fields masked)                                     #
# --------------------------------------------------------------------------- #
class ServerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    ip_address: str
    ssh_port: int
    ssh_username: str
    ssh_auth_method: SSHAuthMethod
    ssh_key_only_mode: bool
    allowed_ip_whitelist: str | None
    status: ServerStatus
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    # Masked indicators — never the real (encrypted or plaintext) values.
    ssh_password: str | None = None
    ssh_key: str | None = None

    @classmethod
    def from_model(cls, server) -> "ServerOut":
        out = cls.model_validate(server)
        out.ssh_password = MASK if server.encrypted_ssh_password else None
        out.ssh_key = MASK if server.encrypted_ssh_key else None
        return out


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class RevealCredentialsResponse(BaseModel):
    auth_method: SSHAuthMethod
    credential: str  # decrypted, returned only after password re-verification


class MessageResponse(BaseModel):
    message: str
