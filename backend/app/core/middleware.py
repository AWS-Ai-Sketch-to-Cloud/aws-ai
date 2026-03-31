from __future__ import annotations

import json
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass
from threading import Lock

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import set_request_id

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'self'",
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


class RequestIdAndAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(request_id)
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        row = {
            "type": "access",
            "requestId": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "durationMs": elapsed_ms,
            "clientIp": _client_ip(request),
        }
        print(json.dumps(row, ensure_ascii=False))
        return response


@dataclass
class _RateBucket:
    timestamps: deque[float]


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit: int = 20, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._buckets: dict[str, _RateBucket] = {}

    def _bucket_key(self, request: Request) -> str | None:
        path = request.url.path
        if path not in {"/api/auth/login", "/api/auth/register"}:
            return None
        return f"{_client_ip(request)}:{path}"

    def _prune_and_get(self, key: str) -> _RateBucket:
        now = time.time()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _RateBucket(timestamps=deque())
            self._buckets[key] = bucket
        while bucket.timestamps and (now - bucket.timestamps[0]) > self.window_seconds:
            bucket.timestamps.popleft()
        return bucket

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        key = self._bucket_key(request)
        if not key:
            return await call_next(request)

        with self._lock:
            bucket = self._prune_and_get(key)
            if len(bucket.timestamps) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            "인증 요청이 너무 많습니다. 잠시 후 다시 시도하세요. "
                            f"(limit={self.limit}/{self.window_seconds}s)"
                        )
                    },
                )

        response = await call_next(request)
        if response.status_code >= 400:
            with self._lock:
                bucket = self._prune_and_get(key)
                bucket.timestamps.append(time.time())
                if len(bucket.timestamps) > self.limit:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": (
                                "인증 요청이 너무 많습니다. 잠시 후 다시 시도하세요. "
                                f"(limit={self.limit}/{self.window_seconds}s)"
                            )
                        },
                    )
        return response


def auth_rate_limit() -> tuple[int, int]:
    limit = int(os.getenv("AUTH_RATE_LIMIT", "20"))
    window = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
    return max(1, limit), max(1, window)
