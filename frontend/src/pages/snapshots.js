import {DEMO_MONTH} from '../constants/business.js';
import {workspace} from '../stores/workspace.js';
import {blank, heading} from '../components/common/heading.js';
import {edit, field} from '../components/common/editor.js';

import {state} from '../components/common/status.js';
import {esc, formValues} from '../utils/html.js';
import {number, percent} from '../utils/format.js';
import {go} from '../router/navigation.js';

export async function snapshotsPage({view, user, active}, reports) {
  const snapshots = await workspace.snapshots();
  if (!active()) return;
  const rows = reports ? snapshots.filter(row => ['ready', 'published'].includes(row.status)) : snapshots;
  const detailPath = reports ? 'reports' : 'runs';
  const create = !reports && user.role === 'analyst' ? '<button class="primary" id="capture">新建口径快照</button>' : '';
  const title = reports ? '月报审阅' : '窗口核算';
  const help = reports ? '查看已核算的月报、复核分钟口径并导出。' : '冻结当月开放计划与停用记录，再交由后台核算。';
  view.innerHTML = heading(title, help, create) +
    `${reports ? '' : '<div class="steps"><span>冻结月度输入</span><b>→</b><span>提交后台核算</span><b>→</b><span>交业务复核</span></div>'}
    <section class="sheet"><div class="table-heading"><div><h2>${reports ? '月报清单' : '口径快照'}</h2><p>${rows.length} 个版本</p></div></div>
    ${rows.length ? `<div class="scroll-table"><table><thead><tr><th>版本</th><th>核算月份</th><th>状态</th><th>计划开放</th><th>可用率</th><th></th></tr></thead>
    <tbody>${rows.map(row => `<tr><th scope="row"><strong>${esc(row.label)}</strong><small class="mono">V${row.id} · ${row.checksum.slice(0, 10)}</small></th>
    <td class="mono">${esc(row.month)}</td><td>${state(row.status)}</td><td>${row.totals ? `${number(row.totals.planned_minutes)} 分钟` : '—'}</td>
    <td class="mono">${percent(row.totals?.availability_pct)}</td><td><a class="text-link" href="#${detailPath}/${row.id}">查看版本 <span aria-hidden="true">↗</span></a></td></tr>`).join('')}</tbody></table></div>` :
    blank('暂无可阅版本', reports ? '核算并发布后，观察员可在这里查看和下载月报。' : '先新建口径快照，选择核算月份并填写版本名称。')}
    </section>`;
  const capture = view.querySelector('#capture');
  if (!capture) return;
  capture.onclick = () => edit('新建口径快照',
    field('核算月份', `<input type="month" name="month" value="${DEMO_MONTH}" min="2000-01" max="2099-12" required>`) +
    field('版本名称', '<input name="label" minlength="2" maxlength="60" placeholder="例 十一月巡检复核" required>') +
    '<p class="field-note">保存时冻结当前开放计划与所选月份内相关停用记录。</p>', async form => {
      const row = await workspace.capture(formValues(form));
      return () => go(`runs/${row.id}`);
    });
}
