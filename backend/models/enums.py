"""Shared enumerations used across ORM models and schemas."""
import enum


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    viewer = "viewer"


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    warning = "warning"


class SSHAuthMethod(str, enum.Enum):
    password = "password"
    key = "key"


class ReportType(str, enum.Enum):
    scheduled = "scheduled"
    manual = "manual"
