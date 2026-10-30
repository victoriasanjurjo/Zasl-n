"""Chunked Anonymization Pipeline for high-throughput batch and streaming execution.

Processes CSV, Parquet, JSON, and text line-by-line or batch-by-batch with minimal memory footprint,
preserving original schema types and emitting live telemetry.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
import pandas as pd

from src.core.interfaces import BaseDetector, BaseParser, BaseTransformer
from src.core.parsers import DataStreamParser
from src.core.types import (
    ColumnConfig,
    PIIEntityType,
    PIIMatch,
    ProcessingMetrics,
    TransformationStrategy,
)
from src.engines.regex_detector import RegexDetector
from src.engines.transformers import DataTransformer


class AnonymizationPipeline:
    """Core orchestrator executing detection, anonymization, and serialization over chunk streams."""

    def __init__(
        self,
        parser: Optional[BaseParser] = None,
        detector: Optional[BaseDetector] = None,
        transformer: Optional[BaseTransformer] = None,
        whitelist: Optional[Set[str]] = None,
    ):
        self.parser = parser or DataStreamParser()
        self.detector = detector or RegexDetector()
        self.transformer = transformer or DataTransformer()
        self.whitelist: Set[str] = {w.lower() for w in (whitelist or set())}

    def process_file(
        self,
        input_file: str,
        output_file: str,
        column_configs: Optional[Dict[str, ColumnConfig]] = None,
        default_strategy: TransformationStrategy = TransformationStrategy.MASK,
        salt: Optional[str] = None,
        chunk_size: int = 25000,
        progress_callback: Optional[Callable[[ProcessingMetrics], None]] = None,
        cancellation_check: Optional[Callable[[], bool]] = None,
    ) -> ProcessingMetrics:
        """Execute stream anonymization on the target file.
        
        Args:
            input_file: Source path.
            output_file: Destination path.
            column_configs: Optional per-column settings. If None, scans all string columns.
            default_strategy: Fallback strategy when not explicitly overridden per column.
            salt: Salt for HMAC-SHA256 pseudonymization.
            chunk_size: Record batch size for streaming.
            progress_callback: Callable receiving ProcessingMetrics after each chunk.
            cancellation_check: Callable returning True if user requested abort.
            
        Returns:
            ProcessingMetrics with total counts and speed.
        """
        metrics = ProcessingMetrics()
        start_time = time.perf_counter()
        is_first_chunk = True

        try:
            for chunk_df in self.parser.read_chunks(input_file, chunk_size=chunk_size):
                if cancellation_check and cancellation_check():
                    break

                chunk_rows = len(chunk_df)
                metrics.total_rows += chunk_rows

                # Process chunk columns
                transformed_chunk = self._process_chunk(
                    chunk_df=chunk_df,
                    column_configs=column_configs,
                    default_strategy=default_strategy,
                    salt=salt,
                    metrics=metrics,
                )

                # Persist transformed chunk
                self.parser.write_chunk(
                    chunk=transformed_chunk,
                    output_path=output_file,
                    is_first_chunk=is_first_chunk
                )
                is_first_chunk = False

                # Update live telemetry
                metrics.processed_rows += chunk_rows
                metrics.elapsed_seconds = max(0.001, time.perf_counter() - start_time)
                metrics.rows_per_second = metrics.processed_rows / metrics.elapsed_seconds

                if progress_callback:
                    progress_callback(metrics)

        finally:
            # Clean up and flush writers
            if isinstance(self.parser, DataStreamParser):
                self.parser.close_writers()

        return metrics

    def _process_chunk(
        self,
        chunk_df: pd.DataFrame,
        column_configs: Optional[Dict[str, ColumnConfig]],
        default_strategy: TransformationStrategy,
        salt: Optional[str],
        metrics: ProcessingMetrics,
    ) -> pd.DataFrame:
        """Anonymize a single chunk dataframe."""
        df_out = chunk_df.copy()

        # Identify columns to scan
        columns_to_scan = list(df_out.columns)

        for col in columns_to_scan:
            cfg = column_configs.get(col) if column_configs else None
            if cfg and not cfg.active:
                continue

            strategy = cfg.strategy if cfg else default_strategy
            col_salt = (cfg.salt if cfg and cfg.salt else salt)

            # Vectorized or element-wise inspection for object/string data
            col_series = df_out[col]
            if col_series.dtype == object or pd.api.types.is_string_dtype(col_series):
                transformed_vals = []
                for val in col_series:
                    if pd.isna(val):
                        transformed_vals.append(val)
                        continue

                    val_str = str(val)
                    # Detect PII
                    detected = self.detector.detect(val_str)
                    
                    # Filter whitelisted matches
                    active_matches: List[PIIMatch] = []
                    for m in detected:
                        if m.value.lower() not in self.whitelist:
                            active_matches.append(m)

                    if active_matches:
                        metrics.detected_pii_count += len(active_matches)
                        metrics.transformed_cells_count += 1
                        new_val = self.transformer.transform_value(
                            value=val_str,
                            matches=active_matches,
                            strategy=strategy,
                            salt=col_salt,
                            custom_mask=cfg.mask_format if cfg else None
                        )
                        transformed_vals.append(new_val)
                    else:
                        transformed_vals.append(val)

                df_out[col] = transformed_vals

        return df_out
