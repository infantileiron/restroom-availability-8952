import {REASONS} from '../constants/business.js';
import {workspace} from '../stores/workspace.js';
import {blank, heading} from '../components/common/heading.js';
import {edit, field} from '../components/common/editor.js';
import {notify} from '../components/common/notifications.js';
import {reason} from '../components/common/status.js';
import {esc, formValues} from '../utils/html.js';
import {localStamp} from '../utils/format.js';

export async function outagesPage({view, user, active, refresh}) {
  const [sites, rows] = await Promise.all([workspace.facilities(), workspace.outages()]);
  if (!active()) return;
  const names = Object.fromEntries(sites.map(site => [site.code, site.name]));
  const siteOptions = sites.map(site => `<option value="${esc(site.code)}">${esc(site.name)}</option>`).join('');
  view.innerHTML = heading('停用核对', '登记停水与设备故障，保留现场原始起止时间。', user.role === 'analyst' ?
    '<button class="primary" id="new-outage">登记停用</button>' : '') +
    `<section class="sheet"><div class="table-heading"><div><h2>巡维记录</h2><p id="outage-count"></p></div>
    <label class="compact-field"><span>设施</span><select id="site-filter"><option value="">全部设施</option>${siteOptions}</select></label></div>
    <div id="outage-table"></div></section><aside class="note"><strong>闭馆时段</strong><span>停用记录可以超出开放窗口。月度核算会裁掉闭馆区间，并合并同一设施的重叠记录。</span></aside>`;
  const filter = view.querySelector('#site-filter');
  const renderRows = () => {
    const shown = rows.filter(row => !filter.value || row.facility_code === filter.value);
    view.querySelector('#outage-count').textContent = `${shown.length} 条记录 · 现场上报时间`;
    view.querySelector('#outage-table').innerHTML = !shown.length ? blank('暂无停用记录', '更换设施筛选，或登记新的停用记录。') :
      `<div class="scroll-table"><table><thead><tr><th>记录编号 / 设施</th><th>停用原因</th><th>开始</th><th>恢复</th><th>巡维备注</th></tr></thead>
      <tbody>${shown.map(row => `<tr><th scope="row"><strong>${esc(names[row.facility_code])}</strong><small class="mono">${esc(row.code)}</small></th>
      <td>${reason(row.reason)}</td><td class="mono nowrap">${localStamp(row.starts_at)}</td><td class="mono nowrap">${localStamp(row.ends_at)}</td>
      <td>${esc(row.note)}</td></tr>`).join('')}</tbody></table></div>`;
  };
  filter.onchange = renderRows;
  renderRows();
  const button = view.querySelector('#new-outage');
  if (!button) return;
  button.disabled = !sites.length;
  button.onclick = () => edit('登记停用',
    `<div class="form-grid">${field('记录编号', '<input name="code" required maxlength="24" pattern="[A-Z0-9][A-Z0-9\\-]{1,23}" placeholder="例 WX-1109">')}
    ${field('设施', `<select name="facility_code">${siteOptions}</select>`)}</div>
    ${field('停用原因', `<select name="reason">${Object.entries(REASONS).map(([code, label]) => `<option value="${code}">${label}</option>`).join('')}</select>`)}
    <div class="form-grid">${field('停用开始', '<input name="starts_at" type="datetime-local" required>')}
    ${field('恢复时间', '<input name="ends_at" type="datetime-local" required>')}</div>
    ${field('巡维备注', '<textarea name="note" maxlength="240" required rows="2"></textarea>')}`, async form => {
      await workspace.createOutage(formValues(form));
      return () => { notify('停用记录已登记'); refresh(); };
    });
}
