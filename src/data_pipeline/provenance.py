"""
Provenance metadata model.
Every number in the system must carry a ProvenanceRecord.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ProvenanceRecord:
    """Immutable record of a single data point's origin."""

    value: Optional[float]
    source_id: str                # config key, e.g. "banxico_sf61745"
    source_name: str              # human label
    source_url: str
    fetch_method: str             # "api" | "csv" | "xls" | "manual" | "reference"
    asof_date: str                # ISO date the data point represents
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    currency: Optional[str] = None
    unit: str = ""                # "percent" | "billion_usd" | "million_mxn" | "count"
    is_estimated: bool = False
    confidence: str = "high"      # "high" | "medium" | "low"
    notes: str = ""

    # ── Serialisation ───────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return asdict(self)

    def to_json_str(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)

    # ── Factory helpers ─────────────────────────────────────────────────
    @classmethod
    def from_reference(
        cls,
        value: float,
        source_id: str,
        source_name: str,
        reference_year: int,
        unit: str = "",
        currency: Optional[str] = None,
        notes: str = "",
    ) -> "ProvenanceRecord":
        return cls(
            value=value,
            source_id=source_id,
            source_name=source_name,
            source_url="",
            fetch_method="reference",
            asof_date=f"{reference_year}-12-31",
            currency=currency,
            unit=unit,
            is_estimated=True,
            confidence="medium",
            notes=f"Reference value from audit. {notes}".strip(),
        )

    @classmethod
    def missing(cls, source_id: str, source_name: str) -> "ProvenanceRecord":
        return cls(
            value=None,
            source_id=source_id,
            source_name=source_name,
            source_url="",
            fetch_method="manual",
            asof_date="",
            is_estimated=False,
            confidence="low",
            notes="Source not accessible — requires manual update",
        )


@dataclass
class CountryDataPoint:
    """One field for one country, with its provenance attached."""
    country: str
    field: str
    provenance: ProvenanceRecord

    @property
    def value(self) -> Optional[float]:
        return self.provenance.value

    def to_supabase_meta(self) -> dict:
        """Returns the source_meta JSON blob for the Supabase column."""
        return {
            "source_id":    self.provenance.source_id,
            "source_name":  self.provenance.source_name,
            "fetch_method": self.provenance.fetch_method,
            "asof_date":    self.provenance.asof_date,
            "fetched_at":   self.provenance.fetched_at,
            "confidence":   self.provenance.confidence,
            "is_estimated": self.provenance.is_estimated,
            "notes":        self.provenance.notes,
        }
