"""
Sandboxed Python code execution environment for LLM-generated code.
"""
import sys
import io
import traceback
import contextlib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.io as pio
from plotly.subplots import make_subplots
import json
import base64
from typing import Dict, Any, Optional, Tuple, List
import logging
import ast

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Execute Python code in a controlled environment."""
    
    def __init__(self):
        self.allowed_modules = {
            'pandas': pd,
            'pd': pd,
            'numpy': np,
            'np': np,
            'plotly.express': px,
            'px': px,
            'plotly.graph_objects': go,
            'go': go,
            'plotly.figure_factory': ff,
            'ff': ff,
            'plotly.subplots': make_subplots,
            'make_subplots': make_subplots,
            'json': json,
            'base64': base64
        }

        # Prevent Plotly from opening browser windows/tabs during code execution
        try:
            pio.renderers.default = 'json'
            def _noop_show(*args, **kwargs):
                return None
            # Patch figure.show to no-op (covers fig.show())
            go.Figure.show = _noop_show
        except Exception:
            pass

        # Built-in functions that are safe to use
        self.allowed_builtins = {
            'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'sum',
            'min', 'max', 'abs', 'round', 'int', 'float', 'str', 'bool', 'list',
            'dict', 'tuple', 'set', 'type', 'isinstance', 'hasattr', 'getattr',
            'print', 'format', '__import__'
        }
    
    def execute_code(
        self,
        code: str,
        dataframe: Optional[pd.DataFrame] = None,
        timeout: int = 30
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute Python code in a sandboxed environment with enhanced validation.

        Args:
            code: Python code to execute
            dataframe: Optional DataFrame to make available as 'df'
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (success, output/error, results_dict)
        """
        try:
            # Pre-execution validation with auto-fix
            validated_code, validation_warnings = self._validate_and_fix_code(code)
            if validated_code is None:
                return False, "Code validation failed: Unable to fix syntax errors", None

            # Use validated code for execution
            code_to_execute = validated_code

            # Capture stdout and stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Create execution namespace
            namespace = self._create_namespace(dataframe)

            # Results dictionary to capture variables
            results = {}

            try:
                # Redirect output
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                # Execute the validated code
                exec(code_to_execute, namespace)

                # Capture important variables from namespace
                results = self._extract_results(namespace)

                # Get output
                output = stdout_capture.getvalue()
                error_output = stderr_capture.getvalue()

                # Add validation warnings to output if any
                if validation_warnings:
                    output = f"Validation Warnings:\n" + "\n".join(validation_warnings) + "\n\n" + output

                if error_output:
                    output += f"\nErrors/Warnings:\n{error_output}"

                return True, output, results

            except Exception as e:
                error_msg = f"Execution Error: {str(e)}\n{traceback.format_exc()}"
                return False, error_msg, None

            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return False, f"Execution setup failed: {str(e)}", None

    def _validate_and_fix_code(self, code: str) -> Tuple[Optional[str], List[str]]:
        """
        Validate and auto-fix code before execution.

        Args:
            code: Python code to validate and fix

        Returns:
            Tuple of (validated_code, warnings_list)
        """
        try:
            # Import validation engine
            from validation_engine import ValidationEngine

            validation_engine = ValidationEngine()
            validation_result = validation_engine.validate_python_code(code)

            if validation_result.is_valid:
                # Code is valid, return cleaned version if available
                cleaned_code = validation_result.cleaned_content or code
                return cleaned_code, validation_result.warnings
            else:
                # Code has errors, check if auto-fix was applied
                if validation_result.cleaned_content:
                    # Auto-fix was attempted, try to validate the fixed version
                    fixed_result = validation_engine.validate_python_code(validation_result.cleaned_content)
                    if fixed_result.is_valid:
                        warnings = validation_result.warnings + [f"Auto-fixed: {err}" for err in validation_result.errors]
                        return validation_result.cleaned_content, warnings

                # Unable to fix, log errors and return None
                logger.error(f"Code validation failed: {validation_result.errors}")
                return None, validation_result.warnings

        except ImportError:
            # Fallback to basic validation if validation engine not available
            logger.warning("ValidationEngine not available, using basic validation")
            return self._basic_code_validation(code)
        except Exception as e:
            logger.error(f"Code validation error: {e}")
            return self._basic_code_validation(code)

    def _basic_code_validation(self, code: str) -> Tuple[Optional[str], List[str]]:
        """
        Basic code validation fallback.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (validated_code, warnings_list)
        """
        try:
            # Basic syntax check
            ast.parse(code)
            return code, []
        except SyntaxError as e:
            # Try basic trailing backslash fix
            if "unexpected EOF while parsing" in str(e):
                fixed_code = self._fix_basic_trailing_backslash(code)
                if fixed_code:
                    try:
                        ast.parse(fixed_code)
                        return fixed_code, ["Fixed trailing backslash syntax error"]
                    except SyntaxError:
                        pass

            logger.error(f"Basic code validation failed: {e}")
            return None, [f"Syntax error: {str(e)}"]

    def _fix_basic_trailing_backslash(self, code: str) -> Optional[str]:
        """
        Basic fix for trailing backslash issues.

        Args:
            code: Python code with potential trailing backslash

        Returns:
            Fixed code or None if unable to fix
        """
        try:
            lines = code.split('\n')
            fixed_lines = []

            for line in lines:
                stripped = line.rstrip()
                if stripped.endswith('\\') and (stripped.rstrip('\\').strip().endswith(('}', ']', ')'))):
                    # Remove trailing backslash from complete structures
                    fixed_line = stripped[:-1].rstrip()
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * indent + fixed_line)
                else:
                    fixed_lines.append(line)

            return '\n'.join(fixed_lines)

        except Exception:
            return None
    
    def _create_namespace(self, dataframe: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Create a safe execution namespace."""
        import builtins

        # Create safe builtins dictionary
        safe_builtins = {}
        for name in self.allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)

        # Add safe __import__ function
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            allowed_imports = {
                'pandas', 'numpy', 'plotly.express', 'plotly.graph_objects',
                'plotly.figure_factory', 'plotly.subplots', 'json', 'base64',
                'datetime', 'time', 'calendar', 'math', 'statistics', 'random',
                'collections', 'itertools', 'functools', 're', 'string',
                'decimal', 'fractions', 'operator', 'copy', 'pickle',
                'csv', 'io', 'pathlib', 'urllib.parse', 'hashlib',
                'matplotlib.pyplot', 'matplotlib', 'seaborn', 'scipy',
                'sklearn', 'warnings', 'typing', '_strptime', '_datetime',
                'locale', 'struct', 'binascii', 'codecs'
            }

            if name in allowed_imports:
                return __import__(name, globals, locals, fromlist, level)
            else:
                raise ImportError(f"Import of '{name}' is not allowed")

        safe_builtins['__import__'] = safe_import

        namespace = {
            '__builtins__': safe_builtins
        }

        # Add allowed modules
        namespace.update(self.allowed_modules)

        # Add dataframe if provided
        if dataframe is not None:
            namespace['df'] = dataframe.copy()  # Use a copy to prevent modification

        return namespace
    
    def _extract_results(self, namespace: Dict[str, Any]) -> Dict[str, Any]:
        """Extract important results from the execution namespace."""
        results = {}
        
        # Look for common result variables
        result_vars = ['result', 'output', 'fig', 'figure', 'plot', 'chart', 'summary', 'analysis']
        
        for var_name in result_vars:
            if var_name in namespace:
                value = namespace[var_name]
                results[var_name] = self._serialize_value(value)
        
        # Look for any plotly figures
        for name, value in namespace.items():
            if hasattr(value, 'to_json') and hasattr(value, 'show'):  # Likely a plotly figure
                results[f'plotly_figure_{name}'] = {
                    'type': 'plotly_figure',
                    'json': value.to_json(),
                    'html': value.to_html(include_plotlyjs='cdn')
                }
        
        # Look for DataFrames
        for name, value in namespace.items():
            if isinstance(value, pd.DataFrame) and name != 'df':  # Exclude original df
                # Convert DataFrame to dict with proper serialization
                df_records = []
                for _, row in value.head().iterrows():
                    record = {}
                    for col, val in row.items():
                        record[col] = self._serialize_value(val)
                    df_records.append(record)

                results[f'dataframe_{name}'] = {
                    'type': 'dataframe',
                    'shape': value.shape,
                    'columns': list(value.columns),
                    'head': df_records,
                    'dtypes': {col: str(dtype) for col, dtype in value.dtypes.items()}
                }
        
        return results
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON output."""
        import math

        try:
            if isinstance(value, (str, int, bool, type(None))):
                return value
            elif isinstance(value, float):
                # Handle NaN and infinity values
                if math.isnan(value):
                    return None
                elif math.isinf(value):
                    return "Infinity" if value > 0 else "-Infinity"
                else:
                    return value
            elif isinstance(value, (list, tuple)):
                return [self._serialize_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: self._serialize_value(v) for k, v in value.items()}
            elif isinstance(value, pd.DataFrame):
                # Convert DataFrame to dict with NaN handling
                df_dict = value.head().fillna("null").to_dict('records')
                return {
                    'type': 'dataframe',
                    'shape': value.shape,
                    'columns': list(value.columns),
                    'head': df_dict
                }
            elif hasattr(value, 'to_json'):  # Plotly figure
                return {
                    'type': 'plotly_figure',
                    'json': value.to_json()
                }
            elif hasattr(value, 'tolist'):  # NumPy array
                return [self._serialize_value(item) for item in value.tolist()]
            elif pd.isna(value):  # Handle pandas NaT and other pandas NA values
                return None
            elif hasattr(value, 'isoformat'):  # Pandas Timestamp or datetime
                try:
                    return value.isoformat()
                except (ValueError, AttributeError):
                    # Handle invalid timestamps or NaT values
                    return None
            elif str(type(value)).startswith("<class 'pandas._libs.tslibs"):  # Pandas timestamp types
                try:
                    # Try to convert to string, but handle NaT values
                    str_value = str(value)
                    if str_value in ['NaT', 'NaN', 'nan']:
                        return None
                    return str_value
                except Exception:
                    return None
            else:
                return str(value)
        except Exception as e:
            logger.warning(f"Failed to serialize value of type {type(value).__name__}: {e}")
            return f"<Unable to serialize {type(value).__name__}>"
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate code for basic safety checks.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        # List of dangerous operations to block
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess', 'import shutil',
            'open(', 'file(', 'exec(', 'eval(',
            'globals()', 'locals()', 'vars()', 'dir()',
            'getattr(', 'setattr(', 'delattr(',
            'input(', 'raw_input('
        ]

        # Allow safe imports
        safe_imports = [
            'import pandas', 'import numpy', 'import plotly', 'import json',
            'from pandas', 'from numpy', 'from plotly', 'from json',
            'import datetime', 'import time', 'import calendar', 'import math',
            'import statistics', 'import random', 'import collections', 'import itertools',
            'import functools', 'import re', 'import string', 'import decimal',
            'import fractions', 'import operator', 'import copy', 'import pickle',
            'import csv', 'import io', 'import pathlib', 'import warnings',
            'from datetime', 'from time', 'from calendar', 'from math',
            'from statistics', 'from random', 'from collections', 'from itertools',
            'from functools', 'from re', 'from string', 'from decimal',
            'from fractions', 'from operator', 'from copy', 'from csv',
            'from io', 'from pathlib', 'from warnings', 'from typing'
        ]
        
        code_lower = code.lower()

        # Check if any dangerous patterns are present, but exclude safe imports
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                # Check if this is part of a safe import
                is_safe_import = any(safe_import in code_lower for safe_import in safe_imports)
                if not is_safe_import:
                    return False, f"Potentially dangerous operation detected: {pattern}"
        
        # Check for file system operations
        if any(op in code_lower for op in ['remove', 'delete', 'rmdir', 'unlink']):
            return False, "File system modification operations are not allowed"
        
        # Check for network operations
        if any(op in code_lower for op in ['urllib', 'requests', 'socket', 'http']):
            return False, "Network operations are not allowed"
        
        return True, ""


# Global code executor instance
code_executor = CodeExecutor()
