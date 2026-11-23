/** @typedef {{planned_minutes: number, lost_minutes: number, available_minutes: number,
 * availability_pct: string|null}} Availability */
/** @typedef {{planned: [number, number][], lost: [number, number][]}} DayTimeline */
/** @typedef {Availability & {code: string, name: string, district: string,
 * out_of_window_minutes: number, daily: Record<string, DayTimeline>}} FacilityResult */
