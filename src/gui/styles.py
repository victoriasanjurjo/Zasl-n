"""Design system and QSS stylesheets for Zaslón Workbench.

Provides light and dark themes tailored for enterprise B2B data workflows.
"""

LIGHT_THEME_QSS = """
/* Global Window & Fonts */
QMainWindow, QDialog, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #e0f2fe;
    selection-color: #0369a1;
}

/* Header & Panels */
QFrame#sidebarPanel {
    background-color: #f1f5f9;
    border-right: 1px solid #e2e8f0;
}

QFrame#cardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
}

/* Drag & Drop Zone */
QFrame#dropZone {
    background-color: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 8px;
    padding: 24px;
}

QFrame#dropZone:hover {
    border-color: #0284c7;
    background-color: #f0f9ff;
}

/* Typography Elements */
QLabel#headerTitle {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.3px;
}

QLabel#sectionTitle {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: #64748b;
    letter-spacing: 0.8px;
}

QLabel#metricValue {
    font-size: 20px;
    font-weight: 700;
    color: #0284c7;
    font-family: 'Consolas', 'Cascadia Code', monospace;
}

QLabel#metricLabel {
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #f1f5f9;
}

QPushButton#primaryButton {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #0369a1;
}

QPushButton#dangerButton {
    background-color: #dc2626;
    border: 1px solid #b91c1c;
    color: #ffffff;
}

QPushButton#dangerButton:hover {
    background-color: #b91c1c;
}

/* Form Controls & Inputs */
QComboBox, QLineEdit, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px 10px;
    color: #1e293b;
}

QComboBox:focus, QLineEdit:focus {
    border: 1px solid #0284c7;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #e2e8f0;
}

/* Tables & Previews */
QTableWidget, QTableView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    gridline-color: #f1f5f9;
    border-radius: 4px;
    color: #334155;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item:selected {
    background-color: #e0f2fe;
    color: #0369a1;
}

/* Progress Bar */
QProgressBar {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    text-align: center;
    color: #0f172a;
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 3px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f8fafc;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

DARK_THEME_QSS = """
/* Global Window & Fonts */
QMainWindow, QDialog, QWidget {
    background-color: #0f1115;
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #1e3a5f;
    selection-color: #ffffff;
}

/* Header & Panels */
QFrame#sidebarPanel {
    background-color: #161920;
    border-right: 1px solid #232834;
}

QFrame#cardFrame {
    background-color: #161920;
    border: 1px solid #232834;
    border-radius: 6px;
}

/* Drag & Drop Zone */
QFrame#dropZone {
    background-color: #131720;
    border: 2px dashed #2d3748;
    border-radius: 8px;
    padding: 24px;
}

QFrame#dropZone:hover {
    border-color: #38bdf8;
    background-color: #171d2b;
}

/* Typography Elements */
QLabel#headerTitle {
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.3px;
}

QLabel#sectionTitle {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    color: #94a3b8;
    letter-spacing: 0.8px;
}

QLabel#metricValue {
    font-size: 20px;
    font-weight: 700;
    color: #38bdf8;
    font-family: 'Consolas', 'Cascadia Code', monospace;
}

QLabel#metricLabel {
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Buttons */
QPushButton {
    background-color: #1e2430;
    color: #f1f5f9;
    border: 1px solid #2d3748;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #283142;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #171d29;
}

QPushButton#primaryButton {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #0369a1;
}

QPushButton#dangerButton {
    background-color: #7f1d1d;
    border: 1px solid #991b1b;
    color: #fecaca;
}

QPushButton#dangerButton:hover {
    background-color: #991b1b;
}

/* Form Controls & Inputs */
QComboBox, QLineEdit, QSpinBox {
    background-color: #131720;
    border: 1px solid #2d3748;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e2e8f0;
}

QComboBox:focus, QLineEdit:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #2d3748;
}

/* Tables & Previews */
QTableWidget, QTableView {
    background-color: #11141c;
    border: 1px solid #232834;
    gridline-color: #1e2433;
    border-radius: 4px;
    color: #cbd5e1;
}

QHeaderView::section {
    background-color: #161a24;
    color: #94a3b8;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #2d3748;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item:selected {
    background-color: #1e3a5f;
    color: #f8fafc;
}

/* Progress Bar */
QProgressBar {
    background-color: #131720;
    border: 1px solid #232834;
    border-radius: 4px;
    text-align: center;
    color: #f8fafc;
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 3px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f1115;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2d3748;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
