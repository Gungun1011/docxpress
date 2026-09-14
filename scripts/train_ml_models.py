"""Offline training script for DocXpress Scikit-Learn models."""

from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.ml.models import train_and_save_models


def main() -> None:
    weights_dir = project_root / "app" / "core" / "ml" / "weights"
    print(f"Training ML models and saving artifacts to: {weights_dir}")
    metrics = train_and_save_models(weights_dir=weights_dir, num_documents=150, random_seed=42)
    print("\n" + "=" * 60)
    print("TRAINING & VALIDATION METRICS")
    print("=" * 60)
    print(f"Total Synthetic Elements:          {metrics['sample_count']:,}")
    print(f"Logistic Regression Test Accuracy: {metrics['logistic_regression_accuracy'] * 100:.2f}%")
    print(f"Decision Tree Test Accuracy:       {metrics['decision_tree_accuracy'] * 100:.2f}%")
    print(f"Trained Classes ({len(metrics['classes'])}):")
    for c in metrics["classes"]:
        print(f"  - {c}")
    print("=" * 60)
    print("Model weights successfully serialized.")


if __name__ == "__main__":
    main()
