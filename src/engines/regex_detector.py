"""High-speed deterministic PII detection engine utilizing pre-compiled regular expressions
and algorithmic checksum validation (e.g. Luhn algorithm, Modulo 11 for Tax IDs).
"""

from __future__ import annotations

import re
from typing import Dict, List, Pattern, Set, Tuple

from src.core.interfaces import BaseDetector
from src.core.types import PIIEntityType, PIIMatch


def validate_luhn(number_str: str) -> bool:
    """Validate numeric string using ISO/IEC 7812 Luhn checksum algorithm."""
    clean_digits = [int(c) for c in number_str if c.isdigit()]
    if len(clean_digits) < 13 or len(clean_digits) > 19:
        return False
    
    checksum = 0
    parity = len(clean_digits) % 2
    for i, digit in enumerate(clean_digits):
        if i % 2 == parity:
            digit = digit * 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (checksum % 10) == 0


def validate_cuit(cuit_str: str) -> bool:
    """Validate Argentine CUIT/CUIL using Modulo 11 verification."""
    clean = [int(c) for c in cuit_str if c.isdigit()]
    if len(clean) != 11:
        return False
    
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(d * m for d, m in zip(clean[:10], multipliers))
    mod = 11 - (total % 11)
    
    if mod == 11:
        expected_check = 0
    elif mod == 10:
        expected_check = 9
    else:
        expected_check = mod
        
    return clean[10] == expected_check


class RegexDetector(BaseDetector):
    """Deterministic PII Detector optimized for speed and low false-positive rates."""

    def __init__(self, active_entities: Set[PIIEntityType] | None = None):
        """Initialize regex rules.
        
        Args:
            active_entities: Optional subset of entities to detect. If None, detects all.
        """
        self.active_entities = active_entities or {
            PIIEntityType.EMAIL,
            PIIEntityType.CREDIT_CARD,
            PIIEntityType.IPV4,
            PIIEntityType.IPV6,
            PIIEntityType.CUIT_CUIL,
            PIIEntityType.DNI,
            PIIEntityType.PHONE,
        }
        self._compiled_rules: Dict[PIIEntityType, List[Tuple[str, Pattern]]] = {}
        self._compile_rules()

    def _compile_rules(self) -> None:
        """Pre-compile regular expression patterns for maximum throughput."""
        
        # 1. Emails: RFC 5322 simplified, fast and accurate
        email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            re.IGNORECASE
        )
        
        # 2. Credit Cards: Major credit card formats (Visa, MasterCard, Amex, Discover, etc.)
        cc_pattern = re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b'
        )
        
        # 3. IPv4 & IPv6
        ipv4_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )
        ipv6_pattern = re.compile(
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b'
        )
        
        # 4. Tax IDs: CUIT / CUIL (Argentina) format ##-########-# or 11 digits
        cuit_pattern = re.compile(
            r'\b(20|23|24|27|30|33|34)[-.]?\d{8}[-.]?\d{1}\b'
        )
        
        # 5. DNI (Argentina / National IDs 7 to 8 digits with or without dots)
        dni_pattern = re.compile(
            r'\b\d{1,2}\.?\d{3}\.?\d{3}\b'
        )
        
        # 6. Phone Numbers (E.164, local and international formats)
        phone_pattern = re.compile(
            r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'
        )

        self._compiled_rules = {
            PIIEntityType.EMAIL: [("EMAIL_REGEX", email_pattern)],
            PIIEntityType.CREDIT_CARD: [("CREDIT_CARD_LUHN", cc_pattern)],
            PIIEntityType.IPV4: [("IPV4_REGEX", ipv4_pattern)],
            PIIEntityType.IPV6: [("IPV6_REGEX", ipv6_pattern)],
            PIIEntityType.CUIT_CUIL: [("CUIT_MOD11", cuit_pattern)],
            PIIEntityType.DNI: [("DNI_REGEX", dni_pattern)],
            PIIEntityType.PHONE: [("PHONE_REGEX", phone_pattern)],
        }

    def detect(self, text: str) -> List[PIIMatch]:
        """Detect and validate all active PII entities in the input text."""
        if not text or not isinstance(text, str):
            return []

        matches: List[PIIMatch] = []

        for entity_type, rules in self._compiled_rules.items():
            if entity_type not in self.active_entities:
                continue

            for rule_name, pattern in rules:
                for m in pattern.finditer(text):
                    val = m.group(0)
                    start, end = m.span()

                    # Algorithmic Validation
                    if entity_type == PIIEntityType.CREDIT_CARD:
                        if not validate_luhn(val):
                            continue  # Ignore false positives like barcodes or product codes
                            
                    elif entity_type == PIIEntityType.CUIT_CUIL:
                        if not validate_cuit(val):
                            continue  # Ignore invalid tax identifiers
                            
                    elif entity_type == PIIEntityType.DNI:
                        # Avoid matching small numbers or year strings if pure digits
                        clean_num = val.replace(".", "")
                        if len(clean_num) < 7 or len(clean_num) > 8:
                            continue
                        if clean_num.startswith("19") or clean_num.startswith("20"):
                            if len(clean_num) == 4:
                                continue

                    matches.append(
                        PIIMatch(
                            entity_type=entity_type,
                            start=start,
                            end=end,
                            value=val,
                            confidence=0.98 if entity_type in (PIIEntityType.CREDIT_CARD, PIIEntityType.CUIT_CUIL) else 0.90,
                            rule_name=rule_name
                        )
                    )

        # Sort matches by start position; resolve overlaps by keeping longest match
        return self._resolve_overlaps(matches)

    def _resolve_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Resolve overlapping matches giving priority to higher confidence or longer spans."""
        if not matches:
            return []

        # Sort primarily by start asc, length desc
        sorted_matches = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
        resolved: List[PIIMatch] = []
        last_end = -1

        for match in sorted_matches:
            if match.start >= last_end:
                resolved.append(match)
                last_end = match.end
            else:
                # Overlap detected. Keep current if it is strictly higher confidence
                if resolved and match.confidence > resolved[-1].confidence and (match.end - match.start) > (resolved[-1].end - resolved[-1].start):
                    resolved[-1] = match
                    last_end = match.end

        return resolved
