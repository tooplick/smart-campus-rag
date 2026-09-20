from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminInfo(BaseModel):
    username: str


class LoginResponseData(BaseModel):
    token: str
    token_type: str = "Bearer"
    admin: AdminInfo
    must_change_password: bool


class InitializeRequest(BaseModel):
    username: str = "admin"
    current_password: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
