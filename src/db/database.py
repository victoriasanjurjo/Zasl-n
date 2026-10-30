"""Local persistence manager using SQLite.

Manages anonymization profiles, whitelist rules, column-level mapping schemas,
and audit logs for compliance tracking.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """Manages local SQLite database operations for Zaslón."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to .sqlite3 database. If None, defaults to config/zaslon_local.db.
        """
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "config"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base_dir / "zaslon_local.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL mode enabled for high concurrency."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                default_strategy TEXT NOT NULL DEFAULT 'MASK',
                salt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS whitelists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                entity_type TEXT NOT NULL,
                allowed_value TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS column_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                column_name TEXT NOT NULL,
                strategy TEXT NOT NULL,
                entity_type TEXT,
                custom_mask TEXT,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_format TEXT NOT NULL,
                total_rows INTEGER,
                detected_pii INTEGER,
                elapsed_seconds REAL,
                output_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Insert default profiles if empty or translate existing
            cursor = conn.execute("SELECT COUNT(*) as count FROM profiles")
            if cursor.fetchone()["count"] == 0:
                conn.execute("""
                INSERT INTO profiles (name, description, default_strategy, salt)
                VALUES ('Enmascaramiento Estricto B2B', 'Enmascaramiento directo para datos personales identificables', 'MASK', 'b2b-salt-001')
                """)
                conn.execute("""
                INSERT INTO profiles (name, description, default_strategy, salt)
                VALUES ('Seudonimización Relacional HMAC', 'Hashes HMAC-SHA256 con sal para preservar integridad referencial', 'HASH_HMAC', 'b2b-salt-secure-99')
                """)
                conn.execute("""
                INSERT INTO profiles (name, description, default_strategy, salt)
                VALUES ('Datos Sintéticos de Prueba', 'Generación de datos ficticios coherentes para entornos de desarrollo y QA', 'SYNTHETIC', 'b2b-salt-test')
                """)
            else:
                # Update any existing English defaults to Spanish
                conn.execute("""
                UPDATE profiles SET name = 'Enmascaramiento Estricto B2B', description = 'Enmascaramiento directo para datos personales identificables'
                WHERE name = 'Strict B2B Masking';
                """)
                conn.execute("""
                UPDATE profiles SET name = 'Seudonimización Relacional HMAC', description = 'Hashes HMAC-SHA256 con sal para preservar integridad referencial'
                WHERE name = 'Relational HMAC Pseudonymization';
                """)
                conn.execute("""
                UPDATE profiles SET name = 'Datos Sintéticos de Prueba', description = 'Generación de datos ficticios coherentes para entornos de desarrollo y QA'
                WHERE name = 'Synthetic Test Data';
                """)

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Fetch all stored profiles."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM profiles ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_whitelists(self, profile_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch whitelisted entries for a profile or global."""
        with self._get_connection() as conn:
            if profile_id:
                cursor = conn.execute("SELECT * FROM whitelists WHERE profile_id = ?", (profile_id,))
            else:
                cursor = conn.execute("SELECT * FROM whitelists")
            return [dict(row) for row in cursor.fetchall()]

    def log_execution(
        self,
        file_name: str,
        file_format: str,
        total_rows: int,
        detected_pii: int,
        elapsed_seconds: float,
        output_path: str
    ) -> None:
        """Record batch execution details for compliance auditing."""
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO audit_logs (file_name, file_format, total_rows, detected_pii, elapsed_seconds, output_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (file_name, file_format, total_rows, detected_pii, elapsed_seconds, output_path))
