(async () => {
  await guard('teacher', 'admin');
  const app = $('#app');
  const id = Number(params.get('id'));
  let course;
  let tab = location.hash.slice(1) || 'lessons';

  async function load() {
    try {
      course = await api(`/api/teacher/courses/${id}`);
    } catch (err) {
      app.innerHTML = `<div class="empty-state"><div class="icon">🤷</div><h2>${esc(err.message)}</h2><a class="btn" href="/teacher.html">Назад</a></div>`;
      return false;
    }
    document.title = `${course.title} — редактор`;
    return true;
  }

  function render() {
    app.innerHTML = `
      <p><a href="/teacher.html">← Мои курсы</a></p>
      <div class="page-head">
        <h1>${esc(course.cover)} ${esc(course.title)}</h1>
        <div class="meta">
          ${course.is_published ? '<span class="badge ok">Опубликован</span>' : '<span class="badge off">Черновик</span>'}
          <button class="btn small ${course.is_published ? 'secondary' : 'success'}" id="toggle-pub">${course.is_published ? 'Снять с публикации' : '🚀 Опубликовать'}</button>
          <a class="btn small secondary" href="/course.html?id=${course.id}">👁 Как видит ученик</a>
        </div>
      </div>
      <div class="tabs" role="tablist">
        ${[['lessons', `📖 Уроки (${course.lessons.length})`], ['students', '👥 Ученики'], ['settings', '⚙️ Настройки']]
          .map(([k, label]) => `<button role="tab" data-tab="${k}" class="${tab === k ? 'active' : ''}">${label}</button>`)
          .join('')}
      </div>
      <div id="tab-body"></div>`;

    app.querySelector('.tabs').addEventListener('click', (e) => {
      const b = e.target.closest('[data-tab]');
      if (!b) return;
      tab = b.dataset.tab;
      history.replaceState(null, '', `#${tab}`);
      render();
    });
    $('#toggle-pub').addEventListener('click', async () => {
      if (!course.is_published && !course.lessons.length) return toast('Добавьте хотя бы один урок', 'error');
      await saveCourse({ ...courseFields(), is_published: !course.is_published });
    });

    ({ lessons: renderLessons, students: renderStudents, settings: renderSettings })[tab]();
  }

  const courseFields = () => ({
    title: course.title, description: course.description, subject: course.subject,
    min_age: course.min_age, max_age: course.max_age, cover: course.cover, is_published: course.is_published,
  });

  async function saveCourse(body) {
    try {
      await api(`/api/teacher/courses/${id}`, { method: 'PUT', body });
      await load();
      render();
      toast('Сохранено', 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  // ---------- Уроки ----------
  function renderLessons() {
    const body = $('#tab-body');
    body.innerHTML = `
      <div id="lesson-list">${course.lessons.map((l, i) => lessonEditorHtml(l, i)).join('')}</div>
      <form class="card stack" id="add-lesson">
        <h3>＋ Новый урок</h3>
        <label>Название <input name="title" required minlength="2" maxlength="120"></label>
        <button class="btn" type="submit">Добавить урок</button>
      </form>`;

    handleForm($('#add-lesson'), async (data) => {
      const lesson = await api(`/api/teacher/courses/${id}/lessons`, { method: 'POST', body: { title: data.title } });
      await load();
      render();
      document.querySelector(`details[data-lesson="${lesson.id}"]`)?.setAttribute('open', '');
    });

    body.querySelectorAll('form.lesson-form').forEach((form) =>
      handleForm(form, async (data) => {
        await api(`/api/teacher/lessons/${form.dataset.id}`, {
          method: 'PUT',
          body: { ...data, video_url: data.video_url || null },
        });
        toast('Урок сохранён', 'success');
        await reloadKeepingOpen();
      })
    );

    body.querySelectorAll('form.question-form').forEach(bindQuestionForm);

    // Перетаскивание: сразу меняем порядок в памяти и нумерацию, а на сервер отправляем с задержкой
    sortable($('#lesson-list'), {
      onChange: (ids) => {
        course.lessons.sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
        $('#lesson-list').querySelectorAll('.lesson-num').forEach((el, i) => (el.textContent = i + 1));
        saveOrder('lessons', `/api/teacher/courses/${id}/lessons/order`, ids);
      },
    });
    body.querySelectorAll('.question-list').forEach((listEl) =>
      sortable(listEl, {
        onChange: (ids) => {
          const lesson = course.lessons.find((l) => l.id === Number(listEl.dataset.lesson));
          lesson.questions.sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
          saveOrder(`q${lesson.id}`, `/api/teacher/lessons/${lesson.id}/questions/order`, ids);
        },
      })
    );

    body.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const { action, id: targetId } = btn.dataset;
      try {
        if (action === 'delete-lesson' && confirm('Удалить урок вместе с тестом и результатами учеников?')) {
          await api(`/api/teacher/lessons/${targetId}`, { method: 'DELETE' });
          await reloadKeepingOpen();
        }
        if (action === 'delete-question' && confirm('Удалить вопрос?')) {
          await api(`/api/teacher/questions/${targetId}`, { method: 'DELETE' });
          await reloadKeepingOpen();
        }
        if (action === 'edit-question') {
          // Подменяем карточку вопроса на ту же форму, что и для нового вопроса, но заполненную
          const item = btn.closest('.question-item');
          const q = findQuestion(Number(targetId));
          item.insertAdjacentHTML('afterend', questionFormHtml(q.lesson_id, q));
          const form = item.nextElementSibling;
          item.remove();
          bindQuestionForm(form);
          form.text.focus();
        }
        if (action === 'cancel-edit') await reloadKeepingOpen();
      } catch (err) {
        toast(err.message, 'error');
      }
    });
  }

  // Отдельный таймер на каждый список: несколько быстрых перемещений подряд = один запрос
  const saveTimers = {};
  function saveOrder(key, url, ids) {
    clearTimeout(saveTimers[key]);
    saveTimers[key] = setTimeout(async () => {
      try {
        await api(url, { method: 'PUT', body: { ids } });
        toast('Порядок сохранён', 'success');
      } catch (err) {
        toast(err.message, 'error');
        await reloadKeepingOpen(); // вернуть порядок, который реально лежит на сервере
      }
    }, 400);
  }

  function findQuestion(qid) {
    for (const l of course.lessons) {
      const q = l.questions.find((x) => x.id === qid);
      if (q) return { ...q, lesson_id: l.id };
    }
    throw new Error('Вопрос не найден — обновите страницу');
  }

  function bindQuestionForm(form) {
    const qid = form.dataset.question;
    handleForm(form, async (data) => {
      if (qid) {
        await api(`/api/teacher/questions/${qid}`, { method: 'PUT', body: questionBody(data) });
        toast('Вопрос сохранён', 'success');
      } else {
        await api(`/api/teacher/lessons/${form.dataset.lesson}/questions`, { method: 'POST', body: questionBody(data) });
      }
      await reloadKeepingOpen();
    });

    // Переключатель типа вопроса. Поля неактивного типа лежат в <fieldset disabled>:
    // браузер не проверяет их required и не кладёт в FormData.
    form.addEventListener('change', (e) => {
      if (e.target.name !== 'kind') return;
      form.querySelectorAll('fieldset[data-kind]').forEach((fs) => {
        const active = fs.dataset.kind === e.target.value;
        fs.disabled = !active;
        fs.hidden = !active;
      });
    });
  }

  function questionFormHtml(lessonId, q = null) {
    const kind = q?.kind || 'choice';
    const isText = kind === 'text';
    const options = q?.options || [];
    const correct = q?.correct_index ?? 0;
    const slots = Math.max(4, options.length); // сервер допускает до 6 вариантов
    return `
      <form class="stack question-form card ${q ? 'editing' : ''}" data-lesson="${lessonId}" ${q ? `data-question="${q.id}" data-sort-id="${q.id}"` : ''}
            style="box-shadow:none;margin:12px 0">
        <strong>${q ? '✏️ Редактирование вопроса' : 'Новый вопрос'}</strong>
        <div class="chips" role="radiogroup" aria-label="Тип вопроса">
          <label class="chip-radio"><input type="radio" name="kind" value="choice" ${isText ? '' : 'checked'}><span>🔘 Выбор варианта</span></label>
          <label class="chip-radio"><input type="radio" name="kind" value="text" ${isText ? 'checked' : ''}><span>✍️ Ввод ответа</span></label>
        </div>
        <label>Вопрос <input name="text" required maxlength="500" placeholder="Например: 5 × 7 = ?" value="${esc(q?.text || '')}"></label>
        <fieldset data-kind="choice" class="stack plain-fieldset" ${isText ? 'disabled hidden' : ''}>
          <div class="row">
            ${Array.from({ length: slots }, (_, n) => `
              <label class="check" style="align-items:center">
                <input type="radio" name="correct" value="${n}" ${n === correct ? 'checked' : ''} aria-label="Правильный ответ">
                <input name="o${n}" placeholder="Вариант ${n + 1}${n < 2 ? '' : ' (необяз.)'}" ${n < 2 ? 'required' : ''} maxlength="200" value="${esc(options[n] || '')}">
              </label>`).join('')}
          </div>
          <span class="hint">Кружком отметьте правильный вариант.</span>
        </fieldset>
        <fieldset data-kind="text" class="stack plain-fieldset" ${isText ? '' : 'disabled hidden'}>
          <label>Правильные ответы <input name="accepted" required maxlength="500" placeholder="Например: 35 или four; 4" value="${esc((q?.accepted || []).join('; '))}">
            <span class="hint">Несколько вариантов перечислите через «;». Регистр, лишние пробелы, ё/е и точка в конце не важны.</span></label>
          <label class="check"><input type="checkbox" name="match_numeric" ${q && !q.match_numeric ? '' : 'checked'}>
            <span>Сравнивать числа по значению: 0,5 = 0.5 = 1/2<br><span class="hint">Снимите галочку, если важна именно форма записи (например, «сократи дробь»).</span></span></label>
        </fieldset>
        <div class="meta">
          ${q
            ? `<button class="btn small" type="submit">💾 Сохранить</button>
               <button class="btn small secondary" type="button" data-action="cancel-edit">Отмена</button>
               <span class="hint">Уже полученные учениками звёзды не пересчитываются.</span>`
            : '<button class="btn small" type="submit">＋ Добавить вопрос</button>'}
        </div>
      </form>`;
  }

  function questionBody(data) {
    if (data.kind === 'text') {
      const accepted = data.accepted.split(';').map((a) => a.trim()).filter(Boolean);
      return { kind: 'text', text: data.text, accepted, match_numeric: data.match_numeric === 'on' };
    }
    // Пустые варианты выкидываем, но помним исходные номера, чтобы не потерять правильный
    const filled = Object.keys(data)
      .filter((k) => /^o\d+$/.test(k))
      .map((k) => ({ n: Number(k.slice(1)), text: data[k].trim() }))
      .filter((o) => o.text);
    const correctIndex = filled.findIndex((o) => o.n === Number(data.correct));
    if (correctIndex === -1) throw new Error('Отмеченный правильный вариант пустой');
    return { kind: 'choice', text: data.text, options: filled.map((o) => o.text), correct_index: correctIndex };
  }

  function questionAnswersHtml(q) {
    if (q.kind === 'text') {
      return `<div class="muted" style="font-size:15px">✍️ Ввод ответа${q.match_numeric ? '' : ', числа строго'}:
        ${q.accepted.map((a) => `<span class="badge ok">${esc(a)}</span>`).join(' ')}</div>`;
    }
    return `<ol>${q.options
      .map((o, oi) => `<li class="${oi === q.correct_index ? 'right' : ''}">${esc(o)}${oi === q.correct_index ? ' ✓' : ''}</li>`)
      .join('')}</ol>`;
  }

  async function reloadKeepingOpen() {
    const open = [...document.querySelectorAll('details[open]')].map((d) => d.dataset.lesson);
    const y = scrollY;
    await load();
    render();
    open.forEach((lid) => document.querySelector(`details[data-lesson="${lid}"]`)?.setAttribute('open', ''));
    scrollTo(0, y);
  }

  function dragHandleHtml(what) {
    return `<button type="button" class="drag-handle" title="Перетащите, чтобы поменять порядок"
      aria-label="Переместить ${esc(what)}: стрелки вверх и вниз">⠿</button>`;
  }

  function lessonEditorHtml(l, i) {
    return `
      <details class="card editor-lesson" data-lesson="${l.id}" data-sort-id="${l.id}">
        <summary>${dragHandleHtml(`урок «${l.title}»`)}<span class="badge lesson-num">${i + 1}</span> ${esc(l.title)} <span class="muted" style="margin-left:auto;font-size:14px">📝 ${l.questions.length}</span></summary>
        <form class="stack lesson-form" data-id="${l.id}">
          <label>Название <input name="title" value="${esc(l.title)}" required minlength="2" maxlength="120"></label>
          <label>Текст урока
            <textarea name="content" rows="10" maxlength="20000">${esc(l.content)}</textarea>
            <span class="hint">Разметка: <code># Заголовок</code>, <code>- пункт списка</code>, <code>**жирный**</code>, <code>*курсив*</code></span>
          </label>
          <label>Видео с YouTube (необязательно) <input name="video_url" type="url" value="${esc(l.video_url || '')}" placeholder="https://www.youtube.com/watch?v=..."></label>
          <div class="meta">
            <button class="btn" type="submit">💾 Сохранить урок</button>
            <a class="btn secondary" href="/lesson.html?id=${l.id}">👁 Просмотр</a>
            <button class="btn danger small" type="button" data-action="delete-lesson" data-id="${l.id}" style="margin-left:auto">Удалить урок</button>
          </div>
        </form>

        <h3 style="margin-top:24px">📝 Тест (${l.questions.length})</h3>
        <div class="question-list" data-lesson="${l.id}">
        ${l.questions
          .map(
            (q) => `
            <div class="question-item" data-sort-id="${q.id}">
              ${dragHandleHtml('вопрос')}
              <div style="flex:1"><strong>${renderInline(q.text)}</strong>${questionAnswersHtml(q)}</div>
              <div class="meta" style="flex-wrap:nowrap;align-items:flex-start">
                <button class="btn ghost small" type="button" data-action="edit-question" data-id="${q.id}" aria-label="Редактировать вопрос">✏️</button>
                <button class="btn ghost small" type="button" data-action="delete-question" data-id="${q.id}" aria-label="Удалить вопрос">🗑</button>
              </div>
            </div>`
          )
          .join('')}
        </div>
        ${questionFormHtml(l.id)}
      </details>`;
  }

  // ---------- Ученики ----------
  async function renderStudents() {
    const body = $('#tab-body');
    body.innerHTML = '<p class="muted">Загрузка…</p>';
    const data = await api(`/api/teacher/courses/${id}/students`);
    if (!data.students.length) {
      body.innerHTML = `<div class="card empty-state"><div class="icon">👥</div><p>На курс пока никто не записался${course.is_published ? '' : ' — сначала опубликуйте его'}.</p></div>`;
      return;
    }
    body.innerHTML = `
      <div class="card table-wrap">
        <table>
          <thead><tr>
            <th>Ученик</th><th>Прогресс</th>
            ${data.lessons.map((l, i) => `<th title="${esc(l.title)}">У${i + 1}</th>`).join('')}
            <th></th>
          </tr></thead>
          <tbody>
            ${data.students
              .map(
                (s) => `
                <tr>
                  <td><strong>${esc(s.avatar)} ${esc(s.name)}</strong><div class="muted" style="font-size:14px">${s.age ?? '—'} лет</div></td>
                  <td style="min-width:120px">${s.done}/${data.lessons.length}${progressHtml(s.done, data.lessons.length)}</td>
                  ${data.lessons
                    .map((l) => {
                      const r = s.results[l.id];
                      return `<td>${r ? `<span title="${r.score}/${r.total}, попыток: ${r.attempts}">${starsHtml(r.stars)}</span>` : '<span class="muted">—</span>'}</td>`;
                    })
                    .join('')}
                  <td class="actions"><button class="btn small secondary" data-feedback="${s.id}" data-name="${esc(s.name)}">💬 Написать</button></td>
                </tr>`
              )
              .join('')}
          </tbody>
        </table>
      </div>
      <form class="card stack hidden" id="fb-form" style="margin-top:20px">
        <h3 id="fb-title"></h3>
        <input type="hidden" name="student_id">
        <label>Сообщение <textarea name="text" required maxlength="2000" placeholder="Молодец! Обрати внимание на…"></textarea></label>
        <div class="meta"><button class="btn" type="submit">Отправить</button><button class="btn secondary" type="button" id="fb-cancel">Отмена</button></div>
      </form>`;

    const form = $('#fb-form');
    body.addEventListener('click', (e) => {
      const b = e.target.closest('[data-feedback]');
      if (!b) return;
      form.student_id.value = b.dataset.feedback;
      $('#fb-title').textContent = `Сообщение для ${b.dataset.name}`;
      form.classList.remove('hidden');
      form.text.focus();
    });
    $('#fb-cancel').addEventListener('click', () => form.classList.add('hidden'));
    handleForm(form, async (d) => {
      await api(`/api/teacher/courses/${id}/feedback`, { method: 'POST', body: { student_id: Number(d.student_id), text: d.text } });
      toast('Сообщение отправлено', 'success');
      form.reset();
      form.classList.add('hidden');
    });
  }

  // ---------- Настройки ----------
  function renderSettings() {
    $('#tab-body').innerHTML = `
      <form class="card stack" id="settings">
        <label>Название <input name="title" value="${esc(course.title)}" required minlength="3" maxlength="120"></label>
        <label>Описание <textarea name="description" maxlength="3000">${esc(course.description)}</textarea></label>
        <div class="row">
          <label>Предмет
            <select name="subject">
              <option value="english" ${course.subject === 'english' ? 'selected' : ''}>🇬🇧 Английский</option>
              <option value="math" ${course.subject === 'math' ? 'selected' : ''}>🔢 Математика</option>
            </select>
          </label>
          <label>Возраст от <input name="min_age" type="number" min="5" max="14" value="${course.min_age}" required></label>
          <label>Возраст до <input name="max_age" type="number" min="5" max="14" value="${course.max_age}" required></label>
          <label>Обложка (эмодзи) <input name="cover" value="${esc(course.cover)}" maxlength="8" required></label>
        </div>
        <div><button class="btn" type="submit">💾 Сохранить</button></div>
      </form>
      <div class="card" style="margin-top:24px;border-color:var(--danger)">
        <h3>Опасная зона</h3>
        <p class="muted">Удаление курса сотрёт все уроки, тесты и результаты учеников. Это нельзя отменить.</p>
        <button class="btn danger" id="delete-course">Удалить курс</button>
      </div>`;

    handleForm($('#settings'), (d) =>
      saveCourse({ ...courseFields(), ...d, min_age: Number(d.min_age), max_age: Number(d.max_age) })
    );
    $('#delete-course').addEventListener('click', async () => {
      if (prompt(`Чтобы удалить курс, введите его название: «${course.title}»`) !== course.title) return;
      await api(`/api/teacher/courses/${id}`, { method: 'DELETE' });
      location.href = '/teacher.html';
    });
  }

  if (await load()) render();
})();
