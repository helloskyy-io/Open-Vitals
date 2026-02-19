"""
Shared result type for Temporal activities.

Activities return ActivityResult so workflows get status, details, and optional
artifacts (e.g. loaded config, secrets) without putting raw data in history
in an ad-hoc way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ActivityResult:
    """Structured result from an activity; status + optional artifacts."""

    status: Literal["ok", "changed", "skipped", "failed"]
    details: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
