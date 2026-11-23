import {session} from '../stores/session.js';

export async function api(path, payload, raw = false, method) {
  const headers = {};
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  if (payload !== undefined) headers['Content-Type'] = 'application/json';
  const verb = method || (payload === undefined ? 'GET' : 'POST');
  let response;
  try {
    response = await fetch(`/api${path}`, {
      headers, method: verb, body: payload === undefined ? undefined : JSON.stringify(payload),
    });
  } catch {
    throw new Error('连接中断，请检查网络后重试');
  }
  if (!response.ok) {
    if (response.status === 401 && path !== '/login') {
      session.clear();
      window.dispatchEvent(new Event('session-expired'));
    }
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `请求失败（${response.status}）`);
  }
  return raw ? response : response.json();
}

export async function download(snapshot, suffix = 'export', filename) {
  const response = await api(`/snapshots/${snapshot.id}/${suffix}`, undefined, true);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename || `开放时段-${snapshot.month}-V${snapshot.id}.csv`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
