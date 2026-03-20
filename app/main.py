from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from jsonschema import ValidationError, validate
from pydantic import BaseModel, Field

CONTRACT_VERSION = "v1"
ROOT = Path(__file__).resolve().parents[1]
ARCH_SCHEMA_PATH = ROOT / "A_JSON_스키마_v1.json"

with ARCH_SCHEMA_PATH.open("r", encoding="utf-8") as f:
    import json

    ARCH_SCHEMA = json.load(f)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_session_id() -> str:
    return f"ses_{uuid4().hex[:12]}"


class SessionCreateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)


class AnalyzeRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=2000)
    input_type: Literal["text", "sketch"] = "text"


class ErrorPayload(BaseModel):
    code: Literal["PARSE_ERROR", "SCHEMA_ERROR", "TIMEOUT_ERROR", "INTERNAL_ERROR"]
    message: str


class SessionState(BaseModel):
    session_id: str
    project_id: str
    status: Literal["created", "analyzing", "generated", "failed"]
    input_text: str
    parsed_json: dict[str, Any] | None
    error: ErrorPayload | None
    created_at: str
    updated_at: str
    contract_version: Literal["v1"] = CONTRACT_VERSION


class SessionCreateResponse(BaseModel):
    session_id: str
    project_id: str
    status: Literal["created"]
    created_at: str
    contract_version: Literal["v1"] = CONTRACT_VERSION


class AnalyzeResponse(BaseModel):
    session_id: str
    status: Literal["generated", "failed"]
    parsed_json: dict[str, Any] | None = None
    error: ErrorPayload | None = None
    contract_version: Literal["v1"] = CONTRACT_VERSION


REGION_KEYWORDS = {
    "ap-northeast-2": ["서울", "seoul", "ap-northeast-2"],
    "ap-northeast-1": ["도쿄", "tokyo", "ap-northeast-1"],
    "ap-southeast-1": ["싱가포르", "singapore", "ap-southeast-1"],
    "us-east-1": ["버지니아", "virginia", "n. virginia", "us-east-1"],
    "us-east-2": ["오하이오", "ohio", "us-east-2"],
}


def parse_count(text: str) -> int:
    lowered = text.lower()
    patterns = [
        r"(?:ec2|서버)\s*(\d+)\s*(?:개|대)?",
        r"(\d+)\s*(?:개|대)\s*(?:ec2|서버)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, lowered)
        if matched:
            return max(1, min(10, int(matched.group(1))))

    korean_map = {
        "한": 1,
        "하나": 1,
        "두": 2,
        "둘": 2,
        "세": 3,
        "셋": 3,
        "네": 4,
        "넷": 4,
    }
    for key, value in korean_map.items():
        if f"{key} 대" in text or f"{key}개" in text:
            return value

    if "여러 대" in text or "여러개" in text or "여러 개" in text:
        return 2
    return 1


def parse_region(text: str) -> str:
    lowered = text.lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return region
    return "ap-northeast-2"


def parse_instance_type(text: str) -> str:
    lowered = text.lower()
    if "t3.medium" in lowered:
        return "t3.medium"
    if "t3.small" in lowered:
        return "t3.small"
    return "t3.micro"


def parse_public(text: str) -> bool:
    lowered = text.lower()
    private_signals = ["비공개", "공개 안", "외부 공개 안", "private", "내부망", "private 환경"]
    public_signals = ["퍼블릭", "공개", "인터넷", "public"]
    if any(k in lowered for k in private_signals):
        return False
    if any(k in lowered for k in public_signals):
        return True
    return False


def parse_rds(text: str) -> dict[str, Any]:
    lowered = text.lower()
    no_db_signals = ["db 없음", "rds 없음", "db 필요 없음", "db는 필요 없음", "rds 빼"]
    if any(k in lowered for k in no_db_signals):
        return {"enabled": False, "engine": None}
    if "mysql" in lowered:
        return {"enabled": True, "engine": "mysql"}
    if "postgres" in lowered or "postgresql" in lowered:
        return {"enabled": True, "engine": "postgres"}
    return {"enabled": False, "engine": None}


def parse_input_to_architecture(input_text: str) -> dict[str, Any]:
    text = input_text.strip()
    result = {
        "vpc": True,
        "ec2": {
            "count": parse_count(text),
            "instance_type": parse_instance_type(text),
        },
        "rds": parse_rds(text),
        "public": parse_public(text),
        "region": parse_region(text),
    }
    return result


app = FastAPI(title="Sketch-to-Cloud API", version=CONTRACT_VERSION)
store: dict[str, SessionState] = {}
store_lock = Lock()


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
    now = utc_now_iso()
    session_id = generate_session_id()
    session = SessionState(
        session_id=session_id,
        project_id=payload.project_id,
        status="created",
        input_text="",
        parsed_json=None,
        error=None,
        created_at=now,
        updated_at=now,
    )
    with store_lock:
        store[session_id] = session

    return SessionCreateResponse(
        session_id=session_id,
        project_id=payload.project_id,
        status="created",
        created_at=now,
    )


@app.post("/sessions/{session_id}/analyze", response_model=AnalyzeResponse)
def analyze_session(session_id: str, payload: AnalyzeRequest) -> AnalyzeResponse:
    with store_lock:
        session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    session.status = "analyzing"
    session.updated_at = utc_now_iso()
    session.input_text = payload.input_text

    try:
        parsed = parse_input_to_architecture(payload.input_text)
        validate(instance=parsed, schema=ARCH_SCHEMA)
        session.status = "generated"
        session.parsed_json = parsed
        session.error = None
    except ValidationError as e:
        session.status = "failed"
        session.parsed_json = None
        session.error = ErrorPayload(code="SCHEMA_ERROR", message=e.message)
    except Exception as e:  # noqa: BLE001
        session.status = "failed"
        session.parsed_json = None
        session.error = ErrorPayload(code="INTERNAL_ERROR", message=str(e))

    session.updated_at = utc_now_iso()
    with store_lock:
        store[session_id] = session

    if session.status == "generated":
        return AnalyzeResponse(
            session_id=session_id,
            status="generated",
            parsed_json=session.parsed_json,
        )
    return AnalyzeResponse(
        session_id=session_id,
        status="failed",
        error=session.error,
    )


@app.get("/sessions/{session_id}", response_model=SessionState)
def get_session(session_id: str) -> SessionState:
    with store_lock:
        session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session
