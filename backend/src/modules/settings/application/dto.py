from pydantic import BaseModel


class SettingsResponse(BaseModel):
    settings: dict[str, str]


class UpdateSettingRequest(BaseModel):
    value: str
