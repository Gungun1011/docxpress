"""NLP-based document structure classification engine.

Infers document structure from linguistic, syntactic, and typographical features
when explicit regex prefixes or Word styles are absent.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.core.nlp.extractor import NLPFeatureExtractor
from app.core.nlp.schemas import NLPElementFeatures
from app.models.ast import BaseElement, CanonicalDocument, ElementType


@dataclass(frozen=True)
class NLPClassification:
    """Structure classification result based on NLP feature analysis.
    
    Attributes:
        element_type: Inferred structural element type.
        confidence: Confidence score between 0.0 and 1.0.
        linguistic_cues: List of linguistic/topographical signals that justified the inference.
        features: The extracted NLPElementFeatures object.
    """
    element_type: str
    confidence: float
    linguistic_cues: Tuple[str, ...]
    features: NLPElementFeatures

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary containing classification and features."""
        return {
            "element_type": self.element_type,
            "confidence": round(self.confidence, 4),
            "linguistic_cues": list(self.linguistic_cues),
            "features": self.features.to_dict(),
        }


class NLPStructureClassifier:
    """Classifies document elements solely via NLP and linguistic heuristics."""

    def __init__(self, extractor: Optional[NLPFeatureExtractor] = None) -> None:
        self.extractor = extractor or NLPFeatureExtractor()

    def classify_element(self, feat: NLPElementFeatures) -> NLPClassification:
        """Classifies an element based on its extracted NLP features."""
        cues: List[str] = []

        # 1. Empty paragraph
        if feat.text_length == 0:
            return NLPClassification(
                element_type="body_paragraph",
                confidence=1.0,
                linguistic_cues=("empty_text_block",),
                features=feat,
            )

        # 2. Front matter Title (prominent, title case, unpunctuated, early)
        if feat.paragraph_position < 0.08 and feat.word_count <= 15:
            if not feat.ends_with_period and (feat.is_title_case or feat.is_all_caps):
                conf = 0.90
                cues.append("front_matter_position")
                cues.append("title_capitalization")
                if feat.is_bold or feat.is_larger_than_surroundings:
                    conf += 0.06
                    cues.append("typographic_prominence")
                if feat.stopword_ratio < 0.30:
                    cues.append("low_stopword_density")
                return NLPClassification(
                    element_type="title",
                    confidence=min(0.98, conf),
                    linguistic_cues=tuple(cues),
                    features=feat,
                )

        # 3. Front matter Author / Affiliation
        if feat.paragraph_position < 0.15 and feat.contains_author_keyword:
            cues.append("contains_affiliation_lexicon")
            cues.append("front_matter_position")
            return NLPClassification(
                element_type="author",
                confidence=0.95,
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 4. Abstract section
        if feat.paragraph_position < 0.20 and feat.contains_abstract_keyword and feat.word_count <= 8:
            cues.append("abstract_keyword_in_front_matter")
            cues.append("concise_heading_length")
            return NLPClassification(
                element_type="abstract",
                confidence=0.97,
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 5. References / Bibliography header
        if feat.contains_reference_keyword and feat.paragraph_position > 0.40 and feat.word_count <= 5:
            cues.append("reference_keyword_in_back_matter")
            cues.append("concise_heading_length")
            return NLPClassification(
                element_type="references",
                confidence=0.98,
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 6. Academic Reference Citation Entry (in back matter, year pattern, citation markers)
        if feat.paragraph_position > 0.50 and feat.word_count >= 6:
            if (feat.starts_with_number or feat.has_numbering_marker) and feat.lexical_diversity > 0.70:
                cues.append("high_lexical_diversity_citation")
                cues.append("back_matter_numbered_item")
                return NLPClassification(
                    element_type="reference_entry",
                    confidence=0.94,
                    linguistic_cues=tuple(cues),
                    features=feat,
                )

        # 7. Chapter Headings (explicit keyword or large unpunctuated section divider)
        if feat.contains_chapter_keyword and feat.word_count <= 20:
            cues.append("contains_chapter_keyword")
            conf = 0.95
            if feat.is_bold or feat.is_all_caps:
                conf += 0.03
                cues.append("prominent_styling")
            return NLPClassification(
                element_type="chapter_heading",
                confidence=min(0.99, conf),
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 8. Unstyled Section Headings (unpunctuated, title-case, short, isolated, low stopwords)
        if (
            feat.word_count <= 12
            and not feat.ends_with_period
            and not feat.ends_with_question
            and (feat.is_title_case or feat.is_all_caps or feat.is_bold or feat.is_larger_than_surroundings)
            and feat.is_isolated
        ):
            cues.append("short_isolated_block")
            cues.append("unpunctuated_terminal")
            conf = 0.88
            if feat.is_bold or feat.is_larger_than_surroundings:
                conf += 0.05
                cues.append("bold_or_large_font")
            if feat.stopword_ratio < 0.25:
                cues.append("low_stopword_ratio")

            target_type = "heading"
            if feat.starts_with_number:
                cues.append("numbered_section_prefix")

            return NLPClassification(
                element_type=target_type,
                confidence=min(0.96, conf),
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 9. List Items (bullet markers or sequential items)
        if feat.has_numbering_marker and feat.word_count < 60:
            cues.append("numbering_or_bullet_marker")
            return NLPClassification(
                element_type="list_item",
                confidence=0.96,
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 10. Conclusion section
        if feat.contains_conclusion_keyword and feat.word_count <= 6:
            cues.append("conclusion_keyword")
            cues.append("concise_heading")
            return NLPClassification(
                element_type="conclusion",
                confidence=0.95,
                linguistic_cues=tuple(cues),
                features=feat,
            )

        # 11. Standard Running Body Paragraph
        cues.append("standard_narrative_characteristics")
        if feat.ends_with_period:
            cues.append("terminal_period_punctuation")
        if feat.stopword_ratio >= 0.35:
            cues.append("high_natural_stopword_frequency")
        if feat.sentence_count >= 1:
            cues.append(f"multi_sentence_flow({feat.sentence_count}_sentences)")

        return NLPClassification(
            element_type="body_paragraph",
            confidence=0.90,
            linguistic_cues=tuple(cues),
            features=feat,
        )

    def classify_document(self, doc: CanonicalDocument) -> List[NLPClassification]:
        """Classifies every element in a document using pure NLP feature analysis."""
        features_list = self.extractor.extract_document_features(doc)
        return [self.classify_element(feat) for feat in features_list]
