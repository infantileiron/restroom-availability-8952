let timer;
export function notify(text, error = false) {
  const node = document.querySelector('#announcement');
  clearTimeout(timer);
  node.textContent = text;
  node.classList.toggle('is-error', error);
  node.hidden = false;
  timer = setTimeout(() => { node.hidden = true; }, error ? 7000 : 3500);
}
