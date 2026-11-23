import {ROLES} from '../constants/business.js';
import {esc} from '../utils/html.js';

const links = [['calendar', '开放日历', 'calendar'], ['outages', '停用核对', 'outage'],
  ['runs', '窗口核算', 'clock'], ['reports', '月报审阅', 'report']];

const icons = {
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v5m8-5v5m-9 6h4m2 3h4"/>',
  outage: '<path d="M12 3 2 20h20L12 3Z M12 9v5m0 3v.1"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  report: '<path d="M6 3h8l4 4v14H6z M14 3v5h4M9 12h6m-6 4h6"/>',
};

const icon = key => `<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">${icons[key]}</svg>`;

export const brand = () => `<div class="brand"><span class="logo" aria-hidden="true">${icon('clock')}</span>
  <div><strong>坊洁巡维</strong><small>公厕开放时段核算</small></div></div>`;

export function shell(section, user) {
  const visibleLinks = links.filter(([key]) => user.role !== 'viewer' || key !== 'runs');
  return `<div class="workspace"><aside class="sidebar">${brand()}<nav aria-label="业务导航">
    ${visibleLinks.map(([key, text, glyph]) => `<a href="#${key}" ${section === key ? 'aria-current="page"' : ''}>${icon(glyph)}${text}</a>`).join('')}
    </nav><div class="sidebar-bottom"><div class="identity"><span class="avatar">${esc(user.display_name.slice(-1))}</span>
    <div><strong>${esc(user.display_name)}</strong><small>${ROLES[user.role]}</small></div></div>
    <button id="logout" type="button" class="logout">退出登录</button></div></aside>
    <div class="workspace-body"><div class="topbar"><span>坊洁市政环卫 · 巡维值班室</span><span class="timezone">UTC+08:00 <span>北京时间</span></span></div>
    <main id="view" class="view" tabindex="-1" aria-live="polite"></main></div></div>`;
}
