"""
Notification package for trading system (Phase 106 / Feature F503 / Release R122).

Exports:
    AlertDispatcher: Multi-channel alert and webhook dispatcher.
    MultiChannelAlertDispatcher: Primary architectural alias.
    NotificationDispatcher: Backward-compatible alias.
    MultiChannelNotifier: Functional alias.
    Phase106AlertDispatcher: Phase-specific alias.
    AlertLevel: Alert severity enumeration (INFO, SUCCESS, WARNING, CRITICAL, EMERGENCY).
    ChannelType: Communication channel enumeration (TELEGRAM, SLACK, CONSOLE).
"""

from .alert_dispatcher import (
    AlertDispatcher,
    MultiChannelAlertDispatcher,
    NotificationDispatcher,
    MultiChannelNotifier,
    Phase106AlertDispatcher,
    AlertLevel,
    ChannelType,
)

__all__ = [
    "AlertDispatcher",
    "MultiChannelAlertDispatcher",
    "NotificationDispatcher",
    "MultiChannelNotifier",
    "Phase106AlertDispatcher",
    "AlertLevel",
    "ChannelType",
]
