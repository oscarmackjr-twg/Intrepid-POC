"""Pydantic models used by the cashflow API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

CashflowMode = Literal["current_assets", "sg", "cibc"]
CashflowJobStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
CashflowFolder = Literal["inputs", "outputs"]


class CashflowFileEntry(BaseModel):
    key: str
    name: str
    folder: CashflowFolder
    size: int
    last_modified: Optional[datetime] = None


class CashflowJobRequest(BaseModel):
    mode: CashflowMode
    buy_num: str = "93rd"
    purchase_date: str = "2026-02-24"
    target: float = 7.9
    cprshock: float = 1.0
    cdrshock: float = 1.0
    workers: int = 1
    current_assets_file: str = "current_assets.csv"
    current_assets_output: str = ""
    prime_file: Optional[str] = None
    sfy_file: Optional[str] = None
    master_sheet: str = "MASTER_SHEET.xlsx"
    notes_sheet: str = "MASTER_SHEET - Notes.xlsx"


class CashflowJobDefaults(BaseModel):
    mode: CashflowMode
    buy_num: str
    purchase_date: str
    target: float
    cprshock: float
    cdrshock: float
    workers: int
    current_assets_file: Optional[str] = None
    current_assets_output: Optional[str] = None
    prime_file: Optional[str] = None
    sfy_file: Optional[str] = None
    master_sheet: Optional[str] = None
    notes_sheet: Optional[str] = None


class CashflowDefaultsResponse(BaseModel):
    bucket: str
    defaults: Dict[CashflowMode, CashflowJobDefaults]


class CashflowJobResponse(BaseModel):
    job_id: str
    status: CashflowJobStatus
    mode: CashflowMode
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request: Dict[str, Any] = Field(default_factory=dict)
    output_files: List[CashflowFileEntry] = Field(default_factory=list)
    progress_percent: int = 0
    progress_message: Optional[str] = None
    log_messages: List[str] = Field(default_factory=list)
    error_detail: Optional[str] = None
    cancel_requested: bool = False

