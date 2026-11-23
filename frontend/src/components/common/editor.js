import {esc} from '../../utils/html.js';

export function edit(title, content, submit) {
  const dialog = document.querySelector('#editor');
  dialog.innerHTML = `<form class="editor-form"><div class="editor-head"><h2 id="editor-title">${esc(title)}</h2>
    <button class="icon" aria-label="关闭" type="button">×</button></div>${content}
    <p class="form-error" role="alert" hidden></p><div class="actions form-actions">
    <button type="button" class="secondary cancel">取消</button><button class="primary" type="submit">保存</button></div></form>`;
  const form = dialog.querySelector('form');
  for (const button of dialog.querySelectorAll('.cancel, .icon')) button.onclick = () => dialog.close();
  form.onsubmit = async event => {
    event.preventDefault();
    const button = form.querySelector('[type=submit]');
    const error = form.querySelector('.form-error');
    error.hidden = true;
    button.disabled = true;
    try {
      const after = await submit(form);
      dialog.close();
      after?.();
    } catch (problem) {
      error.textContent = problem.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  };
  dialog.showModal();
}

let nextField = 0;
export function field(label, input) {
  const id = `editor-field-${++nextField}`;
  const control = input.replace(/^<([a-z]+)/, `<$1 id="${id}"`);
  return `<div class="field"><label for="${id}">${esc(label)}</label>${control}</div>`;
}
