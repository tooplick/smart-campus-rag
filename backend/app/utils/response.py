from fastapi.responses import JSONResponse


def success_response(data=None, message: str = "success") -> JSONResponse:
    return JSONResponse(content={"success": True, "data": data, "message": message})


def error_response(message: str = "error", status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        content={"success": False, "data": None, "message": message},
        status_code=status_code,
    )
