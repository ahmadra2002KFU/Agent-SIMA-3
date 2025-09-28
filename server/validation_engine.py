"""
Validation Engine for AI Data Analysis Application

This module provides comprehensive validation for LLM responses, generated code,
and execution results to prevent corruption and ensure system reliability.
"""

import ast
import json
import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_content: Optional[str] = None


class ValidationEngine:
    """
    Comprehensive validation engine for all system components.
    Ensures data integrity and prevents corruption before streaming.
    """
    
    def __init__(self):
        self.validation_stats = {
            'json_validations': 0,
            'code_validations': 0,
            'response_validations': 0,
            'validation_failures': 0,
            'auto_fixes_applied': 0
        }
    
    def validate_json_response(self, json_text: str) -> ValidationResult:
        """
        Validate and clean JSON response from LLM.
        
        Args:
            json_text: Raw JSON text from LLM
            
        Returns:
            ValidationResult with validation status and cleaned content
        """
        self.validation_stats['json_validations'] += 1
        errors = []
        warnings = []
        cleaned_content = None
        
        try:
            # Basic JSON structure validation
            if not json_text.strip():
                errors.append("Empty JSON response")
                return ValidationResult(False, errors, warnings)
            
            # Check for basic JSON structure
            if not (json_text.strip().startswith('{') and json_text.strip().endswith('}')):
                errors.append("Invalid JSON structure - missing braces")
                # Try to fix by adding braces
                cleaned_text = self._fix_json_structure(json_text)
                if cleaned_text:
                    json_text = cleaned_text
                    warnings.append("Auto-fixed JSON structure")
                    self.validation_stats['auto_fixes_applied'] += 1
                else:
                    return ValidationResult(False, errors, warnings)
            
            # Validate JSON parsing
            try:
                parsed = json.loads(json_text)
                cleaned_content = json_text
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
                fixed_json = self._fix_json_errors(json_text)
                if fixed_json:
                    try:
                        parsed = json.loads(fixed_json)
                        cleaned_content = fixed_json
                        warnings.append(f"Auto-fixed JSON error: {str(e)}")
                        self.validation_stats['auto_fixes_applied'] += 1
                    except json.JSONDecodeError:
                        errors.append(f"JSON parsing failed: {str(e)}")
                        return ValidationResult(False, errors, warnings)
                else:
                    errors.append(f"JSON parsing failed: {str(e)}")
                    return ValidationResult(False, errors, warnings)
            
            # Validate required fields
            required_fields = ['initial_response', 'generated_code', 'result_commentary']
            for field in required_fields:
                if field not in parsed:
                    errors.append(f"Missing required field: {field}")
                elif not isinstance(parsed[field], str):
                    errors.append(f"Field {field} must be a string")
            
            if errors:
                return ValidationResult(False, errors, warnings, cleaned_content)
            
            return ValidationResult(True, errors, warnings, cleaned_content)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            self.validation_stats['validation_failures'] += 1
            return ValidationResult(False, errors, warnings)
    
    def validate_python_code(self, code: str) -> ValidationResult:
        """
        Validate Python code for syntax and security.
        
        Args:
            code: Python code to validate
            
        Returns:
            ValidationResult with validation status and cleaned code
        """
        self.validation_stats['code_validations'] += 1
        errors = []
        warnings = []
        cleaned_content = code
        
        try:
            if not code.strip():
                return ValidationResult(True, errors, warnings, cleaned_content)
            
            # Only clean escape sequences if there are obvious corruption indicators
            if self._has_corruption_indicators(code):
                cleaned_code = self._clean_escape_sequences(code)
                if cleaned_code != code:
                    warnings.append("Cleaned escape sequences in code")
                    cleaned_content = cleaned_code
                    self.validation_stats['auto_fixes_applied'] += 1
            
            # Syntax validation
            try:
                ast.parse(cleaned_content)
            except SyntaxError as e:
                # Try to fix common syntax issues
                fixed_code = self._fix_syntax_errors(cleaned_content)
                if fixed_code:
                    try:
                        ast.parse(fixed_code)
                        cleaned_content = fixed_code
                        warnings.append(f"Auto-fixed syntax error: {str(e)}")
                        self.validation_stats['auto_fixes_applied'] += 1
                    except SyntaxError:
                        errors.append(f"Syntax error: {str(e)}")
                        return ValidationResult(False, errors, warnings, cleaned_content)
                else:
                    errors.append(f"Syntax error: {str(e)}")
                    return ValidationResult(False, errors, warnings, cleaned_content)
            
            # Security validation
            security_result = self._validate_code_security(cleaned_content)
            if not security_result.is_valid:
                errors.extend(security_result.errors)
                return ValidationResult(False, errors, warnings, cleaned_content)
            
            warnings.extend(security_result.warnings)
            
            return ValidationResult(True, errors, warnings, cleaned_content)
            
        except Exception as e:
            errors.append(f"Code validation error: {str(e)}")
            self.validation_stats['validation_failures'] += 1
            return ValidationResult(False, errors, warnings, cleaned_content)
    
    def validate_structured_response(self, response: Dict[str, str]) -> ValidationResult:
        """
        Validate complete structured response from LLM.
        
        Args:
            response: Dictionary with initial_response, generated_code, result_commentary
            
        Returns:
            ValidationResult with overall validation status
        """
        self.validation_stats['response_validations'] += 1
        errors = []
        warnings = []
        
        try:
            # Validate each field
            for field_name, content in response.items():
                if field_name == 'generated_code' and content.strip():
                    code_result = self.validate_python_code(content)
                    if not code_result.is_valid:
                        errors.extend([f"Code validation: {err}" for err in code_result.errors])
                    warnings.extend([f"Code validation: {warn}" for warn in code_result.warnings])
                
                # Check for corruption indicators
                if self._has_corruption_indicators(content):
                    warnings.append(f"Potential corruption detected in {field_name}")
            
            is_valid = len(errors) == 0
            return ValidationResult(is_valid, errors, warnings)
            
        except Exception as e:
            errors.append(f"Response validation error: {str(e)}")
            self.validation_stats['validation_failures'] += 1
            return ValidationResult(False, errors, warnings)
    
    def _fix_json_structure(self, json_text: str) -> Optional[str]:
        """Attempt to fix basic JSON structure issues."""
        try:
            text = json_text.strip()
            
            # Add missing opening brace
            if not text.startswith('{'):
                text = '{' + text
            
            # Add missing closing brace
            if not text.endswith('}'):
                text = text + '}'
            
            # Test if it's valid now
            json.loads(text)
            return text
            
        except Exception:
            return None
    
    def _fix_json_errors(self, json_text: str) -> Optional[str]:
        """Attempt to fix common JSON errors."""
        try:
            text = json_text
            
            # Fix trailing commas
            text = re.sub(r',(\s*[}\]])', r'\1', text)
            
            # Fix unescaped quotes in strings
            text = re.sub(r'(?<!\\)"(?=.*")', r'\\"', text)
            
            # Fix newlines in strings
            text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            
            # Test if it's valid now
            json.loads(text)
            return text
            
        except Exception:
            return None
    
    def _clean_escape_sequences(self, code: str) -> str:
        """Clean corrupted escape sequences in code."""
        try:
            # Fix common escape sequence corruption
            cleaned = code
            
            # Fix corrupted newlines
            cleaned = re.sub(r'\\n(?!["\'])', '\n', cleaned)
            
            # Fix corrupted tabs
            cleaned = re.sub(r'\\t(?!["\'])', '\t', cleaned)
            
            # Fix corrupted quotes
            cleaned = re.sub(r'\\"(?!["\'])', '"', cleaned)
            
            # Remove duplicate brackets/parentheses
            cleaned = re.sub(r'(\]\s*\]|\)\s*\))', lambda m: m.group(0)[0], cleaned)
            
            return cleaned
            
        except Exception:
            return code
    
    def _fix_syntax_errors(self, code: str) -> Optional[str]:
        """Attempt to fix common syntax errors."""
        try:
            lines = code.split('\n')
            fixed_lines = []
            
            for line in lines:
                # Skip obviously corrupted lines
                if re.search(r'[^\w\s\[\](){}.,=+\-*/<>!&|:;"\'\\]', line):
                    continue
                
                # Fix incomplete assignments
                if '=' in line and not line.strip().endswith(('=', '==', '!=', '<=', '>=')):
                    fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            
            fixed_code = '\n'.join(fixed_lines)
            
            # Test if it's valid now
            ast.parse(fixed_code)
            return fixed_code
            
        except Exception:
            return None
    
    def _validate_code_security(self, code: str) -> ValidationResult:
        """Validate code for security issues."""
        errors = []
        warnings = []
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'\bexec\s*\(',
            r'\beval\s*\(',
            r'\b__import__\s*\(',
            r'\bopen\s*\(',
            r'\bfile\s*\(',
            r'\bos\.',
            r'\bsys\.',
            r'\bsubprocess\.',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                errors.append(f"Dangerous operation detected: {pattern}")
        
        # Check for file operations
        if re.search(r'\b(read|write|delete|remove)\b.*\.(csv|xlsx|txt|json)', code, re.IGNORECASE):
            warnings.append("File operation detected - ensure it's safe")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings)
    
    def _has_corruption_indicators(self, content: str) -> bool:
        """Check for indicators of content corruption."""
        corruption_patterns = [
            r'\\n(?!["\'])',      # Unescaped newlines (not in strings)
            r'\\t(?!["\'])',      # Unescaped tabs (not in strings)
            r'\]\s+\]',           # Duplicate brackets with space
            r'\)\s+\)',           # Duplicate parentheses with space
            r'n\\f\[',            # Specific corruption pattern from original issue
            r'== \d+\] == \d+\]', # Specific pattern from original error
        ]

        for pattern in corruption_patterns:
            if re.search(pattern, content):
                return True

        return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        for key in self.validation_stats:
            self.validation_stats[key] = 0


# Global validation engine instance
validation_engine = ValidationEngine()
