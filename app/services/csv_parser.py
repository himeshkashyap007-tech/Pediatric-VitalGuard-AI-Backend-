"""CSV parsing and validation."""
import csv
import io
from typing import List, Dict, Any, Optional
import logging

from app.core.constants import CSV_REQUIRED_COLUMNS, CSV_OPTIONAL_COLUMNS

logger = logging.getLogger(__name__)

class CSVParser:
    """Parse and validate CSV files."""
    
    def __init__(self, max_rows: int = 100000, max_size_mb: int = 10):
        self.max_rows = max_rows
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def parse(self, content: bytes) -> Dict[str, Any]:
        """Parse CSV content and validate."""
        
        # Check size
        if len(content) > self.max_size_bytes:
            raise ValueError(f"File size exceeds {self.max_size_bytes / (1024*1024):.1f} MB limit")
        
        # Decode
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except:
                raise ValueError("Cannot decode file - must be UTF-8 or Latin-1")
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(text))
        
        # Validate headers
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no headers")
        
        missing_required = set(CSV_REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing_required:
            raise ValueError(f"Missing required columns: {', '.join(missing_required)}")
        
        available_optional = set(reader.fieldnames) & set(CSV_OPTIONAL_COLUMNS)
        
        # Parse rows
        data = []
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            if len(data) >= self.max_rows:
                logger.warning(f"Reached maximum row limit of {self.max_rows}")
                break
            
            parsed_row, row_errors = self._parse_row(row, row_num, available_optional)
            
            if row_errors:
                errors.extend(row_errors)
                if len(errors) > 100:  # Limit error reporting
                    errors.append("Too many errors - stopping validation")
                    break
            else:
                data.append(parsed_row)
        
        if not data:
            raise ValueError("No valid data rows found")
        
        logger.info(f"Parsed {len(data)} rows from CSV")
        
        result = {
            "data": data,
            "row_count": len(data),
            "columns": list(reader.fieldnames),
            "required_columns": CSV_REQUIRED_COLUMNS,
            "optional_columns_present": list(available_optional),
            "optional_columns_missing": list(set(CSV_OPTIONAL_COLUMNS) - available_optional),
            "errors": errors
        }
        
        return result
    
    def _parse_row(
        self,
        row: Dict[str, str],
        row_num: int,
        available_optional: set
    ) -> tuple[Optional[Dict[str, Any]], List[str]]:
        """Parse and validate a single row."""
        
        errors = []
        parsed = {}
        
        # Required fields
        try:
            pulse = float(row["pulse_bpm"])
            if not (30 <= pulse <= 250):
                errors.append(f"Row {row_num}: pulse_bpm {pulse} outside valid range (30-250)")
            parsed["pulse_bpm"] = pulse
        except (ValueError, KeyError) as e:
            errors.append(f"Row {row_num}: Invalid pulse_bpm - {str(e)}")
            return None, errors
        
        try:
            spo2 = float(row["spo2_percent"])
            if not (0 <= spo2 <= 100):
                errors.append(f"Row {row_num}: spo2_percent {spo2} outside valid range (0-100)")
            parsed["spo2_percent"] = spo2
        except (ValueError, KeyError) as e:
            errors.append(f"Row {row_num}: Invalid spo2_percent - {str(e)}")
            return None, errors
        
        # Optional fields
        if "timestamp" in available_optional:
            try:
                parsed["timestamp"] = float(row["timestamp"])
            except:
                pass
        
        if "motion" in available_optional:
            try:
                motion = float(row["motion"])
                parsed["motion"] = max(0, min(1, motion))
            except:
                pass
        
        if "contact" in available_optional:
            try:
                contact = float(row["contact"])
                parsed["contact"] = max(0, min(1, contact))
            except:
                pass
        
        if "ppg_amplitude" in available_optional:
            try:
                parsed["ppg_amplitude"] = float(row["ppg_amplitude"])
            except:
                pass
        
        if "ppg_value" in available_optional:
            try:
                parsed["ppg_value"] = float(row["ppg_value"])
            except:
                pass
        
        return parsed, []
