export const ROLES = {analyst: '分析员', reviewer: '业务复核', viewer: '观察员'};
export const REASONS = {water: '停水', fault: '设备故障'};
export const STATES = {draft: '待核算', queued: '核算中', ready: '待复核', published: '已发布', failed: '核算失败'};
export const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
export const DEMO_MONTH = '2026-11';

export const WINDOW_TYPES = {
  extension: '延长开放',
  reduction: '缩短开放',
  closed: '整日关闭',
};
export const RULE_SOURCES = {
  festival: '节庆办通知',
  station: '环卫站调度',
  hotline: '值班热线登记',
};
export const RULE_SOURCE_PRIORITY = {festival: 30, station: 20, hotline: 10};
export const ADJUDICATION_MODES = {
  priority: '按来源优先级整体裁决',
  minute: '按分钟拆分合并',
};
export const VERSION_STATES = {draft: '草稿', active: '生效中'};
