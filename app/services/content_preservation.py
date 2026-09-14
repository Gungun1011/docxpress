"""Content preservation and textual fingerprinting service.

Extracts, normalizes, and fingerprints the textual content of a CanonicalDocument.
Proves textual-content preservation without claiming byte-for-byte DOCX zip container identity.
"""

from dataclasses import dataclass
import hashlib
import re
from typing import List, Sequence, Tuple
import unicodedata

from app.models.ast import CanonicalDocument


@dataclass(frozen=True)
class PreservationFingerprint:
    """Represents the cryptographic and structural fingerprint of document text.
    
    Attributes:
        ordered_text_sequence: Raw text strings extracted in exact document order.
        normalized_text: Canonical normalized textual representation.
        sha256_hash: SHA-256 hexadecimal hash of normalized_text (UTF-8).
        element_count: Number of contributing document elements.
        word_count: Total word count in normalized text.
        char_count: Total character count in normalized text.
    """
    ordered_text_sequence: Tuple[str, ...]
    normalized_text: str
    sha256_hash: str
    element_count: int
    word_count: int
    char_count: int
    token_sequence: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ContentPreservationReport:
    """Detailed comparison of ordered normalized document content."""

    is_identical: bool
    source_hash: str
    output_hash: str
    changed_elements: Tuple[int, ...] = ()
    missing_elements: Tuple[int, ...] = ()
    added_elements: Tuple[int, ...] = ()


class ContentPreservationError(RuntimeError):
    """Raised when a formatting operation changes textual content."""

    def __init__(self, report: ContentPreservationReport) -> None:
        super().__init__(
            f"Formatting changed document content: source={report.source_hash}, "
            f"output={report.output_hash}"
        )
        self.report = report


class ContentPreservationService:
    """Service to compute deterministic textual fingerprints for content preservation.
    
    Normalization Method:
        1. Unicode Normalization: Standardizes all text using Unicode NFKC
           (Compatibility Decomposition followed by Canonical Composition) to handle
           ligatures, accents, and cross-platform encoding discrepancies.
        2. Line Break Standardization: Converts CRLF (\\r\\n) and CR (\\r) to LF (\\n).
        3. Whitespace Collapsing: Collapses multiple consecutive horizontal whitespace
           characters (spaces, tabs) into a single space (' ').
        4. Line Trimming: Trims leading and trailing whitespace from every line.
        5. Empty Segment Filtering: Ignores purely whitespace-only blocks.
        6. Deterministic Delimiting: Joins non-empty normalized element segments with
           double newline ('\\n\\n').
        7. SHA-256 Digest: Computes the SHA-256 cryptographic digest of the UTF-8 bytes.
        
    Note:
        This fingerprint proves textual-content identity according to this documented
        normalization method. It does not claim byte-for-byte DOCX container identity,
        since DOCX is a compressed ZIP archive containing non-deterministic timestamps,
        volatile XML namespaces, and settings files.
    """

    @classmethod
    def normalize_string(cls, text: str) -> str:
        """Applies deterministic normalization to a raw string."""
        if not text:
            return ""

        # Step 1: Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)

        # Step 2: Line break standardization
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Step 3 & 4: Whitespace collapsing & line trimming
        lines = []
        for raw_line in normalized.split("\n"):
            # Collapse internal whitespace
            collapsed = re.sub(r"[ \t\v\f]+", " ", raw_line).strip()
            if collapsed:
                lines.append(collapsed)

        return "\n".join(lines)

    @classmethod
    def generate_fingerprint(cls, doc: CanonicalDocument) -> PreservationFingerprint:
        """Generates a cryptographic fingerprint from a CanonicalDocument AST.
        
        Args:
            doc: The CanonicalDocument AST.
            
        Returns:
            PreservationFingerprint with normalized text and SHA-256 hash.
        """
        raw_sequence: List[str] = []
        normalized_segments: List[str] = []

        for elem in doc.elements:
            raw_text = elem.original_text
            raw_sequence.append(raw_text)

            norm = cls.normalize_string(raw_text)
            if norm:
                normalized_segments.append(norm)

        normalized_document_text = "\n\n".join(normalized_segments)
        encoded_bytes = normalized_document_text.encode("utf-8")
        sha256_digest = hashlib.sha256(encoded_bytes).hexdigest()

        word_count = len(normalized_document_text.split()) if normalized_document_text else 0
        char_count = len(normalized_document_text)

        return PreservationFingerprint(
            ordered_text_sequence=tuple(raw_sequence),
            token_sequence=tuple(cls.normalize_string(value) for value in raw_sequence),
            normalized_text=normalized_document_text,
            sha256_hash=sha256_digest,
            element_count=len(doc.elements),
            word_count=word_count,
            char_count=char_count,
        )

    @classmethod
    def compare_fingerprints(
        cls,
        source: PreservationFingerprint,
        output: PreservationFingerprint,
    ) -> ContentPreservationReport:
        """Compares hashes and ordered normalized element tokens."""
        source_tokens = source.token_sequence
        output_tokens = output.token_sequence
        changed = tuple(
            index for index, (left, right) in enumerate(zip(source_tokens, output_tokens))
            if left != right
        )
        common_length = min(len(source_tokens), len(output_tokens))
        missing = tuple(range(common_length, len(source_tokens)))
        added = tuple(range(common_length, len(output_tokens)))
        return ContentPreservationReport(
            is_identical=(source.sha256_hash == output.sha256_hash and not changed and not missing and not added),
            source_hash=source.sha256_hash,
            output_hash=output.sha256_hash,
            changed_elements=changed,
            missing_elements=missing,
            added_elements=added,
        )

    @classmethod
    def verify_report(cls, doc_a: CanonicalDocument, doc_b: CanonicalDocument) -> ContentPreservationReport:
        """Returns the structured preservation result for two ASTs."""
        return cls.compare_fingerprints(cls.generate_fingerprint(doc_a), cls.generate_fingerprint(doc_b))

    @classmethod
    def verify_content_identity(
        cls,
        doc_a: CanonicalDocument,
        doc_b: CanonicalDocument,
    ) -> Tuple[bool, str]:
        """Compares two CanonicalDocuments to verify exact textual content preservation.
        
        Args:
            doc_a: First CanonicalDocument (typically original).
            doc_b: Second CanonicalDocument (typically processed).
            
        Returns:
            Tuple of (is_identical: bool, diagnostic_message: str).
        """
        fp_a = cls.generate_fingerprint(doc_a)
        fp_b = cls.generate_fingerprint(doc_b)

        if fp_a.sha256_hash != fp_b.sha256_hash:
            return False, (
                f"Content mismatch! Hash A ({fp_a.sha256_hash[:12]}...) != "
                f"Hash B ({fp_b.sha256_hash[:12]}...). "
                f"Chars: {fp_a.char_count} vs {fp_b.char_count}, Words: {fp_a.word_count} vs {fp_b.word_count}."
            )

        return True, "100% textual content preservation verified."
