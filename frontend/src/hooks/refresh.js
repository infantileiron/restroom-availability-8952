export function pollWhileActive(callback, isActive) {
  const poll = async () => {
    if (!isActive()) return;
    const again = await callback();
    if (again && isActive()) setTimeout(poll, 650);
  };
  setTimeout(poll, 650);
}

export function bindAction(button, action, failed) {
  if (!button) return;
  button.onclick = async () => {
    button.disabled = true;
    try {
      await action();
    } catch (error) {
      failed(error.message);
    } finally {
      button.disabled = false;
    }
  };
}
