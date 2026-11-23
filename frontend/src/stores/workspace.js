import {api} from '../api/client.js';

export const workspace = {
  facilities: () => api('/facilities'),
  outages: () => api('/outages'),
  snapshots: () => api('/snapshots'),
  snapshot: id => api(`/snapshots/${id}`),
  createFacility: input => api('/facilities', input),
  addWindow: (code, input) => api(`/facilities/${code}/windows`, input),
  createOutage: input => api('/outages', input),
  capture: input => api('/snapshots', input),
  run: id => api(`/snapshots/${id}/run`, {}),
  publish: id => api(`/snapshots/${id}/publish`, {}),
};
