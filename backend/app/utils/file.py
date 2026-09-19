import hashlib
import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_storage_path() -> Path:
    path = Path(settings.FILE_STORAGE_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def generate_storage_path(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return str(get_storage_path() / unique_name)


def compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }
    return mime_map.get(ext, "application/octet-stream")
