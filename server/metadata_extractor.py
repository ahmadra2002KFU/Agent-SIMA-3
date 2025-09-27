"""
Metadata extraction layer for uploaded data files.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract comprehensive metadata from pandas DataFrames."""
    
    def __init__(self):
        pass
    
    def extract_metadata(self, df: pd.DataFrame, filename: str = "") -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a DataFrame.
        
        Args:
            df: pandas DataFrame to analyze
            filename: Original filename for reference
            
        Returns:
            Dictionary containing comprehensive metadata
        """
        try:
            metadata = {
                "basic_info": self._get_basic_info(df, filename),
                "columns": self._get_column_metadata(df),
                "numeric_summary": self._get_numeric_summary(df),
                "categorical_summary": self._get_categorical_summary(df),
                "data_quality": self._get_data_quality_indicators(df),
                "sample_data": self._get_sample_data(df)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {"error": str(e)}
    
    def _get_basic_info(self, df: pd.DataFrame, filename: str) -> Dict[str, Any]:
        """Get basic information about the dataset."""
        return {
            "filename": filename,
            "shape": {
                "rows": len(df),
                "columns": len(df.columns)
            },
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    
    def _get_column_metadata(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Get detailed metadata for each column."""
        column_metadata = {}
        
        for col in df.columns:
            col_data = df[col]
            
            # Basic column info
            col_info = {
                "dtype": str(col_data.dtype),
                "non_null_count": int(col_data.count()),
                "null_count": int(col_data.isnull().sum()),
                "null_percentage": round((col_data.isnull().sum() / len(df)) * 100, 2),
                "unique_count": int(col_data.nunique()),
                "unique_percentage": round((col_data.nunique() / len(df)) * 100, 2)
            }
            
            # Type-specific analysis
            if pd.api.types.is_numeric_dtype(col_data):
                col_info.update(self._analyze_numeric_column(col_data))
            elif pd.api.types.is_datetime64_any_dtype(col_data):
                col_info.update(self._analyze_datetime_column(col_data))
            else:
                col_info.update(self._analyze_text_column(col_data))
            
            column_metadata[col] = col_info
        
        return column_metadata
    
    def _analyze_numeric_column(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze numeric column."""
        try:
            stats = series.describe()
            return {
                "column_type": "numeric",
                "min": float(stats['min']) if not pd.isna(stats['min']) else None,
                "max": float(stats['max']) if not pd.isna(stats['max']) else None,
                "mean": float(stats['mean']) if not pd.isna(stats['mean']) else None,
                "median": float(stats['50%']) if not pd.isna(stats['50%']) else None,
                "std": float(stats['std']) if not pd.isna(stats['std']) else None,
                "q25": float(stats['25%']) if not pd.isna(stats['25%']) else None,
                "q75": float(stats['75%']) if not pd.isna(stats['75%']) else None,
                "has_negative": bool((series < 0).any()),
                "has_zero": bool((series == 0).any()),
                "outliers_count": self._count_outliers(series)
            }
        except Exception as e:
            logger.warning(f"Error analyzing numeric column: {e}")
            return {"column_type": "numeric", "error": str(e)}
    
    def _analyze_datetime_column(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze datetime column."""
        try:
            return {
                "column_type": "datetime",
                "min_date": str(series.min()) if not pd.isna(series.min()) else None,
                "max_date": str(series.max()) if not pd.isna(series.max()) else None,
                "date_range_days": (series.max() - series.min()).days if not pd.isna(series.min()) else None
            }
        except Exception as e:
            logger.warning(f"Error analyzing datetime column: {e}")
            return {"column_type": "datetime", "error": str(e)}
    
    def _analyze_text_column(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze text/categorical column."""
        try:
            # Get top values
            value_counts = series.value_counts().head(10)
            top_values = [{"value": str(val), "count": int(count)} 
                         for val, count in value_counts.items()]
            
            # Calculate text statistics if it's string data
            text_stats = {}
            if series.dtype == 'object':
                str_series = series.astype(str)
                text_stats = {
                    "avg_length": round(str_series.str.len().mean(), 2),
                    "min_length": int(str_series.str.len().min()),
                    "max_length": int(str_series.str.len().max())
                }
            
            return {
                "column_type": "categorical",
                "top_values": top_values,
                "is_likely_categorical": series.nunique() / len(series) < 0.5,
                **text_stats
            }
        except Exception as e:
            logger.warning(f"Error analyzing text column: {e}")
            return {"column_type": "categorical", "error": str(e)}
    
    def _count_outliers(self, series: pd.Series) -> int:
        """Count outliers using IQR method."""
        try:
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            return int(((series < lower_bound) | (series > upper_bound)).sum())
        except:
            return 0
    
    def _get_numeric_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics for all numeric columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return {"message": "No numeric columns found"}
        
        summary = {}
        for col in numeric_cols:
            try:
                stats = df[col].describe()
                summary[col] = {
                    "count": int(stats['count']),
                    "mean": float(stats['mean']),
                    "std": float(stats['std']),
                    "min": float(stats['min']),
                    "25%": float(stats['25%']),
                    "50%": float(stats['50%']),
                    "75%": float(stats['75%']),
                    "max": float(stats['max'])
                }
            except Exception as e:
                summary[col] = {"error": str(e)}
        
        return summary
    
    def _get_categorical_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary for categorical columns."""
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        
        if len(categorical_cols) == 0:
            return {"message": "No categorical columns found"}
        
        summary = {}
        for col in categorical_cols:
            try:
                value_counts = df[col].value_counts().head(10)
                summary[col] = {
                    "unique_count": int(df[col].nunique()),
                    "most_frequent": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                    "most_frequent_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    "top_values": [{"value": str(val), "count": int(count)} 
                                 for val, count in value_counts.items()]
                }
            except Exception as e:
                summary[col] = {"error": str(e)}
        
        return summary
    
    def _get_data_quality_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get data quality indicators."""
        try:
            total_cells = df.shape[0] * df.shape[1]
            missing_cells = df.isnull().sum().sum()
            
            # Duplicate rows
            duplicate_rows = df.duplicated().sum()
            
            # Columns with high missing data
            high_missing_cols = []
            for col in df.columns:
                missing_pct = (df[col].isnull().sum() / len(df)) * 100
                if missing_pct > 50:
                    high_missing_cols.append({"column": col, "missing_percentage": round(missing_pct, 2)})
            
            # Potential issues
            issues = []
            if missing_cells / total_cells > 0.1:
                issues.append("High missing data percentage (>10%)")
            if duplicate_rows > 0:
                issues.append(f"{duplicate_rows} duplicate rows found")
            if len(high_missing_cols) > 0:
                issues.append(f"{len(high_missing_cols)} columns with >50% missing data")
            
            return {
                "total_cells": total_cells,
                "missing_cells": int(missing_cells),
                "missing_percentage": round((missing_cells / total_cells) * 100, 2),
                "duplicate_rows": int(duplicate_rows),
                "high_missing_columns": high_missing_cols,
                "data_quality_score": max(0, 100 - (missing_cells / total_cells) * 100 - (duplicate_rows / len(df)) * 10),
                "potential_issues": issues
            }
        except Exception as e:
            logger.error(f"Error calculating data quality indicators: {e}")
            return {"error": str(e)}
    
    def _get_sample_data(self, df: pd.DataFrame, n_rows: int = 5) -> Dict[str, Any]:
        """Get sample data from the dataset."""
        try:
            return {
                "head": df.head(n_rows).to_dict('records'),
                "tail": df.tail(n_rows).to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error getting sample data: {e}")
            return {"error": str(e)}


# Global metadata extractor instance
metadata_extractor = MetadataExtractor()
