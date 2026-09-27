(async () => {
  const user = await guard('teacher', 'admin');
  const app = $('#app');
  const COVERS = ['📘', '📗', '🐾', '🕐', '✖️', '🍕', '⚖️', '📐', '🔤', '🌍', '🧩', '🎲'];

  app.innerHTML = `
    <div class="page-head">
      <h1>🧑‍🏫 Мои курсы</h1>
      <button class="btn" id="new-btn">＋ Новый курс</button>
    </div>

    <form class="card stack hidden" id="new-form" style="margin-bottom:24px">
      <h2>Новый курс</h2>
      <label>Название <input name="title" required minlength="3" maxlength="120"></label>
      <label>Описание <textarea name="description" maxlength="3000" placeholder="Чему научится ребёнок?"></textarea></label>
      <div class="row">
        <label>Предмет
          <select name="subject" required><option value="english">🇬🇧 Английский</option><option value="math">🔢 Математика</option></select>
        </label>
        <label>Возраст от <input name="min_age" type="number" min="5" max="14" value="7" required></label>
        <label>Возраст до <input name="max_age" type="number" min="5" max="14" value="10" required></label>
      </div>
      <div><strong>Обложка</strong>
        <div class="avatars" style="margin-top:8px">
          ${COVERS.map((c, i) => `<label><input type="radio" name="cover" value="${c}" ${i === 0 ? 'checked' : ''}><span>${c}</span></label>`).join('')}
        </div>
      </div>
      <div class="meta"><button class="btn" type="submit">Создать и добавить уроки</button><button class="btn secondary" type="button" id="cancel-btn">Отмена</button></div>
    </form>

    <div id="list"></div>`;

  const form = $('#new-form');
  $('#new-btn').addEventListener('click', () => form.classList.remove('hidden'));
  $('#cancel-btn').addEventListener('click', () => form.classList.add('hidden'));

  handleForm(form, async (data) => {
    const course = await api('/api/teacher/courses', {
      method: 'POST',
      body: { ...data, min_age: Number(data.min_age), max_age: Number(data.max_age), is_published: false },
    });
    location.href = `/teacher-course.html?id=${course.id}`;
  });

  const courses = await api('/api/teacher/courses');
  $('#list').innerHTML = courses.length
    ? `<div class="grid">${courses
        .map((c) =>
          courseCardHtml(
            c,
            `<div class="meta">${c.is_published ? '<span class="badge ok">Опубликован</span>' : '<span class="badge off">Черновик</span>'}
               <span class="badge">👥 ${c.students_count}</span></div>`,
            `/teacher-course.html?id=${c.id}`
          )
        )
        .join('')}</div>`
    : `<div class="card empty-state"><div class="icon">📝</div><p>У вас пока нет курсов. Создайте первый!</p></div>`;

  if (user.role === 'admin') {
    $('#list').insertAdjacentHTML('beforeend', '<p class="muted" style="margin-top:16px">Курсы других преподавателей — в <a href="/admin.html#courses">админке</a>.</p>');
  }
})();
