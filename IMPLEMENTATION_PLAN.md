# DocXpress — Implementation Plan & Roadmap

## Phase Overview

- [x] **Phase 0: Architectural Design & System Blueprint** (Complete — see `ARCHITECTURE.md`)
- [x] **Phase 1: Project Scaffolding, Canonical AST & Read-Only DOCX Parser** (Complete)
- [x] **Phase 2: Feature Engineering, ML Classification & Contextual Smoother** (Complete)
- [ ] **Phase 3: Typographic Synthesis, Book Layout Presets & DOCX Emitter**
- [ ] **Phase 4: Content Preservation Verifier & 400+ Page Scalability**
- [ ] **Phase 5: Web Application Layer (FastAPI Backend & React Frontend)**

---

## Phase 1 Scope & Deliverables

### Goals
1. Establish a production-grade Python package structure independent of web frameworks.
2. Design and implement the **Canonical Document AST**:
   - `CanonicalDocument`, `DocumentMetadata`
   - Elements: `ParagraphElement`, `HeadingElement`, `TitleElement`, `AuthorElement`, `TableElement`, `FigureElement`, `CaptionElement`, `ListElement`, `ReferenceElement`, `UnknownElement`
   - Strict immutability guarantee: `original_text` cannot be mutated after parsing.
   - Run-level typography metadata: `text`, `is_bold`, `is_italic`, `is_underline`, `font_name`, `font_size_pt`, `is_superscript`, `is_subscript`.
3. Implement read-only **DOCX Parser**:
   - Reads `.docx` using `python-docx` without writing or touching the source file.
   - Preserves true document sequence (interleaved paragraphs, tables, drawings) via direct XML body traversal.
   - Extracts paragraph styles, inline images/shapes, numbering definitions (`numPr`), and tables.
4. Implement **Content Preservation Baseline**:
   - Deterministic Unicode and whitespace normalization.
   - Ordered text sequence extraction.
   - SHA-256 fingerprinting of normalized textual content.
5. Create deterministic test documents covering all 12 key elements.
6. Exhaustive automated pytest test suite validating parser, AST, immutability, and preservation.
