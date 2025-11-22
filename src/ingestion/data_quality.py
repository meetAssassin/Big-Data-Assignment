"""
Data Quality Utilities for handling malformed records, encoding issues, and data cleaning.
"""
import re
import chardet
from typing import Any, Dict, List, Optional


def detect_encoding_safe(file_path: str, sample_size: int = 10000) -> str:
    """
    Safely detect file encoding with fallback options.
    
    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample for detection
        
    Returns:
        Detected encoding string
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            
            # Common fallbacks
            if encoding is None:
                return 'utf-8'
            if encoding.lower() in ['ascii', 'us-ascii']:
                return 'utf-8'
            if encoding.lower() == 'windows-1252':
                return 'latin-1'
                
            return encoding
    except Exception:
        return 'utf-8'


def clean_string(value: Any) -> str:
    """
    Clean string values by removing control characters and normalizing whitespace.
    
    Args:
        value: Value to clean
        
    Returns:
        Cleaned string
    """
    if value is None:
        return ""
    
    # Convert to string
    str_value = str(value)
    
    # Remove control characters except newlines and tabs
    str_value = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', str_value)
    
    # Normalize whitespace
    str_value = ' '.join(str_value.split())
    
    return str_value.strip()


def fix_malformed_json_line(line: str) -> Optional[str]:
    """
    Attempt to fix common JSON malformation issues.
    
    Args:
        line: Potentially malformed JSON line
        
    Returns:
        Fixed JSON string or None if unfixable
    """
    if not line or not line.strip():
        return None
    
    line = line.strip()
    
    # Try to fix common issues
    # Missing closing brace
    if line.count('{') > line.count('}'):
        line += '}' * (line.count('{') - line.count('}'))
    
    # Missing closing bracket
    if line.count('[') > line.count(']'):
        line += ']' * (line.count('[') - line.count(']'))
    
    # Try to parse
    try:
        import json
        json.loads(line)
        return line
    except:
        return None


def handle_corrupted_line(line: str, format_type: str) -> Optional[Dict]:
    """
    Attempt to recover data from corrupted lines.
    
    Args:
        line: Corrupted line
        format_type: Format type (csv, json, etc.)
        
    Returns:
        Dictionary with recovered data or None
    """
    if not line or not line.strip():
        return None
    
    line = clean_string(line)
    
    if format_type == "csv":
        # Try to split by common delimiters
        for delimiter in [',', ';', '\t', '|']:
            parts = line.split(delimiter)
            if len(parts) > 1:
                return {f"col_{i}": clean_string(part) for i, part in enumerate(parts)}
    
    elif format_type == "json":
        fixed = fix_malformed_json_line(line)
        if fixed:
            try:
                import json
                return json.loads(fixed)
            except:
                pass
    
    return None


def normalize_field_name(name: str) -> str:
    """
    Normalize field names to be consistent.
    
    Args:
        name: Original field name
        
    Returns:
        Normalized field name
    """
    # Convert to lowercase
    name = name.lower().strip()
    
    # Replace spaces and special chars with underscore
    name = re.sub(r'[^\w]', '_', name)
    
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    return name


def validate_record(record: Dict, required_fields: Optional[List[str]] = None) -> bool:
    """
    Validate that a record has required fields.
    
    Args:
        record: Record dictionary
        required_fields: List of required field names
        
    Returns:
        True if valid, False otherwise
    """
    if required_fields is None:
        return True
    
    for field in required_fields:
        if field not in record or not record[field]:
            return False
    
    return True


def sanitize_for_storage(value: Any, max_length: int = 10000) -> str:
    """
    Sanitize values for safe storage in database.
    
    Args:
        value: Value to sanitize
        max_length: Maximum string length
        
    Returns:
        Sanitized string
    """
    if value is None:
        return ""
    
    str_value = str(value)
    
    # Truncate if too long
    if len(str_value) > max_length:
        str_value = str_value[:max_length]
    
    # Clean the string
    str_value = clean_string(str_value)
    
    return str_value

