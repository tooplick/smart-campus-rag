from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    must_change_password: bool
    username: str


class InitializeRequest(BaseModel):
    new_password: str
    new_username: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
