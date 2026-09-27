(async () => {
  const user = await loadUser();
  if (user) {
    location.href = homeFor(user);
    return;
  }

  const ages = Array.from({ length: 10 }, (_, i) => i + 5);
  $('#app').innerHTML = `
    <div class="card auth-box">
      <h1>Регистрация ученика ✨</h1>
      <p class="muted">Аккаунты преподавателей создаёт администратор.</p>
      <form class="stack" id="reg-form">
        <label>Как тебя зовут? <input name="name" required minlength="2" maxlength="80" autocomplete="given-name"></label>
        <label>Возраст
          <select name="age" required>
            <option value="">Выбери…</option>
            ${ages.map((a) => `<option value="${a}">${a} ${plural(a, 'год', 'года', 'лет')}</option>`).join('')}
          </select>
        </label>
        <div>
          <strong>Выбери аватар</strong>
          <div class="avatars" style="margin-top:8px">
            ${AVATARS.map((a, i) => `<label><input type="radio" name="avatar" value="${a}" ${i === 1 ? 'checked' : ''}><span>${a}</span></label>`).join('')}
          </div>
        </div>
        <label>Email <input name="email" type="email" required autocomplete="email"></label>
        <label>Пароль <input name="password" type="password" required minlength="8" autocomplete="new-password">
          <span class="hint">Минимум 8 символов</span></label>
        <button class="btn" type="submit">Создать аккаунт</button>
      </form>
      <p class="muted">Уже есть аккаунт? <a href="/login.html">Войти</a></p>
    </div>`;

  handleForm($('#reg-form'), async (data) => {
    const me = await api('/api/auth/register', {
      method: 'POST',
      body: { ...data, age: Number(data.age) },
    });
    toast('Добро пожаловать! 🎉', 'success');
    location.href = homeFor(me);
  });
})();
