from datetime import datetime, time
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from src.constants.business import Reason
from src.utils.calendar import minutes

Code = Annotated[str, StringConstraints(pattern=r'^[A-Z0-9][A-Z0-9-]{1,23}$')]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class FacilityInput(BaseModel):
    code: Code
    name: Text
    district: Text


class WindowInput(BaseModel):
    weekdays: Annotated[set[Annotated[int, Field(ge=0, le=6)]], Field(min_length=1)]
    start: time
    end: time
    overnight: bool = False

    @model_validator(mode='after')
    def validate_window(self):
        for clock in (self.start, self.end):
            if clock.second or clock.microsecond or clock.tzinfo is not None:
                raise ValueError('开放时间只接受本地时分')
        if not 0 < self.end_min - self.start_min <= 1440:
            raise ValueError('开放窗口须大于零且不超过 24 小时，请核对是否勾选次日结束')
        return self

    @property
    def start_min(self):
        return minutes(self.start)

    @property
    def end_min(self):
        return minutes(self.end) + (1440 if self.overnight else 0)


class OutageInput(BaseModel):
    code: Code
    facility_code: Code
    reason: Reason
    starts_at: datetime
    ends_at: datetime
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]

    @model_validator(mode='after')
    def validate_outage(self):
        for stamp in (self.starts_at, self.ends_at):
            if stamp.second or stamp.microsecond or stamp.tzinfo is not None:
                raise ValueError('停用记录只接受北京时间，精确到分钟')
        if self.ends_at <= self.starts_at:
            raise ValueError('恢复时间必须晚于停用开始时间')
        return self
