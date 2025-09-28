"""
Enhanced Serialization Engine for AI Data Analysis Application

This module provides comprehensive serialization capabilities for all pandas data types,
eliminating JSON serialization errors and ensuring robust data handling.
"""

import json
import math
import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, time
from decimal import Decimal

logger = logging.getLogger(__name__)


class SerializationEngine:
    """
    Enhanced serialization engine that handles all pandas and numpy data types safely.
    Prevents JSON serialization errors by providing comprehensive type handling.
    """
    
    def __init__(self):
        self.serialization_stats = {
            'total_serialized': 0,
            'nat_values_handled': 0,
            'nan_values_handled': 0,
            'timestamp_values_handled': 0,
            'errors_handled': 0
        }
    
    def serialize_value(self, value: Any) -> Any:
        """
        Safely serialize any value for JSON output with comprehensive type handling.
        
        Args:
            value: Any value to serialize
            
        Returns:
            JSON-serializable value
        """
        self.serialization_stats['total_serialized'] += 1
        
        try:
            # Handle None and basic types (including numpy integers)
            if value is None or isinstance(value, (str, int, bool)):
                return value

            # Handle numpy integer types
            if hasattr(value, 'dtype') and 'int' in str(value.dtype):
                return int(value)

            # Handle numpy float types
            if hasattr(value, 'dtype') and 'float' in str(value.dtype):
                return float(value)
            
            # Handle float values (including NaN and infinity)
            if isinstance(value, float):
                return self._serialize_float(value)
            
            # Handle pandas NA values (including NaT) - but not DataFrames/Series
            if not isinstance(value, (pd.DataFrame, pd.Series)) and pd.isna(value):
                self.serialization_stats['nat_values_handled'] += 1
                return None
            
            # Handle collections
            if isinstance(value, (list, tuple)):
                return [self.serialize_value(item) for item in value]
            
            if isinstance(value, dict):
                return {k: self.serialize_value(v) for k, v in value.items()}
            
            # Handle pandas data types
            if isinstance(value, pd.DataFrame):
                return self._serialize_dataframe(value)
            
            if isinstance(value, pd.Series):
                return self._serialize_series(value)
            
            # Handle pandas timestamp types
            if self._is_pandas_timestamp(value):
                return self._serialize_timestamp(value)
            
            # Handle numpy arrays (but not pandas objects)
            if hasattr(value, 'tolist') and not isinstance(value, (pd.DataFrame, pd.Series)):
                return [self.serialize_value(item) for item in value.tolist()]
            
            # Handle datetime objects
            if isinstance(value, (datetime, date, time)):
                return self._serialize_datetime(value)
            
            # Handle Decimal
            if isinstance(value, Decimal):
                return float(value)
            
            # Handle plotly figures (but not pandas objects)
            if (hasattr(value, 'to_json') and hasattr(value, 'show') and
                not isinstance(value, (pd.DataFrame, pd.Series))):
                return self._serialize_plotly_figure(value)
            
            # Fallback to string representation
            return str(value)
            
        except Exception as e:
            self.serialization_stats['errors_handled'] += 1
            logger.warning(f"Serialization error for {type(value).__name__}: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
            return f"<Serialization Error: {type(value).__name__}>"
    
    def _serialize_float(self, value: float) -> Union[float, str, None]:
        """Handle float values including NaN and infinity."""
        if math.isnan(value):
            self.serialization_stats['nan_values_handled'] += 1
            return None
        elif math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        else:
            return value
    
    def _serialize_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Serialize pandas DataFrame with proper handling of all data types."""
        try:
            # Check if DataFrame is empty
            if len(df) == 0:
                return {
                    'type': 'dataframe',
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'head': [],
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
                }

            # Serialize each row individually to handle mixed data types
            records = []
            sample_df = df.head(10)  # Limit to first 10 rows

            for idx in range(len(sample_df)):
                record = {}
                for col in sample_df.columns:
                    val = sample_df.iloc[idx][col]
                    record[col] = self.serialize_value(val)
                records.append(record)

            return {
                'type': 'dataframe',
                'shape': df.shape,
                'columns': list(df.columns),
                'head': records,
                'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
        except Exception as e:
            logger.error(f"DataFrame serialization error: {e}")
            return {
                'type': 'dataframe',
                'error': f"Serialization failed: {str(e)}",
                'shape': getattr(df, 'shape', 'unknown'),
                'columns': getattr(df, 'columns', []).tolist() if hasattr(df, 'columns') else []
            }
    
    def _serialize_series(self, series: pd.Series) -> Dict[str, Any]:
        """Serialize pandas Series with proper handling of all data types."""
        try:
            values = [self.serialize_value(val) for val in series.head(10)]
            return {
                'type': 'series',
                'name': series.name,
                'length': len(series),
                'dtype': str(series.dtype),
                'head': values
            }
        except Exception as e:
            logger.error(f"Series serialization error: {e}")
            return {
                'type': 'series',
                'error': f"Serialization failed: {str(e)}",
                'name': getattr(series, 'name', 'unknown')
            }
    
    def _is_pandas_timestamp(self, value: Any) -> bool:
        """Check if value is a pandas timestamp type."""
        return (
            hasattr(value, 'isoformat') or
            str(type(value)).startswith("<class 'pandas._libs.tslibs") or
            isinstance(value, pd.Timestamp)
        )
    
    def _serialize_timestamp(self, value: Any) -> Optional[str]:
        """Serialize pandas timestamp values safely."""
        try:
            self.serialization_stats['timestamp_values_handled'] += 1
            
            # Handle pandas Timestamp
            if isinstance(value, pd.Timestamp):
                if pd.isna(value):
                    return None
                return value.isoformat()
            
            # Handle other timestamp types
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            
            # Handle string representations
            str_value = str(value)
            if str_value in ['NaT', 'NaN', 'nan', 'None']:
                return None
            
            return str_value
            
        except (ValueError, AttributeError, TypeError):
            return None
    
    def _serialize_datetime(self, value: Union[datetime, date, time]) -> str:
        """Serialize datetime objects."""
        try:
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return str(value)
        except Exception:
            return str(value)
    
    def _serialize_plotly_figure(self, figure: Any) -> Dict[str, Any]:
        """Serialize plotly figures safely."""
        try:
            return {
                'type': 'plotly_figure',
                'json': figure.to_json(),
                'html': figure.to_html(include_plotlyjs='cdn') if hasattr(figure, 'to_html') else None
            }
        except Exception as e:
            logger.error(f"Plotly figure serialization error: {e}")
            return {
                'type': 'plotly_figure',
                'error': f"Serialization failed: {str(e)}"
            }
    
    def serialize_execution_results(self, results: Dict[str, Any]) -> str:
        """
        Safely serialize execution results to JSON string.
        
        Args:
            results: Dictionary containing execution results
            
        Returns:
            JSON string representation
        """
        try:
            serialized_results = {}
            for key, value in results.items():
                serialized_results[key] = self.serialize_value(value)
            
            return json.dumps(serialized_results, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Execution results serialization error: {e}")
            # Fallback to string representation
            return json.dumps({
                'serialization_error': str(e),
                'raw_results': str(results)
            }, indent=2)
    
    def get_stats(self) -> Dict[str, int]:
        """Get serialization statistics."""
        return self.serialization_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset serialization statistics."""
        for key in self.serialization_stats:
            self.serialization_stats[key] = 0


# Global serialization engine instance
serialization_engine = SerializationEngine()
