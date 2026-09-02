"""Domain enums mirroring PostgreSQL ENUM types."""

import enum


class UserRole(str, enum.Enum):
    ROOT_ADMIN = "root_admin"
    TENANT_ADMIN = "tenant_admin"
    WATCHER = "watcher"


class DecisionState(str, enum.Enum):
    NORMAL = "normal"
    WEIRD = "weird"
    WARNING = "warning"
    RESOLVED_TRUE_POSITIVE = "resolved_true_positive"
    RESOLVED_FALSE_POSITIVE = "resolved_false_positive"
    RESOLVED_FALSE_NEGATIVE = "resolved_false_negative"


class FeedbackDisposition(str, enum.Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"


class NotificationChannel(str, enum.Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class ScheduleDay(str, enum.Enum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"
