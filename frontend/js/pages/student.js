(async () => {
  const user = await guard('student');
  const data = await api('/api/me/dashboard');
  const app = $('#app');

  const courseCards = data.courses
    .map((c) => {
      const extra = `
        <div><div class="meta" style="justify-content:space-between"><span>${c.done} из ${c.lessons_count}</span><span class="stars">★ ${c.stars}</span></div>
        ${progressHtml(c.done, c.lessons_count)}</div>`;
      return courseCardHtml(c, extra);
    })
    .join('');

  app.innerHTML = `
    <div class="page-head">
      <h1>${esc(user.avatar)} Привет, ${esc(user.name)}!</h1>
      <a class="btn secondary" href="/catalog.html">📚 Найти новый курс</a>
    </div>

    <div class="stats">
      <div class="card stat"><div class="value stars">★ ${data.total_stars}</div><div class="label">звёзд собрано</div></div>
      <div class="card stat"><div class="value">${data.lessons_done}</div><div class="label">уроков пройдено</div></div>
      <div class="card stat"><div class="value">${data.courses.length}</div><div class="label">${plural(data.courses.length, 'курс', 'курса', 'курсов')}</div></div>
    </div>

    ${nextLessonHtml()}

    <h2>Мои курсы</h2>
    ${
      data.courses.length
        ? `<div class="grid">${courseCards}</div>`
        : `<div class="card empty-state"><div class="icon">🎒</div><p>Ты ещё не записан(а) ни на один курс.</p><a class="btn" href="/catalog.html">Выбрать курс</a></div>`
    }

    <h2 style="margin-top:32px">💬 Сообщения от преподавателей</h2>
    ${
      data.feedback.length
        ? data.feedback
            .map(
              (f) => `
              <div class="feedback-item">
                <div class="meta"><strong>${esc(f.teacher.avatar)} ${esc(f.teacher.name)}</strong><span class="muted">· ${esc(f.course.title)} · ${formatDate(f.created_at)}</span></div>
                <div>${esc(f.text)}</div>
              </div>`
            )
            .join('')
        : '<p class="muted">Пока сообщений нет.</p>'
    }`;

  function nextLessonHtml() {
    const c = data.courses.find((x) => x.next_lesson_id);
    if (!c) return '';
    return `
      <div class="card" style="margin-bottom:24px;display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div style="font-size:44px">${esc(c.cover)}</div>
        <div style="flex:1"><div class="muted">Продолжить обучение</div><h3 style="margin:0">${esc(c.title)}</h3></div>
        <a class="btn" href="/lesson.html?id=${c.next_lesson_id}">Следующий урок ▶</a>
      </div>`;
  }
})();
