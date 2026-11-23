import {WEEKDAYS} from '../constants/business.js';
import {workspace} from '../stores/workspace.js';
import {heading, blank} from '../components/common/heading.js';
import {edit, field} from '../components/common/editor.js';
import {notify} from '../components/common/notifications.js';
import {timeAxis, track} from '../components/common/timeline.js';
import {clock} from '../utils/format.js';
import {esc, formValues} from '../utils/html.js';

const codeInput = '<input name="code" required maxlength="24" pattern="[A-Z0-9][A-Z0-9\\-]{1,23}" placeholder="例 FJ-05">';
const weekdays = WEEKDAYS.map((day, n) => `<label class="check"><input type="checkbox" name="weekdays" value="${n}" checked>${day}</label>`).join('');

export async function calendarPage({view, user, active, refresh}) {
  const sites = await workspace.facilities();
  if (!active()) return;
  const analyst = user.role === 'analyst';
  const actions = analyst ? '<button class="secondary" id="new-facility">新增设施</button><button class="primary" id="new-window">录入开放窗口</button>' : '';
  view.innerHTML = heading('开放日历', '按设施核对常设开放窗口，跨夜规则归属起始日。', actions) +
    `<div class="section-bar"><div><h2>每周开放计划</h2><p>${sites.length} 座设施 · 北京时间</p></div>
    <div class="legend"><span><i></i>计划开放</span><span><i class="carry"></i>前日跨入</span></div></div>
    <section class="sheet calendar-sheet"><div class="day-selector" aria-label="选择星期">${WEEKDAYS.map((day, n) =>
      `<button type="button" data-day="${n}" aria-pressed="${n === 3}">${day}</button>`).join('')}</div>
      <div id="calendar-rows"></div></section>
    <aside class="note"><strong>跨夜规则</strong><span>例如 20:00–次日 02:00，次日凌晨两小时仍计入计划开放。重叠的开放窗口在核算时取并集。</span></aside>`;
  const renderRows = day => {
    const rows = view.querySelector('#calendar-rows');
    rows.innerHTML = sites.length ? `<div class="calendar-grid axis"><span>设施 / 开放规则</span>${timeAxis()}</div>` + sites.map(site => {
      const today = site.windows.filter(window => window.weekday === day);
      const carry = site.windows.filter(window => window.weekday === (day + 6) % 7 && window.end_min > 1440);
      const segments = today.map(window => [window.start_min, Math.min(1440, window.end_min)]);
      const overlays = carry.map(window => [0, window.end_min - 1440]);
      const notes = today.map(window => `${clock(window.start_min)}–${clock(window.end_min)}`);
      return `<div class="calendar-grid site-row"><div><strong>${esc(site.name)}</strong>
      <small>${esc(site.code)} · ${esc(site.district)}</small><div class="rules">${notes.join(' / ') || (carry.length ? '前日跨入' : '本日无计划')}</div></div>
      ${track({planned: [...overlays, ...segments], overlay: overlays, label: notes.join(' / ') || '无当日开门规则'})}</div>`;
    }).join('') : blank('尚无设施', '分析员可先登记设施，再录入一周的开放规则。');
  };
  renderRows(3);
  for (const button of view.querySelectorAll('[data-day]')) button.onclick = () => {
    view.querySelector('[aria-pressed=true]').setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-pressed', 'true');
    renderRows(Number(button.dataset.day));
  };
  if (!analyst) return;
  view.querySelector('#new-facility').onclick = () => edit('新增设施',
    field('设施编号', codeInput) + field('设施名称', '<input name="name" required maxlength="80">') +
    field('所属片区', '<input name="district" required maxlength="80">'), async form => {
      await workspace.createFacility(formValues(form));
      return () => { notify('设施已登记'); refresh(); };
    });
  const add = view.querySelector('#new-window');
  add.disabled = !sites.length;
  add.onclick = () => edit('录入开放窗口', field('设施', `<select name="code">${sites.map(site =>
    `<option value="${esc(site.code)}">${esc(site.name)}</option>`).join('')}</select>`) +
    `<fieldset><legend>起始日</legend><div class="days-check">${weekdays}</div></fieldset><div class="form-grid">
    ${field('开门时间', '<input name="start" type="time" required>')}
    ${field('关门时间', '<input name="end" type="time" required>')}</div>
    <label class="check"><input type="checkbox" name="overnight">次日结束</label>`, async form => {
    const values = formValues(form);
    const days = new FormData(form).getAll('weekdays').map(Number);
    if (!days.length) throw new Error('请选择至少一个起始日');
    const result = await workspace.addWindow(values.code, {weekdays: days, start: values.start,
      end: values.end, overnight: Boolean(values.overnight)});
    return () => { notify(result.added.length ? `已录入 ${result.added.length} 个起始日` : '该规则已登记'); refresh(); };
  });
}
