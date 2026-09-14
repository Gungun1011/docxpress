"""ML and hybrid structure detection package for DocXpress."""

from app.core.ml.classifier import (
    ClassificationReport,
    ElementClassification,
    HybridStructureClassifier,
)
from app.core.ml.features import FEATURE_NAMES, FeatureExtractor
from app.core.ml.models import (
    DocumentStructureModel,
    PredictionResult,
    train_and_save_models,
)
from app.core.ml.rules import RegexRuleEngine, RuleMatch
from app.core.ml.smoother import ContextualSmoother

__all__ = [
    "ClassificationReport",
    "ElementClassification",
    "HybridStructureClassifier",
    "FEATURE_NAMES",
    "FeatureExtractor",
    "DocumentStructureModel",
    "PredictionResult",
    "train_and_save_models",
    "RegexRuleEngine",
    "RuleMatch",
    "ContextualSmoother",
]
