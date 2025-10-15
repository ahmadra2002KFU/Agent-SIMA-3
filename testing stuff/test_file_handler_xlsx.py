"""
Unit tests covering XLSX upload handling.
"""
import sys
import uuid
from pathlib import Path
import unittest

import pandas as pd
import pandas.testing as pdt

# Ensure the server modules are importable when running from repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from file_handler import FileHandler


class FileHandlerXLSXTests(unittest.TestCase):
    """Validate that XLSX files are normalised to CSV and loaded correctly."""

    def setUp(self):
        self.handler = FileHandler()
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)

        self.sample_df = pd.DataFrame(
            {
                "Name": ["Alice", "Bob", "Charlie"],
                "Age": [34, 28, 45],
                "City": ["Riyadh", "Jeddah", "Dammam"],
            }
        )
        self.xlsx_path = self.uploads_dir / f"{uuid.uuid4()}.xlsx"
        self.sample_df.to_excel(self.xlsx_path, index=False)

        self.addCleanup(self._cleanup)

    def _cleanup(self):
        """Remove any transient files produced during the test run."""
        self.handler.clear_current_file()
        if self.xlsx_path.exists():
            self.xlsx_path.unlink()
        csv_candidate = self.xlsx_path.with_suffix(".csv")
        if csv_candidate.exists():
            csv_candidate.unlink()

    def test_xlsx_conversion_creates_csv_and_preserves_data(self):
        """XLSX uploads should be converted to CSV with identical data."""
        self.assertTrue(self.xlsx_path.exists(), "Test XLSX file was not created")

        success = self.handler.set_current_file(str(self.xlsx_path), "sample.xlsx")
        self.assertTrue(success, "FileHandler failed to set the XLSX file as current")

        file_info = self.handler.get_current_file_info()
        self.assertIsNotNone(file_info, "File info should be available after upload")

        self.assertTrue(file_info["converted"], "Converted flag should be True for XLSX uploads")

        processed_path = Path(file_info["path"])
        self.assertTrue(processed_path.exists(), "Converted CSV file does not exist on disk")
        self.assertEqual(processed_path.suffix, ".csv", "Processed file should have .csv extension")

        # Ensure metadata matches expectations
        self.assertEqual(file_info["rows"], len(self.sample_df))
        self.assertEqual(file_info["columns"], len(self.sample_df.columns))

        # Dataframe content should match the original XLSX
        current_df = self.handler.current_file["dataframe"]
        pdt.assert_frame_equal(current_df, self.sample_df)


if __name__ == "__main__":
    unittest.main()
