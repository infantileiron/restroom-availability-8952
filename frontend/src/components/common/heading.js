import {esc} from '../../utils/html.js';

export function heading(title, description, actions = '') {
  return `<header class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>
    ${actions ? `<div class="actions">${actions}</div>` : ''}</header>`;
}

export const blank = (title, note) => `<div class="blank"><strong>${esc(title)}</strong><p>${esc(note)}</p></div>`;
