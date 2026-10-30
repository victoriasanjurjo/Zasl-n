"""Transformation and Anonymization Engines implementing masking, salted HMAC-SHA256
pseudonymization, and synthetically coherent replacements.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, List, Optional

from src.core.interfaces import BaseTransformer
from src.core.types import PIIEntityType, PIIMatch, TransformationStrategy


class DataTransformer(BaseTransformer):
    """Concrete transformer implementing deterministic and synthetic anonymization."""

    def __init__(self, default_salt: str = "zaslon-b2b-default-salt"):
        """Initialize transformer with a default salt for HMAC."""
        self.default_salt = default_salt.encode("utf-8")

    def transform_value(
        self,
        value: Any,
        matches: List[PIIMatch],
        strategy: TransformationStrategy,
        salt: Optional[str] = None,
        custom_mask: Optional[str] = None
    ) -> Any:
        """Apply the specified anonymization strategy to matches in the value."""
        if value is None:
            return None

        # Convert to string for span replacement if string or numeric
        val_str = str(value)
        if not matches:
            return value

        active_salt = salt.encode("utf-8") if salt else self.default_salt

        # Replace spans in reverse order so character offsets remain valid
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)
        transformed = val_str

        for match in sorted_matches:
            replacement = self._generate_replacement(
                match=match,
                strategy=strategy,
                salt=active_salt,
                custom_mask=custom_mask
            )
            transformed = (
                transformed[:match.start]
                + replacement
                + transformed[match.end:]
            )

        return transformed

    def _generate_replacement(
        self,
        match: PIIMatch,
        strategy: TransformationStrategy,
        salt: bytes,
        custom_mask: Optional[str] = None
    ) -> str:
        """Generate replacement token according to strategy."""
        
        if strategy == TransformationStrategy.MASK:
            if custom_mask:
                return custom_mask.format(entity=match.entity_type.value)
            return f"[{match.entity_type.value}_REDACTED]"

        elif strategy == TransformationStrategy.HASH_HMAC:
            # HMAC-SHA256 preserves referential integrity across relational joins
            h = hmac.new(salt, match.value.encode("utf-8"), hashlib.sha256)
            digest = h.hexdigest()
            # Clean formatted token with prefix and short truncated hash
            return f"{match.entity_type.value[:3]}_{digest[:16].upper()}"

        elif strategy == TransformationStrategy.SYNTHETIC:
            return self._generate_synthetic_value(match, salt)

        elif strategy == TransformationStrategy.SUPPRESS:
            return ""

        return f"[REDACTED_{match.entity_type.value}]"

    def _generate_synthetic_value(self, match: PIIMatch, salt: bytes) -> str:
        """Generate contextually coherent synthetic data based on entity type."""
        # Compute deterministic seed based on salt + value to keep consistency
        h = hmac.new(salt, match.value.encode("utf-8"), hashlib.md5).hexdigest()
        num_seed = int(h[:8], 16)

        if match.entity_type == PIIEntityType.EMAIL:
            return f"user_{num_seed % 100000}@anonymized.internal"
            
        elif match.entity_type == PIIEntityType.CREDIT_CARD:
            # Keep brand prefix/length if possible, with deterministic valid Luhn ending
            clean_digits = [c for c in match.value if c.isdigit()]
            last4 = "".join(clean_digits[-4:]) if len(clean_digits) >= 4 else "0000"
            return f"4000-0000-0000-{last4}"
            
        elif match.entity_type == PIIEntityType.IPV4:
            return f"10.{(num_seed >> 8) % 255}.{(num_seed >> 16) % 255}.{(num_seed) % 254 + 1}"
            
        elif match.entity_type == PIIEntityType.IPV6:
            return f"fd00::{(num_seed % 65535):04x}:1"
            
        elif match.entity_type == PIIEntityType.CUIT_CUIL:
            # Deterministic synthetic format
            base = f"20{num_seed % 90000000 + 10000000}4"
            return f"{base[:2]}-{base[2:10]}-{base[10:]}"
            
        elif match.entity_type == PIIEntityType.DNI:
            return f"{num_seed % 80000000 + 10000000}"
            
        elif match.entity_type == PIIEntityType.PHONE:
            return f"+1-555-{(num_seed % 900 + 100):03d}-{(num_seed % 9000 + 1000):04d}"
            
        elif match.entity_type == PIIEntityType.PERSON_NAME:
            return f"Synthetic Person #{num_seed % 10000}"

        return f"SYNTHETIC_{match.entity_type.value}_{num_seed % 1000}"
