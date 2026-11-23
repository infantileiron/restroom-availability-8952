const entities = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'};
export const esc = value => String(value ?? '').replace(/[&<>"']/g, char => entities[char]);
export const formValues = form => Object.fromEntries(new FormData(form));
