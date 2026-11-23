import {api} from '../api/client.js';
import {brand} from '../components/shell.js';
import {session} from '../stores/session.js';
import {formValues} from '../utils/html.js';

export function login(root, enter) {
  root.innerHTML = `<main class="login"><section class="login-visual">${brand()}
    <div class="dial" aria-hidden="true"><span class="dial-north">00</span><span class="dial-east">06</span>
    <span class="dial-south">12</span><span class="dial-west">18</span><div class="dial-face"><i></i><b></b></div></div>
    <div class="dial-caption"><strong>市政巡检时钟</strong><span>每日开放窗口 · 停用核对 · 月度复核</span></div></section>
    <section class="login-panel"><form id="login-form"><p class="eyebrow">坊洁市政环卫 · 巡维值班室</p>
    <h1>登录工作台</h1><p class="login-intro">登录后查看辖区公厕开放日历与月度核算。</p>
    <label class="field"><span>账号</span><input name="username" required autocomplete="username" placeholder="输入巡维账号"></label>
    <label class="field"><span>密码</span><input name="password" type="password" required autocomplete="current-password" placeholder="输入密码"></label>
    <p class="form-error" role="alert" hidden></p><button class="primary" type="submit">进入工作台 <span aria-hidden="true">↗</span></button>
    <div class="demo-access"><strong>演示账号</strong><span>analyst · reviewer · viewer</span><span>密码 Fangjie2026!</span></div>
    </form></section></main>`;
  const form = document.querySelector('#login-form');
  form.onsubmit = async event => {
    event.preventDefault();
    const button = form.querySelector('button');
    const error = form.querySelector('.form-error');
    button.disabled = true;
    error.hidden = true;
    try {
      session.start(await api('/login', formValues(form)));
      enter();
    } catch (problem) {
      error.textContent = problem.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  };
}
