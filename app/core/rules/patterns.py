"""Regex pattern definitions for document structure detection.

Defines compiled regular expressions for chapters, headings, figures,
tables, lists, references, titles, authors, and special sections.
"""

import re
from typing import Dict, Pattern

# English word representations for numbers (1 to 100)
NUMBER_WORDS = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth"
)

# Standard Roman numerals (I to L)
ROMAN_NUMERALS = r"(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{1,3})"

# CHAPTER PATTERNS
# 1. "Chapter 1", "Chapter 1:", "Chapter 1 - The Beginning"
RE_CHAPTER_DIGIT = re.compile(
    r"^(?:chapter|ch\.|part|book|section)\s+(\d+)[:\s\-—]*(.*)$",
    re.IGNORECASE,
)
# 2. "CHAPTER ONE", "Chapter Two:", "CHAPTER FIRST"
RE_CHAPTER_WORD = re.compile(
    rf"^(?:chapter|ch\.|part|book|section)\s+({NUMBER_WORDS})[:\s\-—]*(.*)$",
    re.IGNORECASE,
)
# 3. "CHAPTER I", "Chapter IV:", "CHAPTER IX"
RE_CHAPTER_ROMAN = re.compile(
    rf"^(?:chapter|ch\.|part|book|section)\s+({ROMAN_NUMERALS})[:\s\-—]*(.*)$",
    re.IGNORECASE,
)
# Standalone chapter word (e.g. "Chapter 1" with nothing else)
RE_CHAPTER_STANDALONE = re.compile(
    rf"^(?:chapter|ch\.|part|book)\s+(?:\d+|{NUMBER_WORDS}|{ROMAN_NUMERALS})\s*$",
    re.IGNORECASE,
)

# HEADING PATTERNS
# Level 1: "1 Introduction", "1. Introduction", "1: Introduction"
RE_HEADING_L1 = re.compile(
    r"^(\d+)[\.\:]?\s+([A-Z][\w\s,–—\-\?]+)$"
)
# Level 2: "1.1 Background", "1.1. Background", "1.1: Background"
RE_HEADING_L2 = re.compile(
    r"^(\d+\.\d+)[\.\:]?\s+([A-Z][\w\s,–—\-\?]+)$"
)
# Level 3: "1.2.1 Subtopic", "1.2.1. Subtopic", "1.2.1: Subtopic"
RE_HEADING_L3 = re.compile(
    r"^(\d+\.\d+\.\d+(?:\.\d+)*)[\.\:]?\s+([A-Z][\w\s,–—\-\?]+)$"
)

# FIGURE PATTERNS
# "Figure 1", "Figure 1:", "Fig. 1", "Figure 1.1", "Fig 1:"
RE_FIGURE_CAPTION = re.compile(
    r"^(?:figure|fig\.|fig)\s+(\d+(?:\.\d+)?)[:\s\-—.]*(.*)$",
    re.IGNORECASE,
)
RE_FIGURE_STANDALONE = re.compile(
    r"^(?:figure|fig\.|fig)\s+(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

# TABLE PATTERNS
# "Table 1", "Table 1:", "Table 1.1", "Tbl. 1"
RE_TABLE_CAPTION = re.compile(
    r"^(?:table|tbl\.|tbl)\s+(\d+(?:\.\d+)?)[:\s\-—.]*(.*)$",
    re.IGNORECASE,
)
RE_TABLE_STANDALONE = re.compile(
    r"^(?:table|tbl\.|tbl)\s+(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

# REFERENCES & BIBLIOGRAPHY PATTERNS
RE_REFERENCES_HEADER = re.compile(
    r"^(?:references|bibliography|works cited|literature cited)\s*$",
    re.IGNORECASE,
)
RE_REFERENCE_ENTRY = re.compile(
    r"^(?:\[\d+\]|\d+[\.\)])\s+[A-Z][a-zA-Z\s\-\.]+,?\s+.*?\b(18|19|20)\d{2}\b"
)

# LIST ITEM PATTERNS
# Numbered lists: "1.", "2.", "3.", "1)", "(1)"
RE_LIST_NUMBERED = re.compile(
    r"^(?:(\d+)[\.\)]|\((\d+)\))\s+(.*)$"
)
# Lettered lists: "a.", "b.", "c.", "a)", "(a)"
RE_LIST_LETTERED = re.compile(
    r"^(?:([a-zA-Z])[\.\)]|\(([a-zA-Z])\))\s+(.*)$"
)
# Bullet lists: "-", "•", "*", "–", "—"
RE_LIST_BULLET = re.compile(
    r"^([\*\-\•\–\—\◦\▪\▫\►\⁃])\s+(.*)$"
)

# SPECIAL SECTION PATTERNS
RE_ABSTRACT = re.compile(
    r"^(?:abstract|executive summary)\s*[:\-—]*\s*(.*)$",
    re.IGNORECASE,
)
RE_ACKNOWLEDGEMENTS = re.compile(
    r"^(?:acknowledgements?|acknowledgments?)\s*[:\-—]*\s*(.*)$",
    re.IGNORECASE,
)
RE_CONCLUSION = re.compile(
    r"^(?:conclusion|conclusions|concluding remarks|summary and conclusions)\s*[:\-—]*\s*(.*)$",
    re.IGNORECASE,
)

# AUTHOR & TITLE HEURISTIC PATTERNS
RE_AUTHOR_AFFILIATION = re.compile(
    r"\b(?:department of|university of|university|faculty of|school of|institute of|"
    r"laboratory|dr\.|prof\.|ph\.d|m\.d|by\s+[A-Z]|author:|email:|@[\w\.\-]+\.(?:edu|org|ac\.uk|gov|com))\b",
    re.IGNORECASE,
)
