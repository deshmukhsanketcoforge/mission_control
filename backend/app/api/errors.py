"""One error shape for the whole API: ``{"errors": {field: message}}``."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

REQUIRED_MESSAGE = "This field is required."


def _clean_message(error: dict) -> str:
    """Turn a pydantic error into one short sentence for the user."""
    kind = error.get("type", "")
    if kind in ("missing", "string_too_short"):
        return REQUIRED_MESSAGE
    if kind == "string_too_long":
        limit = error.get("ctx", {}).get("max_length")
        return f"Must be at most {limit} characters."
    if kind in ("float_parsing", "float_type", "finite_number"):
        return "Must be a number."
    msg = error.get("msg", "Invalid value.")
    return msg.removeprefix("Value error, ")


def error_response(status_code: int, field: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"errors": {field: message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors: dict[str, str] = {}
        for err in exc.errors():
            loc = [p for p in err["loc"] if p != "body"]
            field = str(loc[0]) if loc else "body"
            errors.setdefault(field, _clean_message(err))
        return JSONResponse(status_code=422, content={"errors": errors})
