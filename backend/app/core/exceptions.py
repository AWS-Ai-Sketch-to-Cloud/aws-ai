from __future__ import annotations

import json

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


def extract_validation_message(exc: RequestValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors():
        message = error.get("msg")
        if isinstance(message, str) and message.startswith("Value error, "):
            message = message.removeprefix("Value error, ").strip()
        if message and message not in messages:
            messages.append(message)
    if not messages:
        return "입력값을 다시 확인해 주세요."
    return "\n".join(messages)


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=422,
        content={"detail": extract_validation_message(exc), "requestId": get_request_id()},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = get_request_id()
    if exc.status_code >= 500:
        print(
            json.dumps(
                {
                    "type": "http_error",
                    "requestId": request_id,
                    "status": exc.status_code,
                    "path": request.url.path,
                    "detail": exc.detail,
                },
                ensure_ascii=False,
            )
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "requestId": request_id})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id()
    print(
        json.dumps(
            {
                "type": "unhandled_error",
                "requestId": request_id,
                "path": request.url.path,
                "errorType": type(exc).__name__,
                "error": str(exc),
            },
            ensure_ascii=False,
        )
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "requestId": request_id},
    )
