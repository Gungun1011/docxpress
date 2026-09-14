"""Scikit-learn model wrapper and training engine for document element classification.

Implements Logistic Regression and Decision Tree estimators with offline
feature scaling, model serialization via joblib, and probability calibration.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.core.ml.dataset import ManuscriptDatasetGenerator
from app.models.ast import ElementType


WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"


@dataclass
class PredictionResult:
    """Class prediction with confidence score and class distribution."""
    element_type: ElementType
    confidence: float
    probabilities: Dict[str, float]


class DocumentStructureModel:
    """Manages inference using pre-trained Logistic Regression or Decision Tree models."""

    def __init__(
        self,
        model_type: str = "logistic_regression",
        weights_dir: Optional[Path] = None,
    ) -> None:
        """Initializes model loader.
        
        Args:
            model_type: 'logistic_regression' or 'decision_tree'.
            weights_dir: Custom directory containing joblib files (default: app/core/ml/weights).
        """
        self.model_type = model_type
        self.weights_dir = weights_dir or WEIGHTS_DIR
        self.scaler: Optional[StandardScaler] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.model: Any = None
        self._is_loaded = False

    def load(self) -> None:
        """Loads serialized weights from disk. Trains them if they do not exist."""
        if not (self.weights_dir / "scaler.joblib").exists():
            # Automatically train and persist if missing
            train_and_save_models(self.weights_dir)

        self.scaler = joblib.load(self.weights_dir / "scaler.joblib")
        self.label_encoder = joblib.load(self.weights_dir / "label_encoder.joblib")

        model_filename = (
            "model_dt.joblib" if self.model_type == "decision_tree" else "model_logreg.joblib"
        )
        self.model = joblib.load(self.weights_dir / model_filename)
        self._is_loaded = True

    def predict_elements(self, X: np.ndarray) -> List[PredictionResult]:
        """Predicts ElementTypes and class probabilities for a feature matrix X.
        
        Args:
            X: Feature matrix of shape (N_elements, 32).
            
        Returns:
            List of PredictionResult instances.
        """
        if not self._is_loaded:
            self.load()

        if len(X) == 0:
            return []

        # Standardize features
        assert self.scaler is not None
        assert self.label_encoder is not None
        X_scaled = self.scaler.transform(X)

        probabilities = self.model.predict_proba(X_scaled)
        class_indices = np.argmax(probabilities, axis=1)

        results: List[PredictionResult] = []
        class_names = list(self.label_encoder.classes_)

        for idx, probs in zip(class_indices, probabilities):
            pred_label = class_names[idx]
            conf = float(probs[idx])
            prob_dict = {name: float(p) for name, p in zip(class_names, probs)}

            # Map to canonical ElementType
            try:
                elem_type = ElementType(pred_label)
            except ValueError:
                elem_type = ElementType.UNKNOWN

            results.append(
                PredictionResult(
                    element_type=elem_type,
                    confidence=conf,
                    probabilities=prob_dict,
                )
            )

        return results


def train_and_save_models(
    weights_dir: Optional[Path] = None,
    num_documents: int = 120,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Trains both Logistic Regression and Decision Tree models and saves weights.
    
    Args:
        weights_dir: Directory where weights will be saved.
        num_documents: Number of synthetic documents to generate for training.
        random_seed: Random seed for reproducibility.
        
    Returns:
        Evaluation metrics dictionary.
    """
    target_dir = weights_dir or WEIGHTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate synthetic training corpus
    X_raw, y_raw = ManuscriptDatasetGenerator.generate_synthetic_corpus(
        num_documents=num_documents,
        random_seed=random_seed,
    )

    # 2. Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y_raw)

    # 3. Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_raw, y_encoded, test_size=0.20, random_state=random_seed, stratify=y_encoded
    )

    # 4. Feature scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 5. Train Logistic Regression
    clf_logreg = LogisticRegression(
        solver="lbfgs",
        max_iter=1500,
        class_weight="balanced",
        random_state=random_seed,
    )
    clf_logreg.fit(X_train_scaled, y_train)

    # 6. Train Decision Tree
    clf_dt = DecisionTreeClassifier(
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_seed,
    )
    clf_dt.fit(X_train_scaled, y_train)

    # 7. Evaluate
    logreg_acc = float(clf_logreg.score(X_test_scaled, y_test))
    dt_acc = float(clf_dt.score(X_test_scaled, y_test))

    # 8. Save artifacts using joblib
    joblib.dump(scaler, target_dir / "scaler.joblib")
    joblib.dump(label_encoder, target_dir / "label_encoder.joblib")
    joblib.dump(clf_logreg, target_dir / "model_logreg.joblib")
    joblib.dump(clf_dt, target_dir / "model_dt.joblib")

    return {
        "sample_count": len(X_raw),
        "logistic_regression_accuracy": logreg_acc,
        "decision_tree_accuracy": dt_acc,
        "classes": list(label_encoder.classes_),
    }
