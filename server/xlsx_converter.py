"""
Utility helpers for normalising Excel uploads into CSV files.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def convert_excel_to_csv(
    source_path: str,
    *,
    output_dir: Optional[Path] = None,
    sheet_name: Optional[str] = None,
) -> tuple[pd.DataFrame, str]:
    """
    Convert an Excel workbook into a CSV file and return the dataframe.

    Args:
        source_path: Path to the uploaded Excel file.
        output_dir: Directory where the generated CSV should be stored.
                    Defaults to the source file's parent directory.
        sheet_name: Optional sheet to load. Defaults to the first sheet.

    Returns:
        Tuple containing the in-memory dataframe and the generated CSV path.

    Raises:
        ValueError: If the Excel file cannot be read or the CSV cannot be written.
    """
    excel_path = Path(source_path)
    if output_dir is None:
        output_dir = excel_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Converting Excel file to CSV: %s", excel_path)

    sheet_to_load = 0 if sheet_name is None else sheet_name

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_to_load)
    except Exception as exc:
        logger.error("Failed to read Excel file '%s': %s", excel_path, exc)
        raise ValueError(f"Failed to read Excel file: {exc}") from exc

    csv_filename = f"{excel_path.stem}.csv"
    csv_path = output_dir / csv_filename

    try:
        df.to_csv(csv_path, index=False)
    except Exception as exc:
        logger.error("Failed to write CSV file '%s': %s", csv_path, exc)
        raise ValueError(f"Failed to write CSV file: {exc}") from exc

    logger.info("Excel conversion complete. CSV stored at %s", csv_path)

    return df, str(csv_path)
