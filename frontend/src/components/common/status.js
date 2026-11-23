import {REASONS, STATES} from '../../constants/business.js';
import {esc} from '../../utils/html.js';

export const state = value => `<span class="status ${esc(value)}"><i></i>${esc(STATES[value])}</span>`;
export const reason = value => `<span class="status ${esc(value)}"><i></i>${esc(REASONS[value])}</span>`;
