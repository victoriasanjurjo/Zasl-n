"""Asynchronous background worker executing chunked pipeline via QThread.

Ensures zero GUI lockup or stuttering when processing massive multi-gigabyte datasets.
"""

from __future__ import annotations

import traceback
from typing import Dict, Optional, Set
from PySide6.QtCore import QObject, QThread, Signal

from src.core.pipeline import AnonymizationPipeline
from src.core.types import ColumnConfig, ProcessingMetrics, TransformationStrategy


class PipelineWorker(QObject):
    """Worker object that executes AnonymizationPipeline on a dedicated worker thread."""

    started = Signal()
    progress = Signal(int, float, int)  # processed_rows, rows_per_sec, detected_pii
    status_message = Signal(str)
    finished = Signal(ProcessingMetrics)
    error = Signal(str)

    def __init__(
        self,
        input_file: str,
        output_file: str,
        column_configs: Optional[Dict[str, ColumnConfig]] = None,
        default_strategy: TransformationStrategy = TransformationStrategy.MASK,
        salt: Optional[str] = None,
        chunk_size: int = 25000,
        whitelist: Optional[Set[str]] = None,
    ):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.column_configs = column_configs
        self.default_strategy = default_strategy
        self.salt = salt
        self.chunk_size = chunk_size
        self.whitelist = whitelist or set()
        self._is_cancelled = False

    def request_cancellation(self) -> None:
        """Signal the worker to abort processing at next chunk boundary."""
        self._is_cancelled = True
        self.status_message.emit("Cancelación solicitada. Finalizando el bloque actual...")

    def run(self) -> None:
        """Execute processing pipeline in background."""
        self.started.emit()
        self.status_message.emit("Inicializando flujos de datos y motor de expresiones regulares...")

        try:
            pipeline = AnonymizationPipeline(whitelist=self.whitelist)

            def on_progress(metrics: ProcessingMetrics) -> None:
                self.progress.emit(
                    metrics.processed_rows,
                    metrics.rows_per_second,
                    metrics.detected_pii_count
                )

            metrics = pipeline.process_file(
                input_file=self.input_file,
                output_file=self.output_file,
                column_configs=self.column_configs,
                default_strategy=self.default_strategy,
                salt=self.salt,
                chunk_size=self.chunk_size,
                progress_callback=on_progress,
                cancellation_check=lambda: self._is_cancelled
            )

            if self._is_cancelled:
                self.status_message.emit("Procesamiento cancelado por el usuario.")
            else:
                self.status_message.emit("Anonimización de datos completada exitosamente.")
                
            self.finished.emit(metrics)

        except Exception as e:
            err_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(err_msg)
