from datetime import datetime
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.subscription.rules import CONFIG_FORMATS


def _validate_pattern(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    try:
        re.compile(value)
    except re.error as exc:
        raise ValueError(f"Invalid regular expression: {exc}")
    return value


def _validate_format(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    if value not in CONFIG_FORMATS:
        raise ValueError(f"config_format must be one of {', '.join(CONFIG_FORMATS)}")
    return value


class SubscriptionRuleBase(BaseModel):
    name: str = Field(max_length=64)
    pattern: str = Field(max_length=512)
    config_format: str
    as_base64: bool = False
    reverse: bool = False
    priority: int = Field(default=100, ge=0, le=10000)
    ignore_case: bool = False
    min_version: Optional[str] = Field(default=None, max_length=32)
    max_version: Optional[str] = Field(default=None, max_length=32)
    is_disabled: bool = False

    @field_validator("pattern")
    @classmethod
    def check_pattern(cls, value):
        return _validate_pattern(value)

    @field_validator("config_format")
    @classmethod
    def check_format(cls, value):
        return _validate_format(value)


class SubscriptionRuleCreate(SubscriptionRuleBase):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "happ-json",
            "pattern": "^Happ/(\\d+\\.\\d+\\.\\d+)",
            "config_format": "v2ray-json",
            "priority": 80,
            "min_version": "1.11.0",
        }
    })


class SubscriptionRuleModify(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    pattern: Optional[str] = Field(default=None, max_length=512)
    config_format: Optional[str] = None
    as_base64: Optional[bool] = None
    reverse: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10000)
    ignore_case: Optional[bool] = None
    min_version: Optional[str] = Field(default=None, max_length=32)
    max_version: Optional[str] = Field(default=None, max_length=32)
    is_disabled: Optional[bool] = None

    @field_validator("pattern")
    @classmethod
    def check_pattern(cls, value):
        return _validate_pattern(value)

    @field_validator("config_format")
    @classmethod
    def check_format(cls, value):
        return _validate_format(value)


class SubscriptionRuleResponse(SubscriptionRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SubscriptionRulesResponse(BaseModel):
    rules: List[SubscriptionRuleResponse]
    formats: List[str] = list(CONFIG_FORMATS)


class SubscriptionTokenCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class SubscriptionTokenResponse(BaseModel):
    id: int
    name: Optional[str] = None
    token: str
    url: str = ""
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_user_agent: Optional[str] = None
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class SubscriptionTokensResponse(BaseModel):
    tokens: List[SubscriptionTokenResponse]


class SubscriptionClientPreview(BaseModel):
    """What a given User-Agent would receive."""

    user_agent: str
    rule: str
    config_format: str
    as_base64: bool
    reverse: bool
    media_type: str
    source: str
