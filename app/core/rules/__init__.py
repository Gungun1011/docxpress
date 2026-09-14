"""Rule-based document structure detection package."""

from app.core.rules.config import RuleEngineConfig
from app.core.rules.detector import RegexStructureDetector
from app.core.rules.patterns import (
    RE_ABSTRACT,
    RE_ACKNOWLEDGEMENTS,
    RE_AUTHOR_AFFILIATION,
    RE_CHAPTER_DIGIT,
    RE_CHAPTER_ROMAN,
    RE_CHAPTER_WORD,
    RE_CONCLUSION,
    RE_FIGURE_CAPTION,
    RE_HEADING_L1,
    RE_HEADING_L2,
    RE_HEADING_L3,
    RE_LIST_BULLET,
    RE_LIST_LETTERED,
    RE_LIST_NUMBERED,
    RE_REFERENCES_HEADER,
    RE_TABLE_CAPTION,
)
from app.core.rules.schemas import DetectionResult

__all__ = [
    "RuleEngineConfig",
    "RegexStructureDetector",
    "DetectionResult",
    "RE_ABSTRACT",
    "RE_ACKNOWLEDGEMENTS",
    "RE_AUTHOR_AFFILIATION",
    "RE_CHAPTER_DIGIT",
    "RE_CHAPTER_ROMAN",
    "RE_CHAPTER_WORD",
    "RE_CONCLUSION",
    "RE_FIGURE_CAPTION",
    "RE_HEADING_L1",
    "RE_HEADING_L2",
    "RE_HEADING_L3",
    "RE_LIST_BULLET",
    "RE_LIST_LETTERED",
    "RE_LIST_NUMBERED",
    "RE_REFERENCES_HEADER",
    "RE_TABLE_CAPTION",
]
