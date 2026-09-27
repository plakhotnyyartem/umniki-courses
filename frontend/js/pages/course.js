(async () => {
  const user = await loadUser();
  const app = $('#app');
  const id = Number(params.get('id'));

  let course;
  try {
    course = await api(`/api/courses/${id}`);
  } catch (err) {
    app.innerHTML = `<div class="empty-state"><div class="icon">🤷</div><h2>${esc(err.message)}</h2><a class="btn" href="/catalog.html">К каталогу</a></div>`;
    return;
  }
  document.title = `${course.title} — Умники`;

  const done = course.lessons.filter((l) => l.done).length;
  const canOpen = course.enrolled || course.can_edit;

  let action = '';
  if (course.can_edit) {
    action = `<a class="btn secondary" href="/teacher-course.html?id=${course.id}">✏️ Редактировать</a>`;
  } else if (!user) {
    action = `<a class="btn" href="/login.html?next=${encodeURIComponent(location.pathname + location.search)}">Войти, чтобы записаться</a>`;
  } else if (user.role === 'student' && !course.enrolled) {
    action = `<button class="btn" id="enroll">🚀 Записаться на курс</button>`;
  } else if (course.enrolled) {
    const next = course.lessons.find((l) => !l.done);
    action = next
      ? `<a class="btn" href="/lesson.html?id=${next.id}">${done ? 'Продолжить' : 'Начать'} ▶</a>`
      : `<span class="badge ok">🏆 Курс пройден!</span>`;
  }

  app.innerHTML = `
    ${course.is_published ? '' : '<p class="badge off">Черновик — ученики этот курс не видят</p>'}
    <section class="course-head ${esc(course.subject)}">
      <div class="cover">${esc(course.cover)}</div>
      <div>
        <div class="meta">${subjectBadge(course.subject)}<span class="badge">${course.min_age}–${course.max_age} лет</span><span class="badge">👥 ${course.students_count}</span></div>
        <h1>${esc(course.title)}</h1>
        <p class="muted">${esc(course.description)}</p>
        <p>Преподаватель: <strong>${esc(course.teacher.avatar)} ${esc(course.teacher.name)}</strong></p>
        <div class="meta">${action}</div>
      </div>
    </section>

    ${course.enrolled ? `<div class="card" style="margin-bottom:20px"><strong>Прогресс: ${done} из ${course.lessons.length}</strong>${progressHtml(done, course.lessons.length)}</div>` : ''}

    <h2>Уроки</h2>
    ${
      course.lessons.length
        ? `<ol class="lesson-list">
            ${course.lessons
              .map((l, i) => {
                const inner = `
                  <span class="num">${l.done ? '✓' : i + 1}</span>
                  <span class="title">${esc(l.title)}</span>
                  ${l.questions_count ? `<span class="muted">📝 ${l.questions_count}</span>` : ''}
                  ${l.stars !== null ? starsHtml(l.stars) : canOpen ? '' : '🔒'}`;
                return `<li class="${l.done ? 'done' : ''}">${
                  canOpen ? `<a href="/lesson.html?id=${l.id}">${inner}</a>` : `<div>${inner}</div>`
                }</li>`;
              })
              .join('')}
          </ol>`
        : '<p class="muted">Уроков пока нет.</p>'
    }`;

  $('#enroll')?.addEventListener('click', async (e) => {
    e.target.disabled = true;
    try {
      await api(`/api/courses/${course.id}/enroll`, { method: 'POST' });
      toast('Ура! Вы записаны на курс 🎉', 'success');
      setTimeout(() => location.reload(), 600);
    } catch (err) {
      toast(err.message, 'error');
      e.target.disabled = false;
    }
  });
})();
