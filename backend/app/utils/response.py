import math
from fastapi.responses import JSONResponse


def success_response(data=None, message: str = "success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(content={"success": True, "data": data, "message": message}, status_code=status_code)


def error_response(message: str = "请求失败", status_code: int = 400, code: str = None, details=None) -> JSONResponse:
    return JSONResponse(
        content={
            "success": False,
            "data": None,
            "message": message,
            "error": {
                "code": code or f"HTTP_{status_code}",
                "details": details,
            },
        },
        status_code=status_code,
    )


def paginated_response(items: list, page: int, page_size: int, total: int, message: str = "success") -> JSONResponse:
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    return success_response(
        data={
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
        message=message,
    )
