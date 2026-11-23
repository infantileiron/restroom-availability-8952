const whole = new Intl.NumberFormat('zh-CN');
export const number = value => whole.format(value);
export const percent = value => value == null ? '—' : `${value}%`;
export const localStamp = stamp => stamp.replace('T', ' ').slice(0, 16);
export const clock = minute => {
  const base = minute % 1440;
  const two = value => String(value).padStart(2, '0');
  return `${minute >= 1440 ? '次日 ' : ''}${two(Math.floor(base / 60))}:${two(base % 60)}`;
};
