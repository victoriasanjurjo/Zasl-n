"""Entry point for Zaslón PII Stripper & Data Anonymizer Workbench.

Enforces offline execution policy, initializes High-DPI Qt runtime,
and launches the PySide6 desktop interface.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src module resolution
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def configure_offline_environment() -> None:
    """Enforce air-gapped local restrictions in environment variables."""
    # Disable automated telemetry / proxy dials
    os.environ["NO_PROXY"] = "*"
    os.environ["HTTP_PROXY"] = ""
    os.environ["HTTPS_PROXY"] = ""
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


def main() -> int:
    """Main application lifecycle."""
    configure_offline_environment()

    app = QApplication(sys.argv)
    app.setApplicationName("ZaslonWorkbench")
    app.setOrganizationName("ZaslonEnterprise")
    app.setApplicationDisplayName("Zaslón — Eliminador de PII y Anonimizador de Datos")

    # Set application-wide icon
    icon_path = ROOT_DIR / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
