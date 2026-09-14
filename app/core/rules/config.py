"""Configuration system for the rule-based structure detector."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class RuleEngineConfig:
    """Configuration parameters for the RegexStructureDetector.
    
    Attributes:
        enabled_categories: Set of active rule categories.
        custom_patterns: User-defined regex pattern additions by element_type.
        confidence_overrides: Specific confidence scores for named rules.
        front_matter_threshold: Relative document fraction for front matter (default 0.20).
        back_matter_threshold: Relative document fraction for back matter (default 0.60).
        require_typography_signals: If True, uses bold/size/formatting to modulate confidence.
        min_confidence: Threshold below which matches are considered ambiguous.
    """
    enabled_categories: Set[str] = field(default_factory=lambda: {
        "chapter",
        "heading",
        "figure",
        "table",
        "reference",
        "list",
        "front_matter",
        "special_section",
    })
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)
    confidence_overrides: Dict[str, float] = field(default_factory=dict)
    front_matter_threshold: float = 0.20
    back_matter_threshold: float = 0.60
    require_typography_signals: bool = True
    min_confidence: float = 0.50

    def is_category_enabled(self, category: str) -> bool:
        """Checks if a rule category is active."""
        return category in self.enabled_categories

    def get_confidence(self, rule_name: str, default_confidence: float) -> float:
        """Returns the configured or default confidence score for a rule."""
        return self.confidence_overrides.get(rule_name, default_confidence)
