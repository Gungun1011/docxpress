"""Unit tests for Scikit-Learn model loading, inference, and probability calibration."""

from pathlib import Path
import numpy as np
import pytest

from app.core.ml.features import FEATURE_NAMES
from app.core.ml.models import DocumentStructureModel
from app.models.ast import ElementType


def test_model_loading_logistic_regression():
    """Verifies Logistic Regression model and preprocessors load correctly."""
    model = DocumentStructureModel(model_type="logistic_regression")
    model.load()

    assert model._is_loaded is True
    assert model.scaler is not None
    assert model.label_encoder is not None
    assert model.model is not None


def test_model_loading_decision_tree():
    """Verifies Decision Tree model and preprocessors load correctly."""
    model = DocumentStructureModel(model_type="decision_tree")
    model.load()

    assert model._is_loaded is True
    assert model.scaler is not None
    assert model.label_encoder is not None
    assert model.model is not None


def test_prediction_output_structure():
    """Verifies predict_elements returns valid PredictionResult with normalized probabilities."""
    model = DocumentStructureModel(model_type="logistic_regression")
    model.load()

    # Create dummy 1x32 feature vector representing a body paragraph
    X = np.zeros((1, len(FEATURE_NAMES)), dtype=np.float32)
    X[0, 0] = 120.0  # char length
    X[0, 1] = 25.0   # word count
    X[0, 2] = 4.8    # avg word length
    X[0, 10] = 0.45  # stopword ratio (high)
    X[0, 16] = 0.50  # relative doc position

    results = model.predict_elements(X)

    assert len(results) == 1
    res = results[0]
    assert isinstance(res.element_type, ElementType)
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.probabilities) >= 8

    # Probabilities must sum to ~1.0
    prob_sum = sum(res.probabilities.values())
    assert abs(prob_sum - 1.0) < 1e-4
