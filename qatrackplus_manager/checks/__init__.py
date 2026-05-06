from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ScanResult:
    label: str
    status: str  # "ok" | "fail" | "warn" | "info"
    detail: str = ""

@dataclass
class TestResult:
    label: str
    status: str  # "pass" | "fail" | "warn" | "info"
    detail: str = ""
