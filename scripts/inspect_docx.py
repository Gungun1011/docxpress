"""CLI tool to inspect any DOCX file, parse into Canonical AST, and print summary."""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Force UTF-8 encoding on standard output for Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.parser.docx_parser import DocxParser
from app.services.document_summary import DocumentSummaryService
from app.utils.file_utils import get_file_fingerprint, verify_file_unmodified


def inspect_file(file_path: Path) -> None:
    """Parses DOCX file and prints summary while verifying read-only invariant."""
    print(f"\nTarget File: {file_path.resolve()}")
    if not file_path.exists():
        print(f"Error: File does not exist: {file_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Record fingerprint before
    before_fp = get_file_fingerprint(file_path)
    print(f"Original File SHA-256: {before_fp.sha256}")
    print(f"Original File MTime:   {before_fp.mtime}")

    # 2. Parse into AST
    parser = DocxParser(enforce_read_only=True)
    doc = parser.parse(file_path)

    # 3. Print Native AST Summary
    summary_text = DocumentSummaryService.format_summary(doc)
    print("\n" + summary_text)

    # 4. Run Phase 2 Hybrid Structure Detection
    from app.core.ml.classifier import HybridStructureClassifier
    classifier = HybridStructureClassifier(model_type="logistic_regression")
    classified_doc, report = classifier.classify_document(doc)

    print("\n" + "=" * 70)
    print("PHASE 2: HYBRID ML CLASSIFICATION REPORT")
    print("=" * 70)
    print(f"Total Elements Classified:  {report.total_elements}")
    print(f"Average Confidence Score:   {report.average_confidence * 100:.1f}%")
    print(f"Classified via Rules:       {report.rule_classified_count}")
    print(f"Classified via ML Model:    {report.ml_classified_count}")
    print(f"Adjusted via Smoother:      {report.smoothed_count}")
    print("-" * 70)
    print("DETECTED 11-CLASS BREAKDOWN:")
    for class_name, count in sorted(report.type_counts.items()):
        print(f"  - {class_name.upper():<16}: {count}")
    print("=" * 70)

    # 5. Run Phase 3 Rule-Based Structure Detector
    import json
    from app.core.rules.detector import RegexStructureDetector
    detector = RegexStructureDetector()
    rule_results = detector.detect_document(doc)

    print("\n" + "=" * 70)
    print("PHASE 3: RULE-BASED REGEX STRUCTURE DETECTION (SAMPLE JSON RESULTS)")
    print("=" * 70)
    # Display sample detection dictionaries as specified in requirements
    preview_indices = [0, 1, 2, 3, 6, 8, 9, 10, 13, 16, 17]
    for idx in preview_indices:
        if idx < len(rule_results):
            res_dict = rule_results[idx].to_dict()
            elem_text = doc.elements[idx].original_text.replace("\n", " ")[:45]
            print(f"Element [{idx:02d}] Text: \"{elem_text}\"")
            print(json.dumps(res_dict, indent=2))
            print("-" * 50)
    print("=" * 70)

    # 5. Record fingerprint after
    after_fp = get_file_fingerprint(file_path)
    unmodified, reason = verify_file_unmodified(before_fp, after_fp)
    print(f"\nRead-Only Invariant Check: {'PASSED [OK]' if unmodified else 'FAILED [ERROR]'}")
    print(f"Details: {reason}")
    if not unmodified:
        sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to sample document
        sample_path = project_root / "sample_documents" / "deterministic_sample.docx"
        if not sample_path.exists():
            from scripts.generate_test_docs import generate_all_test_documents
            generate_all_test_documents(sample_path.parent)
        inspect_file(sample_path)
    else:
        inspect_file(Path(sys.argv[1]))
