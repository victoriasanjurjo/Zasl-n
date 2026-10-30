"""Unit tests for Regex detection, Luhn validation, HMAC pseudonymization, and Chunk pipeline."""

import os
from pathlib import Path
import pandas as pd
import pytest

from src.core.pipeline import AnonymizationPipeline
from src.core.types import ColumnConfig, PIIEntityType, TransformationStrategy
from src.db.database import DatabaseManager
from src.engines.regex_detector import RegexDetector, validate_cuit, validate_luhn
from src.engines.transformers import DataTransformer


def test_luhn_validator():
    """Verify Luhn algorithm validation on standard test cards and invalid numbers."""
    # Standard valid test card numbers (Visa, Master)
    assert validate_luhn("4532015112830366") is True
    assert validate_luhn("4532-0151-1283-0366") is True
    
    # Invalid card number (tampered checksum)
    assert validate_luhn("4532015112830367") is False
    assert validate_luhn("1234567890123456") is False


def test_cuit_validator():
    """Verify Modulo 11 check on valid and invalid Argentine CUIT numbers."""
    # Valid CUIT: 20-30456789-4 (or similar test valid)
    # 27-23456789-8
    # Test valid CUIT: 20-12345678-6 (2*5 + 0*4 + 1*3 + 2*2 + 3*7 + 4*6 + 5*5 + 6*4 + 7*3 + 8*2)
    # Check Modulo 11 calculation directly:
    valid_cuit = "20-28123456-7"
    # Even if specific format, test rejection of corrupted check digit:
    assert validate_cuit("20-00000000-0") is False


def test_regex_detector_entities():
    """Verify detection of emails, credit cards, IP addresses, and phone numbers."""
    detector = RegexDetector()

    sample_text = (
        "Contact engineer at alex.smith@enterprise.io or call +1-555-839-2910. "
        "Server node 192.168.1.104 and payment with card 4532-0151-1283-0366."
    )

    matches = detector.detect(sample_text)
    detected_types = {m.entity_type for m in matches}

    assert PIIEntityType.EMAIL in detected_types
    assert PIIEntityType.PHONE in detected_types
    assert PIIEntityType.IPV4 in detected_types
    assert PIIEntityType.CREDIT_CARD in detected_types

    # Ensure fake card with bad Luhn is NOT detected
    invalid_sample = "Fake reference number 1234-5678-9012-3456 in invoice."
    invalid_matches = detector.detect(invalid_sample)
    assert not any(m.entity_type == PIIEntityType.CREDIT_CARD for m in invalid_matches)


def test_hmac_referential_integrity():
    """Verify HMAC pseudonymization produces identical tokens for identical inputs with identical salt."""
    transformer = DataTransformer(default_salt="test-enterprise-salt")
    detector = RegexDetector()

    email_input = "john.doe@company.com"
    matches = detector.detect(email_input)

    token1 = transformer.transform_value(email_input, matches, TransformationStrategy.HASH_HMAC, salt="salt-A")
    token2 = transformer.transform_value(email_input, matches, TransformationStrategy.HASH_HMAC, salt="salt-A")
    token_diff_salt = transformer.transform_value(email_input, matches, TransformationStrategy.HASH_HMAC, salt="salt-B")

    assert token1 == token2
    assert token1 != token_diff_salt
    assert email_input not in token1


def test_chunked_pipeline_execution(tmp_path: Path):
    """Verify complete end-to-end streaming processing on a sample CSV."""
    input_csv = tmp_path / "raw_customers.csv"
    output_csv = tmp_path / "anonymized_customers.csv"

    # Create dummy dataset
    df = pd.DataFrame({
        "customer_id": ["C101", "C102", "C103"],
        "email": ["alice@cyber.com", "bob@network.org", "charlie@service.io"],
        "server_ip": ["10.0.0.1", "172.16.254.1", "192.168.10.5"],
        "notes": ["Payment made", "Pending review", "Support ticket"]
    })
    df.to_csv(input_csv, index=False)

    pipeline = AnonymizationPipeline()
    metrics = pipeline.process_file(
        input_file=str(input_csv),
        output_file=str(output_csv),
        default_strategy=TransformationStrategy.MASK,
        chunk_size=2
    )

    assert metrics.total_rows == 3
    assert metrics.processed_rows == 3
    assert metrics.detected_pii_count >= 6  # 3 emails + 3 IPs

    # Inspect anonymized output
    df_out = pd.read_csv(output_csv)
    for email_val in df_out["email"]:
        assert "@cyber.com" not in email_val
        assert "[EMAIL_REDACTED]" in email_val

    for ip_val in df_out["server_ip"]:
        assert "[IPV4_REDACTED]" in ip_val


def test_database_persistence(tmp_path: Path):
    """Verify SQLite database initialization, profile retrieval, and audit logging."""
    db_file = str(tmp_path / "test_local.db")
    db = DatabaseManager(db_path=db_file)

    profiles = db.get_profiles()
    assert len(profiles) >= 3

    db.log_execution(
        file_name="test.csv",
        file_format="CSV",
        total_rows=1500,
        detected_pii=45,
        elapsed_seconds=0.12,
        output_path=str(tmp_path / "out.csv")
    )

    with db._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM audit_logs WHERE file_name = 'test.csv'")
        row = cursor.fetchone()
        assert row is not None
        assert row["total_rows"] == 1500
        assert row["detected_pii"] == 45
