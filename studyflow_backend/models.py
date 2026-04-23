from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectMeta:
    icon: str
    color: str
