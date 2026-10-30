"""Data stream parsers and exporters for CSV, Parquet, JSON/JSONL, Excel, and Plaintext/Logs.

Optimized for constant memory footprint using chunks and streaming iterators via pandas and pyarrow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator, List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.core.interfaces import BaseParser


class DataStreamParser(BaseParser):
    """Unified streaming parser for structured and semi-structured tabular and text files."""

    def __init__(self):
        self._parquet_writer: Optional[pq.ParquetWriter] = None

    def read_chunks(self, file_path: str, chunk_size: int = 50000) -> Generator[pd.DataFrame, None, None]:
        """Stream data sequentially from file according to its format."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".csv":
            for chunk in pd.read_csv(file_path, chunksize=chunk_size, low_memory=False, dtype=str):
                yield chunk

        elif ext in (".parquet", ".pq"):
            parquet_file = pq.ParquetFile(file_path)
            for batch in parquet_file.iter_batches(batch_size=chunk_size):
                yield batch.to_pandas()

        elif ext in (".jsonl", ".ndjson"):
            for chunk in pd.read_json(file_path, lines=True, chunksize=chunk_size, dtype=False):
                yield chunk

        elif ext == ".json":
            # For standard JSON array of records
            df = pd.read_json(file_path)
            total_len = len(df)
            for i in range(0, total_len, chunk_size):
                yield df.iloc[i : i + chunk_size]

        elif ext in (".xlsx", ".xls"):
            # Excel files loaded in memory; yielded in chunks to maintain pipeline uniformity
            df = pd.read_excel(file_path, dtype=str)
            total_len = len(df)
            for i in range(0, total_len, chunk_size):
                yield df.iloc[i : i + chunk_size]

        elif ext in (".txt", ".log"):
            # Line by line chunking for unstructured logs
            lines_accumulator: List[str] = []
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    lines_accumulator.append(line.rstrip("\r\n"))
                    if len(lines_accumulator) >= chunk_size:
                        yield pd.DataFrame({"line": lines_accumulator})
                        lines_accumulator = []
            if lines_accumulator:
                yield pd.DataFrame({"line": lines_accumulator})

        else:
            raise ValueError(f"Unsupported file format extension: {ext}")

    def write_chunk(self, chunk: pd.DataFrame, output_path: str, is_first_chunk: bool = False) -> None:
        """Stream write or append a chunk to the destination file."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        ext = out_p.suffix.lower()

        if ext == ".csv":
            mode = "w" if is_first_chunk else "a"
            chunk.to_csv(output_path, mode=mode, header=is_first_chunk, index=False)

        elif ext in (".parquet", ".pq"):
            table = pa.Table.from_pandas(chunk)
            if is_first_chunk or self._parquet_writer is None:
                if self._parquet_writer is not None:
                    self._parquet_writer.close()
                self._parquet_writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
            self._parquet_writer.write_table(table)

        elif ext in (".jsonl", ".ndjson"):
            mode = "w" if is_first_chunk else "a"
            chunk.to_json(output_path, orient="records", lines=True, mode=mode)

        elif ext == ".json":
            # Appending standard JSON is done as JSON Lines or buffered
            mode = "w" if is_first_chunk else "a"
            chunk.to_json(output_path, orient="records", lines=True, mode=mode)

        elif ext in (".xlsx", ".xls"):
            # Excel does not support direct streaming append natively; handled per chunk or buffered
            mode = "w" if is_first_chunk else "a"
            with pd.ExcelWriter(output_path, engine="openpyxl", mode=mode) as writer:
                chunk.to_excel(writer, index=False)

        elif ext in (".txt", ".log"):
            mode = "w" if is_first_chunk else "a"
            with open(output_path, mode, encoding="utf-8") as f:
                for line in chunk.iloc[:, 0]:
                    f.write(f"{line}\n")

    def close_writers(self) -> None:
        """Flush and finalize active file writers (e.g., Parquet)."""
        if self._parquet_writer is not None:
            self._parquet_writer.close()
            self._parquet_writer = None

    def inspect_schema(self, file_path: str, sample_size: int = 100) -> pd.DataFrame:
        """Return sample preview dataframe for UI schema inspection."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".csv":
            return pd.read_csv(file_path, nrows=sample_size, dtype=str)
        elif ext in (".parquet", ".pq"):
            parquet_file = pq.ParquetFile(file_path)
            first_batch = next(parquet_file.iter_batches(batch_size=sample_size))
            return first_batch.to_pandas()
        elif ext in (".jsonl", ".ndjson"):
            return pd.read_json(file_path, lines=True, nrows=sample_size)
        elif ext == ".json":
            return pd.read_json(file_path).head(sample_size)
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(file_path, nrows=sample_size, dtype=str)
        elif ext in (".txt", ".log"):
            lines: List[str] = []
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(sample_size):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\r\n"))
            return pd.DataFrame({"line": lines})
        else:
            raise ValueError(f"Unsupported file format: {ext}")
