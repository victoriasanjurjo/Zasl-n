"""Abstract Base Classes (ABCs) and contracts for Zaslón architecture.

Ensures complete decoupling between:
1. Data Ingestion/Export (BaseParser)
2. PII Detection Engines (BaseDetector)
3. Transformation & Anonymization Engine (BaseTransformer)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generator, List, Optional
import pandas as pd

from src.core.types import PIIMatch, TransformationStrategy


class BaseParser(ABC):
    """Contract for file parsers supporting chunked streaming and writing."""

    @abstractmethod
    def read_chunks(self, file_path: str, chunk_size: int = 50000) -> Generator[pd.DataFrame, None, None]:
        """Stream chunks of data sequentially from source to avoid memory saturation.
        
        Args:
            file_path: Absolute or relative path to source file.
            chunk_size: Number of records per chunk.
            
        Yields:
            pandas.DataFrame representing the chunk.
        """
        pass

    @abstractmethod
    def write_chunk(self, chunk: pd.DataFrame, output_path: str, is_first_chunk: bool = False) -> None:
        """Append or initialize writing processed chunk to target file.
        
        Args:
            chunk: Data chunk to persist.
            output_path: Destination file path.
            is_first_chunk: True if starting a new output file; False when appending.
        """
        pass

    @abstractmethod
    def inspect_schema(self, file_path: str, sample_size: int = 100) -> pd.DataFrame:
        """Extract column headers, inferred data types, and preview rows without loading full file."""
        pass


class BaseDetector(ABC):
    """Contract for PII identification engines (Regex, NER, Checksum-based, etc.)."""

    @abstractmethod
    def detect(self, text: str) -> List[PIIMatch]:
        """Detect PII entities in a single string.
        
        Args:
            text: Raw input string to analyze.
            
        Returns:
            List of detected PIIMatch instances with byte offsets and entity types.
        """
        pass

    def detect_batch(self, texts: List[str]) -> List[List[PIIMatch]]:
        """Batch detection optimized for vectorized or multi-element analysis.
        
        Default implementation iterates over elements; can be overridden by GPU/ONNX backends.
        """
        return [self.detect(t) for t in texts]


class BaseTransformer(ABC):
    """Contract for data transformation, pseudonymization, and synthetic substitution."""

    @abstractmethod
    def transform_value(
        self,
        value: Any,
        matches: List[PIIMatch],
        strategy: TransformationStrategy,
        salt: Optional[str] = None,
        custom_mask: Optional[str] = None
    ) -> Any:
        """Apply transformation strategy across detected PII occurrences within a value.
        
        Args:
            value: Cell or text content to transform.
            matches: Detected entities inside the value.
            strategy: Desired anonymization strategy.
            salt: Optional cryptographic salt for HMAC pseudonymization.
            custom_mask: Custom template (e.g., "[REDACTED_{ENTITY}]").
            
        Returns:
            Transformed value preserving type where applicable.
        """
        pass
