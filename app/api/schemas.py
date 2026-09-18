"""Public Pydantic schemas for the DocXpress API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size: int
    status: str


class ElementResponse(BaseModel):
    element_id: str
    type: str
    confidence: float
    detection_method: Optional[str] = None
    reason: Optional[str] = None
    text_preview: Optional[str] = None
    applied_formatting: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    document_id: str
    status: str
    selected_model: str
    total_elements: int
    chapters: int = 0
    titles: int = 0
    authors: int = 0
    headings: int = 0
    subheadings: int = 0
    paragraphs: int = 0
    tables: int = 0
    figures: int = 0
    captions: int = 0
    lists: int = 0
    references: int = 0
    average_confidence: float
    elements: List[ElementResponse]


class AnalyzeRequest(BaseModel):
    model: str = Field(default="logistic_regression")


class FormatRequest(BaseModel):
    profile: str = Field(default="hackathon_default")
    model: str = Field(default="logistic_regression")


class PublicationPresetResponse(BaseModel):
    name: str
    body_font: str
    body_size_pt: float
    body_alignment: str
    body_line_spacing: float
    body_first_indent_cm: float
    heading_1_size_pt: float
    subheading_size_pt: float
    title_size_pt: float
    author_size_pt: float
    caption_size_pt: float
    reference_size_pt: float
    list_size_pt: float
    table_size_pt: float
    top_margin_cm: float
    bottom_margin_cm: float
    left_margin_cm: float
    right_margin_cm: float


class PublicationPresetsResponse(BaseModel):
    profiles: List[PublicationPresetResponse]


class PreservationResponse(BaseModel):
    is_identical: bool
    source_hash: str
    output_hash: str
    changed_elements: List[int]
    missing_elements: List[int]
    added_elements: List[int]


class StatusResponse(BaseModel):
    document_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    current_stage: str
    elapsed_seconds: float
    error: Optional[str] = None


class ReportResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    publication_profile: Optional[str] = None
    formatting: Dict[str, Any] = {}
    statistics: Dict[str, Any] = {}
    elements: List[ElementResponse] = []
    processing: Dict[str, float] = {}
    preservation: Optional[PreservationResponse] = None
    warnings: List[str] = []
    errors: List[str] = []


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str