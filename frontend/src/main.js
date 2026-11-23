import {api} from './api/client.js';
import {shell} from './components/shell.js';
import {blank} from './components/common/heading.js';
import {calendarPage} from './pages/calendar.js';
import {login} from './pages/login.js';
import {outagesPage} from './pages/outages.js';
import {detailPage} from './pages/snapshot-detail.js';
import {snapshotsPage} from './pages/snapshots.js';
import {route} from './router/navigation.js';
import {session} from './stores/session.js';

const app = document.querySelector('#app');
let revision = 0;

async function render() {
  const current = ++revision;
  const active = () => revision === current;
  const user = session.user;
  if (!user) {
    login(app, render);
    return;
  }
  const {section, id} = route(user.role);
  app.innerHTML = shell(section, user);
  app.querySelector('#logout').onclick = () => { session.clear(); history.replaceState(null, '', '/'); render(); };
  const view = app.querySelector('#view');
  const context = {view, user, active, refresh: render};
  view.innerHTML = '<p class="loading">正在加载工作记录…</p>';
  try {
    if (section === 'calendar') await calendarPage(context);
    else if (section === 'outages') await outagesPage(context);
    else if (id) await detailPage(context, section, id);
    else await snapshotsPage(context, section === 'reports');
  } catch (error) {
    if (!active()) return;
    view.innerHTML = blank('暂时无法打开页面', error.message) + '<button class="secondary" id="reload">重试</button>';
    view.querySelector('#reload').onclick = render;
  }
}

window.addEventListener('hashchange', render);
window.addEventListener('session-expired', render);
if (session.token) {
  try { session.resume(await api('/me')); } catch { session.clear(); }
}
render();
