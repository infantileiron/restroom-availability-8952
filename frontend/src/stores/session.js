let user = null;
const key = 'fangjie-session';
export const session = {
  get user() { return user; },
  get token() { return sessionStorage.getItem(key); },
  resume(identity) { user = identity; },
  start({token, user: identity}) {
    sessionStorage.setItem(key, token);
    user = identity;
  },
  clear() {
    sessionStorage.removeItem(key);
    user = null;
  },
};
