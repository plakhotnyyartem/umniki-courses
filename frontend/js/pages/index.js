(async () => {
  const user = await loadUser();
  const courses = await api('/api/courses').catch(() => []);
  const app = $('#app');

  const cta = user
    ? `<a class="btn" href="${homeFor(user)}">Перейти в кабинет</a>`
    : `<a class="btn" href="/register.html">Начать учиться</a><a class="btn secondary" href="/catalog.html">Смотреть курсы</a>`;

  app.innerHTML = `
    <section class="hero">
      <div>
        <h1>Учиться — это весело! 🎉</h1>
        <p>Короткие уроки по английскому и математике для ребят от 5 до 14 лет. Проходи мини-тесты, собирай звёзды и получай советы от преподавателя.</p>
        <div class="actions">${cta}</div>
      </div>
      <div class="art" aria-hidden="true">🦉<br>📚✏️</div>
    </section>

    <section class="subjects">
      <a class="card subject-tile english" href="/catalog.html?subject=english">
        <div class="icon">🇬🇧</div>
        <div><h3>Английский</h3><div class="muted">Слова, грамматика и первые диалоги</div></div>
      </a>
      <a class="card subject-tile math" href="/catalog.html?subject=math">
        <div class="icon">🔢</div>
        <div><h3>Математика</h3><div class="muted">Счёт, таблица умножения, дроби и уравнения</div></div>
      </a>
    </section>

    <h2>Популярные курсы</h2>
    <div class="grid">${courses.slice(0, 6).map((c) => courseCardHtml(c)).join('') || '<p class="muted">Курсов пока нет.</p>'}</div>

    <section class="features">
      <div class="card"><div class="icon">⏱️</div><h3>Уроки по 10 минут</h3><p class="muted">Легко найти время даже после школы</p></div>
      <div class="card"><div class="icon">⭐</div><h3>Звёзды за тесты</h3><p class="muted">До трёх звёзд за каждый урок</p></div>
      <div class="card"><div class="icon">🧑‍🏫</div><h3>Живые преподаватели</h3><p class="muted">Следят за прогрессом и дают советы</p></div>
    </section>`;
})();
