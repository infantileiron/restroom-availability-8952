import {esc} from '../../utils/html.js';
import {clock} from '../../utils/format.js';

export const timeAxis = () => `<div class="time-axis" aria-hidden="true">${['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00']
  .map(t => `<span>${t}</span>`).join('')}</div>`;

function segment([start, end], style) {
  const label = `${start === 1440 ? '24:00' : clock(start)}–${end === 1440 ? '24:00' : clock(end)}`;
  return `<span class="segment ${style}" style="--start:${start / 14.4}%;--duration:${(end - start) / 14.4}%" title="${label}"></span>`;
}

export function track({planned = [], lost = [], overlay = [], label = ''}) {
  return `<div class="track" role="img" aria-label="${esc(label)}">
    ${planned.map(interval => segment(interval, 'plan')).join('')}
    ${overlay.map(interval => segment(interval, 'overlay')).join('')}
    ${lost.map(interval => segment(interval, 'loss')).join('')}
    ${planned.length ? '' : '<span class="no-track">无开放计划</span>'}</div>`;
}
