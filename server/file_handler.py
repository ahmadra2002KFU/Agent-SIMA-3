"""
File upload and processing handler for CSV and XLSX files.
"""
import os
import uuid
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from metadata_extractor import metadata_extractor

logger = logging.getLogger(__name__)

# Directory to store uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}


class FileHandler:
    """Handles file upload, validation, and basic processing."""
    
    def __init__(self):
        self.current_file: Optional[Dict[str, Any]] = None
    
    def validate_file(self, filename: str, file_size: int) -> tuple[bool, str]:
        """
        Validate uploaded file.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        
        return True, ""
    
    async def save_uploaded_file(self, filename: str, file_content: bytes) -> tuple[bool, str, Optional[str]]:
        """
        Save uploaded file to disk.
        
        Args:
            filename: Original filename
            file_content: File content as bytes
            
        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            # Validate file
            is_valid, error_msg = self.validate_file(filename, len(file_content))
            if not is_valid:
                return False, error_msg, None
            
            # Generate unique filename
            file_ext = Path(filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return True, "File uploaded successfully", str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, f"Error saving file: {str(e)}", None
    
    def load_file_data(self, file_path: str) -> tuple[bool, str, Optional[pd.DataFrame]]:
        """
        Load data from uploaded file.
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Tuple of (success, message, dataframe)
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.csv':
                # Try different encodings for CSV files
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return False, "Could not decode CSV file with any supported encoding", None
                    
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                return False, f"Unsupported file extension: {file_ext}", None
            
            logger.info(f"Loaded data: {df.shape[0]} rows, {df.shape[1]} columns")
            return True, "File loaded successfully", df
            
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False, f"Error loading file: {str(e)}", None
    
    def set_current_file(self, file_path: str, original_filename: str) -> bool:
        """
        Set the current active file for the session.
        
        Args:
            file_path: Path to the uploaded file
            original_filename: Original filename
            
        Returns:
            Success status
        """
        try:
            success, message, df = self.load_file_data(file_path)
            if not success:
                return False
            
            # Extract metadata
            metadata = metadata_extractor.extract_metadata(df, original_filename)

            self.current_file = {
                'path': file_path,
                'original_filename': original_filename,
                'dataframe': df,
                'metadata': metadata,
                'upload_time': pd.Timestamp.now()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting current file: {e}")
            return False
    
    def get_current_file_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current active file."""
        if not self.current_file:
            return None

        df = self.current_file['dataframe']

        return {
            'filename': self.current_file['original_filename'],
            'path': self.current_file['path'],
            'upload_time': self.current_file['upload_time'].isoformat(),
            'rows': len(df),
            'columns': len(df.columns),
            'size_mb': round(os.path.getsize(self.current_file['path']) / (1024 * 1024), 2)
        }

    def get_current_file_metadata(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive metadata about the current active file."""
        if not self.current_file:
            return None

        return self.current_file.get('metadata', {})
    
    def clear_current_file(self):
        """Clear the current file from memory."""
        if self.current_file and os.path.exists(self.current_file['path']):
            try:
                os.remove(self.current_file['path'])
                logger.info(f"Deleted file: {self.current_file['path']}")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
        
        self.current_file = None


# Global file handler instance
file_handler = FileHandler()
