"""Ventana Principal para Zaslón — PII Stripper & Data Anonymizer Workbench.

Implementa ingesta por arrastrar y soltar (Drag & Drop), previsualización interactiva de esquemas,
selección de reglas, ejecución asíncrona multihilo con telemetría en tiempo real y garantía 100% offline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from PySide6.QtCore import QThread, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.parsers import DataStreamParser
from src.core.types import ColumnConfig, ProcessingMetrics, TransformationStrategy
from src.db.database import DatabaseManager
from src.engines.regex_detector import RegexDetector
from src.gui.styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from src.gui.worker import PipelineWorker


class MainWindow(QMainWindow):
    """Ventana principal de escritorio para Zaslón Workbench."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zaslón — Eliminador de PII y Anonimizador de Datos [Modo Desconectado]")
        self.resize(1180, 780)
        self.setMinimumSize(960, 640)

        # Persistencia y motores
        self.db_manager = DatabaseManager()
        self.parser = DataStreamParser()
        self.detector = RegexDetector()

        # Estado
        self.current_file_path: Optional[str] = None
        self.preview_df: Optional[pd.DataFrame] = None
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[PipelineWorker] = None
        self.is_dark_mode: bool = False  # Modo claro por defecto

        # Configuración de Ícono
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_ui()
        self.setStyleSheet(LIGHT_THEME_QSS)
        self._load_profiles()

    def _setup_ui(self) -> None:
        """Construye la jerarquía visual de componentes."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Panel Lateral Izquierdo: Perfiles y Configuración
        sidebar = QFrame()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 24)
        sidebar_layout.setSpacing(16)

        title_lbl = QLabel("ZASLÓN WORKBENCH")
        title_lbl.setObjectName("headerTitle")
        subtitle_lbl = QLabel("Eliminador de PII B2B\nEntorno 100% Local y Desconectado")
        subtitle_lbl.setStyleSheet("color: #64748b; font-size: 11px;")

        sidebar_layout.addWidget(title_lbl)
        sidebar_layout.addWidget(subtitle_lbl)

        # Insignia de seguridad Offline
        badge = QLabel("● AISLADO DE RED / 100% LOCAL")
        badge.setStyleSheet("color: #059669; font-weight: 700; font-size: 11px; padding: 4px 8px; background: #d1fae5; border-radius: 4px;")
        sidebar_layout.addWidget(badge)

        # Selector / Conmutador de tema
        self.btn_theme_toggle = QPushButton("Cambiar a Modo Oscuro ☾")
        self.btn_theme_toggle.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        sidebar_layout.addWidget(self.btn_theme_toggle)

        sidebar_layout.addSpacing(6)

        # Selector de Perfil
        prof_title = QLabel("PERFIL DE ANONIMIZACIÓN")
        prof_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(prof_title)

        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        sidebar_layout.addWidget(self.profile_combo)

        self.profile_desc_lbl = QLabel("Enmascaramiento directo para datos personales identificables.")
        self.profile_desc_lbl.setWordWrap(True)
        self.profile_desc_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        sidebar_layout.addWidget(self.profile_desc_lbl)

        sidebar_layout.addSpacing(10)

        # Estrategia Global
        strat_title = QLabel("ESTRATEGIA PREDETERMINADA")
        strat_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(strat_title)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "ENMASCARAR ([REDACTADO])",
            "HASH_HMAC (SHA-256 con Sal)",
            "SINTÉTICO (Datos Coherentes)",
            "SUPRIMIR (Limpiar Valor)"
        ])
        sidebar_layout.addWidget(self.strategy_combo)

        sidebar_layout.addStretch()

        # Botones de Acción
        self.btn_start = QPushButton("INICIAR ANONIMIZACIÓN")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._start_processing)

        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_processing)

        sidebar_layout.addWidget(self.btn_start)
        sidebar_layout.addWidget(self.btn_cancel)

        main_layout.addWidget(sidebar)

        # 2. Área de Contenido Principal (Derecha)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        # Zona de Arrastrar y Soltar (Drop Zone)
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self._drag_enter_event
        self.drop_zone.dropEvent = self._drop_event

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        self.drop_lbl = QLabel("ARRASTRE Y SUELTE EL ARCHIVO AQUÍ\nFormatos soportados: CSV, Parquet, JSON, Excel (.xlsx), TXT o Logs")
        self.drop_lbl.setAlignment(Qt.AlignCenter)
        self.drop_lbl.setStyleSheet("color: #475569; font-weight: 600;")
        
        self.btn_browse = QPushButton("O explorar archivos...")
        self.btn_browse.setFixedWidth(180)
        self.btn_browse.clicked.connect(self._browse_file)

        drop_layout.addWidget(self.drop_lbl)
        drop_layout.addWidget(self.btn_browse, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.drop_zone)

        # Cabecera de la tabla de previsualización
        preview_header_layout = QHBoxLayout()
        table_title = QLabel("VISTA PREVIA DEL ESQUEMA Y COLUMNAS DETECTADAS")
        table_title.setObjectName("sectionTitle")
        self.file_info_lbl = QLabel("Ningún archivo seleccionado")
        self.file_info_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        preview_header_layout.addWidget(table_title)
        preview_header_layout.addStretch()
        preview_header_layout.addWidget(self.file_info_lbl)
        content_layout.addLayout(preview_header_layout)

        # Tabla de Esquema y Muestra
        self.table_preview = QTableWidget(0, 5)
        self.table_preview.setHorizontalHeaderLabels([
            "Nombre de Columna", "Tipo Inferido", "Muestra de Contenido", "PII Detectada", "Acción por Columna"
        ])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        content_layout.addWidget(self.table_preview)

        # Fila de Tarjetas de Telemetría
        metrics_frame = QFrame()
        metrics_frame.setObjectName("cardFrame")
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(16, 12, 16, 12)

        self.metric_rows_val = QLabel("0")
        self.metric_rows_val.setObjectName("metricValue")
        self.metric_speed_val = QLabel("0 fil/s")
        self.metric_speed_val.setObjectName("metricValue")
        self.metric_pii_val = QLabel("0")
        self.metric_pii_val.setObjectName("metricValue")
        self.metric_time_val = QLabel("0.0s")
        self.metric_time_val.setObjectName("metricValue")

        metrics_layout.addLayout(self._create_metric_col("FILAS PROCESADAS", self.metric_rows_val))
        metrics_layout.addLayout(self._create_metric_col("VELOCIDAD", self.metric_speed_val))
        metrics_layout.addLayout(self._create_metric_col("PII REDACTADA", self.metric_pii_val))
        metrics_layout.addLayout(self._create_metric_col("TIEMPO TRANSCURRIDO", self.metric_time_val))
        content_layout.addWidget(metrics_frame)

        # Barra de progreso y pie de estado
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        content_layout.addWidget(self.progress_bar)

        self.status_bar_lbl = QLabel("Listo. Seleccione o arrastre un archivo de datos para comenzar.")
        self.status_bar_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
        content_layout.addWidget(self.status_bar_lbl)

        main_layout.addWidget(content)

    def _toggle_theme(self) -> None:
        """Permite alternar dinámicamente entre modo claro y modo oscuro."""
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet(DARK_THEME_QSS)
            self.btn_theme_toggle.setText("Cambiar a Modo Claro ☼")
        else:
            self.setStyleSheet(LIGHT_THEME_QSS)
            self.btn_theme_toggle.setText("Cambiar a Modo Oscuro ☾")

    def _create_metric_col(self, label_text: str, val_widget: QLabel) -> QVBoxLayout:
        """Generador auxiliar para columnas de métricas."""
        layout = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setObjectName("metricLabel")
        layout.addWidget(lbl)
        layout.addWidget(val_widget)
        return layout

    def _load_profiles(self) -> None:
        """Carga perfiles de anonimización almacenados en SQLite."""
        self.profile_combo.clear()
        profiles = self.db_manager.get_profiles()
        for p in profiles:
            self.profile_combo.addItem(p["name"], userData=p)

    def _on_profile_changed(self) -> None:
        """Sincroniza descripción y estrategia al cambiar el perfil activo."""
        p_data = self.profile_combo.currentData()
        if p_data:
            self.profile_desc_lbl.setText(p_data.get("description", ""))
            strat = p_data.get("default_strategy", "MASK")
            index = 0
            if strat == "HASH_HMAC":
                index = 1
            elif strat == "SYNTHETIC":
                index = 2
            elif strat == "SUPPRESS":
                index = 3
            self.strategy_combo.setCurrentIndex(index)

    def _drag_enter_event(self, event: QDragEnterEvent) -> None:
        """Acepta eventos de arrastre con archivos válidos."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent) -> None:
        """Maneja el evento de soltar un archivo en la Drop Zone."""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._load_file(file_path)

    def _browse_file(self) -> None:
        """Abre el diálogo nativo de selección de archivos."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Archivo de Datos para Anonimizar",
            "",
            "Archivos Soportados (*.csv *.parquet *.json *.jsonl *.xlsx *.txt *.log);;Todos los Archivos (*.*)"
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str) -> None:
        """Inspecciona el esquema del archivo y rellena la tabla de previsualización."""
        self.current_file_path = file_path
        p = Path(file_path)
        self.drop_lbl.setText(f"Cargado: {p.name} ({p.suffix.upper()})")
        self.file_info_lbl.setText(f"{file_path} | Tamaño: {p.stat().st_size / (1024*1024):.2f} MB")

        try:
            self.preview_df = self.parser.inspect_schema(file_path, sample_size=50)
            self._populate_table(self.preview_df)
            self.btn_start.setEnabled(True)
            self.status_bar_lbl.setText(f"Esquema inspeccionado exitosamente: {len(self.preview_df.columns)} columnas detectadas.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Inspección", f"No se pudo inspeccionar el archivo:\n{str(e)}")

    def _populate_table(self, df: pd.DataFrame) -> None:
        """Puebla la tabla de previsualización con tipos, muestras y selectores de acción."""
        self.table_preview.setRowCount(0)
        self.table_preview.setRowCount(len(df.columns))

        action_labels = [
            "USAR PREDETERMINADO",
            "ENMASCARAR",
            "HASH_HMAC",
            "SINTÉTICO",
            "SUPRIMIR",
            "CONSERVAR / OMITIR"
        ]

        for row_idx, col_name in enumerate(df.columns):
            # Nombre de Columna
            item_name = QTableWidgetItem(str(col_name))
            self.table_preview.setItem(row_idx, 0, item_name)

            # Tipo Inferido
            dtype_str = str(df[col_name].dtype)
            item_dtype = QTableWidgetItem(dtype_str)
            self.table_preview.setItem(row_idx, 1, item_dtype)

            # Muestra de Contenido
            sample_val = str(df[col_name].dropna().iloc[0]) if not df[col_name].dropna().empty else "<VACÍO>"
            if len(sample_val) > 40:
                sample_val = sample_val[:37] + "..."
            item_sample = QTableWidgetItem(sample_val)
            self.table_preview.setItem(row_idx, 2, item_sample)

            # Escaneo de PII detectada en la muestra
            detected = self.detector.detect(sample_val)
            detected_summary = ", ".join(m.entity_type.value for m in detected) if detected else "Ninguna detectada"
            item_pii = QTableWidgetItem(detected_summary)
            if detected:
                item_pii.setForeground(Qt.darkYellow if not self.is_dark_mode else Qt.yellow)
            self.table_preview.setItem(row_idx, 3, item_pii)

            # Selector de Acción por Columna
            action_combo = QComboBox()
            action_combo.addItems(action_labels)
            action_combo.setCurrentIndex(0)
            self.table_preview.setCellWidget(row_idx, 4, action_combo)

    def _start_processing(self) -> None:
        """Inicia el PipelineWorker en un hilo QThread secundario para ejecución por streaming."""
        if not self.current_file_path:
            return

        in_p = Path(self.current_file_path)
        out_name = f"{in_p.stem}_anonimizado{in_p.suffix}"
        default_out = in_p.parent / out_name

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Archivo Anonimizado Como",
            str(default_out),
            f"Archivos (*{in_p.suffix})"
        )
        if not output_file:
            return

        # Preparar configuraciones individuales de columnas
        col_configs: Dict[str, ColumnConfig] = {}
        for row in range(self.table_preview.rowCount()):
            col_name = self.table_preview.item(row, 0).text()
            combo: QComboBox = self.table_preview.cellWidget(row, 4)
            chosen = combo.currentText()

            if chosen == "CONSERVAR / OMITIR":
                col_configs[col_name] = ColumnConfig(column_name=col_name, strategy=TransformationStrategy.MASK, active=False)
            elif chosen == "ENMASCARAR":
                col_configs[col_name] = ColumnConfig(column_name=col_name, strategy=TransformationStrategy.MASK, active=True)
            elif chosen == "HASH_HMAC":
                col_configs[col_name] = ColumnConfig(column_name=col_name, strategy=TransformationStrategy.HASH_HMAC, active=True)
            elif chosen == "SINTÉTICO":
                col_configs[col_name] = ColumnConfig(column_name=col_name, strategy=TransformationStrategy.SYNTHETIC, active=True)
            elif chosen == "SUPRIMIR":
                col_configs[col_name] = ColumnConfig(column_name=col_name, strategy=TransformationStrategy.SUPPRESS, active=True)

        # Estrategia Global
        idx = self.strategy_combo.currentIndex()
        strategies = [
            TransformationStrategy.MASK,
            TransformationStrategy.HASH_HMAC,
            TransformationStrategy.SYNTHETIC,
            TransformationStrategy.SUPPRESS
        ]
        default_strategy = strategies[idx]

        # Actualizar interfaz a estado ocupado
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # Modo indeterminado durante streaming
        self.status_bar_lbl.setText("Procesando y anonimizando registros por lotes...")

        # Instanciar Worker y QThread
        self.worker_thread = QThread()
        self.worker = PipelineWorker(
            input_file=self.current_file_path,
            output_file=output_file,
            column_configs=col_configs,
            default_strategy=default_strategy,
            salt="zaslon-b2b-secure-salt-2026"
        )
        self.worker.moveToThread(self.worker_thread)

        # Conectar señales Qt
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.status_message.connect(self._on_status_message)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)

        # Ciclo de vida y limpieza de hilos
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _on_worker_progress(self, processed_rows: int, rows_per_sec: float, detected_pii: int) -> None:
        """Actualiza los contadores de telemetría en tiempo real."""
        self.metric_rows_val.setText(f"{processed_rows:,}")
        self.metric_speed_val.setText(f"{int(rows_per_sec):,} fil/s")
        self.metric_pii_val.setText(f"{detected_pii:,}")

    def _on_status_message(self, msg: str) -> None:
        """Actualiza el mensaje en la barra de estado inferior."""
        self.status_bar_lbl.setText(msg)

    def _on_worker_finished(self, metrics: ProcessingMetrics) -> None:
        """Notifica la finalización exitosa del proceso de anonimización."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.metric_time_val.setText(f"{metrics.elapsed_seconds:.2f}s")

        # Registrar en la bitácora SQLite
        if self.current_file_path:
            p = Path(self.current_file_path)
            self.db_manager.log_execution(
                file_name=p.name,
                file_format=p.suffix.upper(),
                total_rows=metrics.processed_rows,
                detected_pii=metrics.detected_pii_count,
                elapsed_seconds=metrics.elapsed_seconds,
                output_path=""
            )

        QMessageBox.information(
            self,
            "Anonimización Completada",
            f"Se procesaron exitosamente {metrics.processed_rows:,} filas.\n"
            f"Entidades de PII redactadas: {metrics.detected_pii_count:,}\n"
            f"Tiempo de ejecución: {metrics.elapsed_seconds:.2f} segundos ({metrics.rows_per_second:.0f} filas/s)."
        )

    def _on_worker_error(self, err_msg: str) -> None:
        """Gestiona excepciones ocurridas en el hilo de trabajo."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.status_bar_lbl.setText("Ocurrió un error durante el procesamiento.")
        QMessageBox.critical(self, "Error en el Pipeline", f"Ocurrió un error inesperado:\n{err_msg}")

    def _cancel_processing(self) -> None:
        """Solicita la cancelación cooperativa del proceso."""
        if self.worker:
            self.worker.request_cancellation()
            self.btn_cancel.setEnabled(False)
