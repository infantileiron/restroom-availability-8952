import {
  ADJUDICATION_MODES, RULE_SOURCES, RULE_SOURCE_PRIORITY, VERSION_STATES, WINDOW_TYPES,
} from '../constants/business.js';
import {workspace} from '../stores/workspace.js';
import {blank, heading} from '../components/common/heading.js';
import {edit, field} from '../components/common/editor.js';
import {notify} from '../components/common/notifications.js';
import {clockRange} from '../utils/format.js';
import {esc, formValues} from '../utils/html.js';

const TYPE_BADGE = {extension: 'status ready', reduction: 'status water', closed: 'status fault'};

function versionBadge(status) {
  return `<span class="status ${status === 'active' ? 'published' : 'queued'}">${VERSION_STATES[status] || status}</span>`;
}

export async function festivalPage({view, user, active, refresh}) {
  const analyst = user.role === 'analyst';
  const [sites, versions] = await Promise.all([workspace.facilities(), workspace.ruleVersions()]);
  if (!active()) return;
  const siteName = Object.fromEntries(sites.map(site => [site.code, site.name]));
  let selectedId = versions.length ? versions[0].id : null;

  view.innerHTML = heading('节庆临时窗口', '同一公厕同日可同时录入延长、缩短和整日关闭；跨夜按开门日归属，按版本归一化裁决。',
    analyst ? '<button class="primary" id="new-version">新建规则版本</button>' : '') +
    `<div class="section-bar"><div><h2>规则版本</h2><p>${versions.length} 个版本 · 同一时刻仅一个生效</p></div></div>
    <section class="sheet"><div id="version-list"></div></section>
    <div id="version-detail"></div>
    <aside class="note"><strong>记录保护</strong><span>已激活版本不可变更或删除，已冻结快照沿用当时规则；任何丢失的记录都不能恢复，删除仅限草稿并留审计。</span></aside>`;

  const renderList = () => {
    view.querySelector('#version-list').innerHTML = versions.length ?
      `<div class="scroll-table"><table><thead><tr><th>版本</th><th>状态</th><th>裁决方式</th><th>窗口数</th><th>建版人</th><th></th></tr></thead>
      <tbody>${versions.map(v => `<tr data-version="${v.id}" class="${v.id === selectedId ? 'selected-row' : ''}">
        <th scope="row"><strong>${esc(v.label)}</strong><small class="mono">V${v.id}</small></th>
        <td>${versionBadge(v.status)}</td><td>${ADJUDICATION_MODES[v.adjudication_mode] || v.adjudication_mode}</td>
        <td class="mono">${v.window_count}</td><td>${esc(v.created_by)}</td>
        <td><button class="text-link version-open" data-version="${v.id}">查看窗口与裁决 <span aria-hidden="true">↗</span></button></td></tr>`).join('')}</tbody></table></div>`
      : blank('尚无规则版本', analyst ? '新建一个草稿版本，再逐条录入节庆临时窗口。' : '分析员建版后，可在此查看生效窗口与裁决。');
    view.querySelectorAll('.version-open').forEach(button => {
      button.onclick = () => {
        selectedId = Number(button.dataset.version);
        view.querySelectorAll('tr[data-version]').forEach(row =>
          row.classList.toggle('selected-row', Number(row.dataset.version) === selectedId));
        openDetail(selectedId);
      };
    });
  };

  const openDetail = async versionId => {
    const [detail, preview] = await Promise.all([
      workspace.ruleVersion(versionId), workspace.rulePreview(versionId)]);
    if (!active()) return;
    renderDetail(detail, preview);
  };

  const renderDetail = (detail, preview) => {
    const isDraft = detail.status === 'draft';
    const canWrite = analyst && isDraft;
    const conflicts = Object.values(preview.days).flatMap(days =>
      Object.entries(days).flatMap(([date, day]) => day.conflicts.map(c => ({date, ...c}))));
    const adoptedCount = detail.windows.filter(w => {
      const day = preview.days[w.facility_code]?.[w.open_date];
      return day?.records.find(r => r.id === w.id)?.adopted;
    }).length;

    view.querySelector('#version-detail').innerHTML = `<section class="sheet detail-sheet">
      <div class="table-heading"><div><h2>${esc(detail.label)} <small class="mono">V${detail.id}</small></h2>
      <p>${versionBadge(detail.status)} · ${ADJUDICATION_MODES[detail.adjudication_mode]} · 录入 ${detail.windows.length} 条 · 采用 ${adoptedCount} 条</p></div>
      <div class="actions">${canWrite ? `<button class="secondary" id="add-window">录入临时窗口</button>
        <button class="primary" id="activate"${detail.windows.length ? '' : ' disabled'}>激活为生效版本</button>` : ''}</div></div>
      <div class="scroll-table"><table><thead><tr><th>设施 / 开门日</th><th>类型</th><th>来源（优先级）</th><th>窗口（按开门日）</th><th>裁决</th><th>备注</th><th></th></tr></thead>
      <tbody>${detail.windows.length ? detail.windows.map(w => {
        const verdict = preview.days[w.facility_code]?.[w.open_date]?.records.find(r => r.id === w.id);
        return `<tr><th scope="row"><strong>${esc(siteName[w.facility_code] || w.facility_code)}</strong>
          <small class="mono">${esc(w.facility_code)} · ${esc(w.open_date)}</small></th>
          <td><span class="${TYPE_BADGE[w.window_type]}">${WINDOW_TYPES[w.window_type]}</span></td>
          <td>${RULE_SOURCES[w.source]} <small class="mono">P${RULE_SOURCE_PRIORITY[w.source]}</small></td>
          <td class="mono nowrap">${clockRange(w.start_min, w.end_min)}</td>
          <td>${verdict?.adopted ? `<span class="status published">采用 ${verdict.adopted_minutes} 分</span>`
            : `<span class="status failed">覆盖 ${verdict?.overridden_minutes ?? 0} 分</span>`}</td>
          <td>${esc(w.note || '—')}</td>
          <td>${canWrite ? `<button class="text-link del-window" data-window="${w.id}">删除</button>` : ''}</td></tr>`;
      }).join('') : `<tr><td colspan="7">${blank('版本内暂无窗口', canWrite ? '录入延长、缩短或整日关闭记录。' : '')}</td></tr>`}</tbody></table></div>
      ${conflicts.length ? conflictBlock(conflicts) : ''}
    </section>`;

    if (!canWrite) return;
    view.querySelector('#add-window')?.addEventListener('click', () => windowDialog(detail));
    view.querySelector('#activate')?.addEventListener('click', () => activateDialog(detail));
    view.querySelectorAll('.del-window').forEach(button => {
      button.onclick = async () => {
        await workspace.removeTempWindow(detail.id, Number(button.dataset.window));
        notify('草稿记录已删除并留痕');
        refresh();
      };
    });
  };

  const conflictBlock = conflicts => `<div class="conflict-box"><h3>冲突裁决结果（${conflicts.length} 组）</h3>
    <div class="scroll-table"><table><thead><tr><th>开门日</th><th>裁决方式</th><th>采用记录</th><th>被覆盖记录</th><th>说明</th></tr></thead><tbody>
    ${conflicts.map(c => `<tr><td class="mono">${esc(c.date)}</td><td>${ADJUDICATION_MODES[c.mode]}</td>
      <td class="mono">${c.winning_record_ids.join('、')}${c.winning_source ? `（${RULE_SOURCES[c.winning_source]}）` : ''}</td>
      <td class="mono">${(c.overridden_record_ids || []).join('、') || '—'}</td><td>${esc(c.reason)}</td></tr>`).join('')}
    </tbody></table></div></div>`;

  const windowDialog = detail => {
    const siteOptions = sites.map(site => `<option value="${esc(site.code)}">${esc(site.name)}</option>`).join('');
    edit('录入节庆临时窗口',
      `<div class="form-grid">${field('设施', `<select name="facility_code">${siteOptions}</select>`)}
      ${field('开门日（跨夜归此日）', '<input name="open_date" type="date" required>')}</div>
      <div class="form-grid">${field('窗口类型', `<select name="window_type" id="fw-type">${Object.entries(WINDOW_TYPES)
        .map(([code, label]) => `<option value="${code}">${label}</option>`).join('')}</select>`)}
      ${field('来源', `<select name="source">${Object.entries(RULE_SOURCES)
        .map(([code, label]) => `<option value="${code}">${label}（优先级 ${RULE_SOURCE_PRIORITY[code]}）</option>`).join('')}</select>`)}</div>
      <div class="form-grid">${field('开始时间', '<input name="start" id="fw-start" type="time" required value="00:00">')}
      ${field('结束时间', '<input name="end" id="fw-end" type="time" required value="23:59">')}</div>
      <label class="check"><input type="checkbox" name="overnight" id="fw-overnight">次日结束（跨夜，仍归属开门日）</label>
      ${field('备注', '<textarea name="note" maxlength="240" rows="2" placeholder="选填，来源文号或现场说明"></textarea>')}
      <p class="field-note" id="fw-note">整日关闭固定为开门日 00:00–24:00；相同窗口重复录入会被归一化去重。</p>`,
      async form => {
        const values = formValues(form);
        if (values.window_type === 'closed') {
          values.start = '00:00'; values.end = '00:00'; values.overnight = true;
        }
        const result = await workspace.addTempWindow(detail.id, {
          facility_code: values.facility_code, window_type: values.window_type, source: values.source,
          open_date: values.open_date, start: values.start,
          end: values.window_type === 'closed' ? '00:00' : values.end,
          overnight: Boolean(values.overnight) || values.window_type === 'closed',
          note: values.note || '',
        });
        return () => { notify(result.duplicated ? '与已有窗口完全相同，已归一化去重' : '临时窗口已录入草稿'); refresh(); };
      });
    const typeSelect = document.querySelector('#fw-type');
    const startInput = document.querySelector('#fw-start');
    const endInput = document.querySelector('#fw-end');
    const overnightBox = document.querySelector('#fw-overnight');
    typeSelect.onchange = () => {
      const closed = typeSelect.value === 'closed';
      for (const control of [startInput, endInput, overnightBox]) control.disabled = closed;
      if (closed) {
        startInput.value = '00:00'; endInput.value = '00:00'; overnightBox.checked = true;
      }
    };
  };

  const activateDialog = detail => edit('激活规则版本',
    `<p>将按「<strong>${ADJUDICATION_MODES[detail.adjudication_mode]}</strong>」归一化裁决全部 ${detail.windows.length} 条窗口。</p>
     <p class="field-note">激活在单事务内完成：若中途失败，当前旧生效版本保持不变；重复激活不会重复覆盖。激活后此版本不可再改。</p>`,
    async () => {
      const result = await workspace.activateRuleVersion(detail.id);
      return () => { notify(result.idempotent ? '该版本已是生效版本，未重复处理' : '规则版本已激活，后续快照将采用此版本'); refresh(); };
    });

  const newVersion = view.querySelector('#new-version');
  if (newVersion) newVersion.onclick = () => edit('新建规则版本',
    field('版本名称', '<input name="label" minlength="2" maxlength="80" placeholder="例 春节保障窗口·第一版" required>') +
    field('冲突裁决方式', `<select name="adjudication_mode">${Object.entries(ADJUDICATION_MODES)
      .map(([code, label]) => `<option value="${code}">${label}</option>`).join('')}</select>`) +
    '<p class="field-note">整体裁决：同冲突组最高优先级来源整组胜出；分钟拆分：每分钟取最高优先级再合并。</p>',
    async form => {
      const row = await workspace.createRuleVersion(formValues(form));
      return () => { notify('草稿版本已创建'); refresh(); };
    });

  renderList();
  if (selectedId) openDetail(selectedId);
}
