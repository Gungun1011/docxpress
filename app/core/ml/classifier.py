"""Master Hybrid Structure Detection Classifier for DocXpress.

Combines Tier 1 deterministic regex rules, Tier 2 feature engineering,
Tier 3 scikit-learn estimators (Logistic Regression / Decision Tree), and
Tier 4 contextual sequence smoothing into a single unified classification engine.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from app.core.ml.features import FeatureExtractor
from app.core.ml.models import DocumentStructureModel
from app.core.ml.rules import RegexRuleEngine, RuleMatch
from app.core.ml.smoother import ContextualSmoother
from app.models.ast import (
    BaseElement,
    CanonicalDocument,
    ElementType,
    FigureElement,
    ParagraphElement,
    TableElement,
)


@dataclass(frozen=True)
class ElementClassification:
    """Detailed classification trace for a single document element."""
    element_id: str
    original_text: str
    final_type: ElementType
    confidence: float
    detection_tier: str  # 'rule', 'ml', 'smoother'
    rule_applied: Optional[str]
    ml_probabilities: Dict[str, float]


@dataclass(frozen=True)
class ClassificationReport:
    """Telemetry report for the classification pass across a document."""
    total_elements: int
    type_counts: Dict[str, int]
    rule_classified_count: int
    ml_classified_count: int
    smoothed_count: int
    average_confidence: float
    elements: Tuple[ElementClassification, ...]


class HybridStructureClassifier:
    """Orchestrates hybrid document structure detection."""

    def __init__(
        self,
        model_type: str = "logistic_regression",
        rule_threshold: float = 0.90,
        enable_smoothing: bool = True,
        weights_dir: Optional[Path] = None,
    ) -> None:
        """Initializes the hybrid classifier.
        
        Args:
            model_type: 'logistic_regression' or 'decision_tree'.
            rule_threshold: Confidence above which deterministic rules override ML.
            enable_smoothing: Whether to apply contextual sequence smoothing.
            weights_dir: Directory containing pre-trained model weights.
        """
        self.model_type = model_type
        self.rule_threshold = rule_threshold
        self.enable_smoothing = enable_smoothing
        self.ml_model = DocumentStructureModel(
            model_type=model_type,
            weights_dir=weights_dir,
        )

    def classify_document(self, doc: CanonicalDocument) -> Tuple[CanonicalDocument, ClassificationReport]:
        """Classifies all elements in a CanonicalDocument AST.
        
        Preserves 100% of the document's original text, runs, and metadata.
        
        Args:
            doc: The CanonicalDocument AST from DocxParser.
            
        Returns:
            Tuple of (annotated_doc: CanonicalDocument, report: ClassificationReport).
        """
        elements = doc.elements
        n = len(elements)
        if n == 0:
            empty_report = ClassificationReport(
                total_elements=0,
                type_counts={},
                rule_classified_count=0,
                ml_classified_count=0,
                smoothed_count=0,
                average_confidence=1.0,
                elements=(),
            )
            return doc, empty_report

        # 1. Tier 2: Extract 32-dimensional feature matrix
        X = FeatureExtractor.extract_document_features(doc)

        # 2. Tier 3: Compute ML predictions & probability distributions
        ml_results = self.ml_model.predict_elements(X)

        # 3. Tier 1: Evaluate deterministic rules and arbitrate
        initial_types: List[ElementType] = []
        confidences: List[float] = []
        tiers: List[str] = []
        rules_applied: List[Optional[str]] = []
        prob_dicts: List[Dict[str, float]] = []

        rule_count = 0
        ml_count = 0

        for i, elem in enumerate(elements):
            rel_pos = float(i) / max(1.0, float(n - 1)) if n > 1 else 0.0
            rule_match = RegexRuleEngine.evaluate(elem, doc_position=rel_pos, total_elements=n)
            ml_pred = ml_results[i]
            prob_dicts.append(ml_pred.probabilities)

            if not elem.original_text.strip() and not isinstance(elem, (TableElement, FigureElement)) and not getattr(elem, "contains_drawing", False):
                initial_types.append(ElementType.PARAGRAPH)
                confidences.append(1.0)
                tiers.append("rule")
                rules_applied.append("rule_empty_paragraph")
                rule_count += 1
            elif rule_match and rule_match.confidence >= self.rule_threshold:
                initial_types.append(rule_match.element_type)
                confidences.append(rule_match.confidence)
                tiers.append("rule")
                rules_applied.append(rule_match.rule_name)
                rule_count += 1
            else:
                initial_types.append(ml_pred.element_type)
                confidences.append(ml_pred.confidence)
                tiers.append("ml")
                rules_applied.append(None)
                ml_count += 1

        # 4. Tier 4: Contextual Sequence Smoothing
        smoothed_count = 0
        if self.enable_smoothing:
            final_types, final_confs, smooth_reasons = ContextualSmoother.smooth_sequence(
                elements=elements,
                predicted_types=initial_types,
                confidences=confidences,
            )
            for i in range(n):
                if final_types[i] != initial_types[i]:
                    smoothed_count += 1
                    tiers[i] = "smoother"
                    rules_applied[i] = smooth_reasons[i]
        else:
            final_types = initial_types
            final_confs = confidences

        # 5. Build updated immutable AST elements
        updated_elements: List[BaseElement] = []
        classification_traces: List[ElementClassification] = []
        type_counts: Dict[str, int] = {}

        for i, elem in enumerate(elements):
            f_type = final_types[i]
            f_conf = final_confs[i]
            t_tier = tiers[i]
            r_name = rules_applied[i]

            type_counts[f_type.value] = type_counts.get(f_type.value, 0) + 1

            classification_traces.append(
                ElementClassification(
                    element_id=elem.element_id,
                    original_text=elem.original_text,
                    final_type=f_type,
                    confidence=f_conf,
                    detection_tier=t_tier,
                    rule_applied=r_name,
                    ml_probabilities=prob_dicts[i],
                )
            )

            # Reconstruct elements with updated classifications while preserving all verbatim content
            if isinstance(elem, TableElement):
                updated_elements.append(
                    TableElement(
                        element_id=elem.element_id,
                        element_type=f_type,
                        paragraph_index=elem.paragraph_index,
                        original_text=elem.original_text,
                        original_style=elem.original_style,
                        runs=elem.runs,
                        confidence=f_conf,
                        detection_method=f"{t_tier}:{r_name or self.model_type}",
                        rows_count=elem.rows_count,
                        cols_count=elem.cols_count,
                        cells=elem.cells,
                    )
                )
            elif isinstance(elem, FigureElement):
                updated_elements.append(
                    FigureElement(
                        element_id=elem.element_id,
                        element_type=f_type,
                        paragraph_index=elem.paragraph_index,
                        original_text=elem.original_text,
                        original_style=elem.original_style,
                        runs=elem.runs,
                        confidence=f_conf,
                        detection_method=f"{t_tier}:{r_name or self.model_type}",
                        image_id=elem.image_id,
                        image_filename=elem.image_filename,
                        content_type=elem.content_type,
                        width_pt=elem.width_pt,
                        height_pt=elem.height_pt,
                        caption_text=elem.caption_text,
                    )
                )
            elif isinstance(elem, ParagraphElement):
                updated_elements.append(
                    ParagraphElement(
                        element_id=elem.element_id,
                        element_type=f_type,
                        paragraph_index=elem.paragraph_index,
                        original_text=elem.original_text,
                        original_style=elem.original_style,
                        runs=elem.runs,
                        confidence=f_conf,
                        detection_method=f"{t_tier}:{r_name or self.model_type}",
                        list_info=elem.list_info,
                        contains_drawing=elem.contains_drawing,
                        alignment=elem.alignment,
                    )
                )
            else:
                # Generic fallback
                updated_elements.append(
                    ParagraphElement(
                        element_id=elem.element_id,
                        element_type=f_type,
                        paragraph_index=elem.paragraph_index,
                        original_text=elem.original_text,
                        original_style=elem.original_style,
                        runs=elem.runs,
                        confidence=f_conf,
                        detection_method=f"{t_tier}:{r_name or self.model_type}",
                    )
                )

        annotated_doc = doc.with_elements(updated_elements)
        avg_conf = float(np.mean(final_confs)) if final_confs else 1.0

        report = ClassificationReport(
            total_elements=n,
            type_counts=type_counts,
            rule_classified_count=rule_count,
            ml_classified_count=ml_count,
            smoothed_count=smoothed_count,
            average_confidence=avg_conf,
            elements=tuple(classification_traces),
        )

        return annotated_doc, report
