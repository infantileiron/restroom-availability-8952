from datetime import date, time
from typing import Annotated

from pydantic import BaseModel, StringConstraints, model_validator

from src.constants.business import AdjudicationMode, RuleSource, TempWindowType
from src.utils.calendar import minutes

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)]


class RuleVersionInput(BaseModel):
    label: Text
    adjudication_mode: AdjudicationMode = AdjudicationMode.PRIORITY


class TempWindowInput(BaseModel):
    facility_code: Annotated[str, StringConstraints(pattern=r'^[A-Z0-9][A-Z0-9-]{1,23}$')]
    window_type: TempWindowType
    source: RuleSource
    open_date: date
    start: time
    end: time
    overnight: bool = False
    note: Note = ''

    @model_validator(mode='after')
    def validate_window(self):
        for clock in (self.start, self.end):
            if clock.second or clock.microsecond or clock.tzinfo is not None:
                raise ValueError('节庆窗口只接受本地时分')
        if self.window_type == TempWindowType.CLOSED:
            # 整日关闭固定为开门日 00:00–24:00（结束填 00:00 并勾选次日结束）。
            if (self.start.hour, self.start.minute, self.end.hour, self.end.minute) != (0, 0, 0, 0) \
                    or not self.overnight:
                raise ValueError('整日关闭固定为开门日 00:00–24:00，请保持起止 00:00 并勾选次日结束')
        if not 0 < self.end_min - self.start_min <= 1440:
            raise ValueError('临时窗口须大于零且不超过 24 小时，请核对是否勾选次日结束')
        return self

    @property
    def start_min(self):
        if self.window_type == TempWindowType.CLOSED:
            return 0
        return minutes(self.start)

    @property
    def end_min(self):
        if self.window_type == TempWindowType.CLOSED:
            return 1440
        return minutes(self.end) + (1440 if self.overnight else 0)
