(async () => {
  const user = await loadUser();
  if (user) {
    location.href = homeFor(user);
    return;
  }

  $('#app').innerHTML = `
    <div class="card auth-box">
      <h1>Вход 👋</h1>
      <form class="stack" id="login-form">
        <label>Email <input name="email" type="email" required autocomplete="email"></label>
        <label>Пароль <input name="password" type="password" required autocomplete="current-password"></label>
        <button class="btn" type="submit">Войти</button>
      </form>
      <p class="muted">Нет аккаунта? <a href="/register.html">Зарегистрироваться</a></p>
    </div>`;

  handleForm($('#login-form'), async (data) => {
    const me = await api('/api/auth/login', { method: 'POST', body: data });
    // Возвращаем туда, откуда пришли, но только на свой сайт
    const next = params.get('next');
    location.href = next && next.startsWith('/') && !next.startsWith('//') ? next : homeFor(me);
  });
})();
