"""Core type definitions and data structures for Zaslón PII Stripper & Data Anonymizer.

Provides strictly typed dataclasses and enums for detection, transformation,
metrics, and pipeline management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PIIEntityType(str, Enum):
    """Supported deterministic and heuristic PII entity types."""
    EMAIL = "EMAIL"
    CREDIT_CARD = "CREDIT_CARD"
    IPV4 = "IPV4"
    IPV6 = "IPV6"
    CUIT_CUIL = "CUIT_CUIL"
    DNI = "DNI"
    PHONE = "PHONE"
    PERSON_NAME = "PERSON_NAME"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    CUSTOM = "CUSTOM"


class TransformationStrategy(str, Enum):
    """Anonymization and pseudonymization strategies."""
    MASK = "MASK"                  # e.g., [EMAIL_REDACTED] or ***-***-1234
    HASH_HMAC = "HASH_HMAC"        # Salted HMAC-SHA256 to preserve referential integrity
    SYNTHETIC = "SYNTHETIC"        # Statistically or contextually coherent dummy values
    SUPPRESS = "SUPPRESS"          # Clear or None value


@dataclass(slots=True)
class PIIMatch:
    """Represents an identified PII entity within a string or cell."""
    entity_type: PIIEntityType
    start: int
    end: int
    value: str
    confidence: float = 1.0
    rule_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ColumnConfig:
    """Configuration mapping for a specific column/field."""
    column_name: str
    strategy: TransformationStrategy
    entity_types: List[PIIEntityType] = field(default_factory=list)
    salt: Optional[str] = None
    mask_format: Optional[str] = None
    active: bool = True


@dataclass(slots=True)
class ProcessingMetrics:
    """Runtime telemetry for chunked data execution."""
    total_rows: int = 0
    processed_rows: int = 0
    detected_pii_count: int = 0
    transformed_cells_count: int = 0
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0
    memory_usage_mb: float = 0.0
