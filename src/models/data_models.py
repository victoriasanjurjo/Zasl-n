"""Data models for schemas, profiles, and audit representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.types import TransformationStrategy


@dataclass(slots=True)
class ColumnSchema:
    """Schema descriptor for a single column."""
    name: str
    dtype: str
    sample_values: List[str] = field(default_factory=list)
    suggested_strategy: TransformationStrategy = TransformationStrategy.MASK


@dataclass(slots=True)
class AnonymizationProfile:
    """Stored configuration profile for batch operations."""
    id: Optional[int]
    name: str
    description: str
    default_strategy: TransformationStrategy
    salt: Optional[str]
    created_at: Optional[datetime] = None


@dataclass(slots=True)
class AuditRecord:
    """Log entry recording anonymization run metadata."""
    id: Optional[int]
    file_name: str
    file_format: str
    total_rows: int
    detected_pii: int
    elapsed_seconds: float
    output_path: str
    timestamp: Optional[datetime] = None
