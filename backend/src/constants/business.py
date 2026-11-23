from enum import StrEnum


class Role(StrEnum):
    ANALYST = 'analyst'
    REVIEWER = 'reviewer'
    VIEWER = 'viewer'


class Reason(StrEnum):
    WATER = 'water'
    FAULT = 'fault'


class Status(StrEnum):
    DRAFT = 'draft'
    QUEUED = 'queued'
    READY = 'ready'
    PUBLISHED = 'published'
    FAILED = 'failed'


class TempWindowType(StrEnum):
    EXTENSION = 'extension'   # 延长开放
    REDUCTION = 'reduction'   # 缩短开放
    CLOSED = 'closed'         # 整日关闭


class RuleSource(StrEnum):
    FESTIVAL = 'festival'     # 节庆办通知
    STATION = 'station'       # 环卫站调度
    HOTLINE = 'hotline'       # 值班热线登记


class RuleVersionStatus(StrEnum):
    DRAFT = 'draft'
    ACTIVE = 'active'


class AdjudicationMode(StrEnum):
    PRIORITY = 'priority'     # 按来源优先级整体裁决
    MINUTE = 'minute'         # 按分钟拆分合并


# 数值越大优先级越高；整体裁决与分钟拆分共用同一优先级次序
SOURCE_PRIORITY = {
    RuleSource.FESTIVAL: 30,
    RuleSource.STATION: 20,
    RuleSource.HOTLINE: 10,
}

FORMULA_VERSION = 'facility-minute-v2'
