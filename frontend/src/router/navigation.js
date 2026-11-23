const pattern = /^(calendar|outages|runs|reports)(?:\/(\d+))?$/;

export function route(role) {
  const match = location.hash.slice(1).match(pattern);
  const fallback = role === 'viewer' ? 'reports' : 'calendar';
  if (!match || (role === 'viewer' && match[1] === 'runs')) return {section: fallback};
  return {section: match[1], id: match[2]};
}

export function go(path) {
  location.hash = path;
}
