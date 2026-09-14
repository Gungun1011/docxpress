"""Schemas and data models for rule-based structure detection."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DetectionResult:
    """Structured detection result for a document element.
    
    Attributes:
        element_type: Canonical element label (e.g. 'chapter_heading', 'heading', 'title').
        confidence: Normalized confidence score between 0.0 and 1.0.
        reason: Human-readable explanation of why the rule fired.
        pattern_matched: Exact text snippet or regex pattern that matched.
        metadata: Optional dictionary with additional structural metadata.
    """
    element_type: str
    confidence: float
    reason: str
    pattern_matched: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result to the required JSON-compatible dictionary format."""
        return {
            "element_type": self.element_type,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "pattern_matched": self.pattern_matched,
        }
