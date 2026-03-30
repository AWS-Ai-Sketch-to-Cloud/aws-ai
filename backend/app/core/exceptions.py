from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


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
    return JSONResponse(status_code=422, content={"detail": extract_validation_message(exc)})
