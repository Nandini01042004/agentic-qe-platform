"""Data Pipeline Normalization and Schema Validation Service."""

from typing import List, Dict, Any, Optional
import math


class RecordValidationError(Exception):
    """Raised when an ingested record violates schema constraints."""
    pass


class DataPipeline:
    """
    ETL Data Pipeline component for normalizing tabular records,
    detecting numerical outliers, and ensuring mandatory field schemas.
    """

    MANDATORY_FIELDS = {"record_id", "timestamp", "value"}

    def __init__(self, outlier_std_threshold: float = 3.0):
        self.threshold = outlier_std_threshold
        self._processed_batches: List[List[Dict[str, Any]]] = []

    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validates that a single data dictionary conforms to mandatory schema."""
        if not isinstance(record, dict):
            raise RecordValidationError("Record must be a dictionary.")

        missing = self.MANDATORY_FIELDS - set(record.keys())
        if missing:
            raise RecordValidationError(f"Record missing required keys: {missing}")

        val = record.get("value")
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            raise RecordValidationError(f"Invalid numeric value: {val}")

        return True

    def normalize_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validates all records in batch, filters out outliers,
        and scales values between 0.0 and 1.0.
        """
        if not batch:
            return []

        for record in batch:
            self.validate_record(record)

        values = [float(r["value"]) for r in batch]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        # Filter outliers
        filtered = []
        for r in batch:
            val = float(r["value"])
            if std_dev > 0 and abs(val - mean) > (self.threshold * std_dev):
                continue
            filtered.append(r)

        if not filtered:
            return []

        # Min-Max Scaling
        clean_vals = [float(r["value"]) for r in filtered]
        min_v = min(clean_vals)
        max_v = max(clean_vals)
        diff = max_v - min_v

        normalized = []
        for r in filtered:
            val = float(r["value"])
            norm_val = round((val - min_v) / diff, 4) if diff > 0 else 0.5
            normalized.append({
                "record_id": r["record_id"],
                "timestamp": r["timestamp"],
                "raw_value": val,
                "normalized_value": norm_val,
            })

        self._processed_batches.append(normalized)
        return normalized
