(async () => {
  const me = await guard('admin');
  const app = $('#app');
  let tab = location.hash.slice(1) || 'users';

  app.innerHTML = `
    <div class="page-head"><h1>🛡️ Администрирование</h1></div>
    <div class="stats" id="stats"></div>
    <div class="tabs" role="tablist">
      <button role="tab" data-tab="users">👤 Пользователи</button>
      <button role="tab" data-tab="courses">📚 Все курсы</button>
    </div>
    <div id="tab-body"></div>`;

  app.querySelector('.tabs').addEventListener('click', (e) => {
    const b = e.target.closest('[data-tab]');
    if (!b) return;
    tab = b.dataset.tab;
    history.replaceState(null, '', `#${tab}`);
    renderTab();
  });

  async function renderStats() {
    const s = await api('/api/admin/stats');
    const stat = (value, label) => `<div class="card stat"><div class="value">${value}</div><div class="label">${label}</div></div>`;
    $('#stats').innerHTML = [
      stat(s.users.student || 0, '🎒 учеников'),
      stat(s.users.teacher || 0, '🧑‍🏫 преподавателей'),
      stat(`${s.published}/${(s.courses.english || 0) + (s.courses.math || 0)}`, '📚 курсов опубликовано'),
      stat(s.enrollments, '✍️ записей на курсы'),
      stat(s.lessons_completed, '✅ уроков пройдено'),
    ].join('');
  }

  function renderTab() {
    app.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
    (tab === 'courses' ? renderCourses : renderUsers)();
  }

  // ---------- Пользователи ----------
  const filter = { role: '', q: '' };

  async function renderUsers() {
    const body = $('#tab-body');
    body.innerHTML = `
      <div class="filters">
        <select id="role-filter" aria-label="Роль">
          <option value="">Все роли</option>
          ${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${filter.role === k ? 'selected' : ''}>${v}</option>`).join('')}
        </select>
        <input id="user-q" type="search" placeholder="Имя или email…" value="${esc(filter.q)}" aria-label="Поиск">
        <button class="btn" id="add-user-btn">＋ Добавить пользователя</button>
      </div>

      <form class="card stack hidden" id="user-form" style="margin-bottom:20px">
        <h3>Новый пользователь</h3>
        <div class="row">
          <label>Имя <input name="name" required minlength="2" maxlength="80"></label>
          <label>Email <input name="email" type="email" required></label>
          <label>Временный пароль <input name="password" type="text" required minlength="8" autocomplete="off"></label>
          <label>Роль
            <select name="role" id="new-role">
              <option value="teacher">Преподаватель</option>
              <option value="student">Ученик</option>
              <option value="admin">Администратор</option>
            </select>
          </label>
        </div>
        <div class="row hidden" id="student-fields">
          <label>Возраст <input name="age" type="number" min="5" max="14"></label>
        </div>
        <div class="meta"><button class="btn" type="submit">Создать</button><button class="btn secondary" type="button" id="user-cancel">Отмена</button></div>
      </form>

      <div class="card table-wrap" id="users-table"><p class="muted">Загрузка…</p></div>`;

    const form = $('#user-form');
    $('#add-user-btn').addEventListener('click', () => form.classList.remove('hidden'));
    $('#user-cancel').addEventListener('click', () => form.classList.add('hidden'));
    $('#new-role').addEventListener('change', (e) => $('#student-fields').classList.toggle('hidden', e.target.value !== 'student'));
    $('#role-filter').addEventListener('change', (e) => { filter.role = e.target.value; loadUsers(); });
    let timer;
    $('#user-q').addEventListener('input', (e) => {
      clearTimeout(timer);
      timer = setTimeout(() => { filter.q = e.target.value.trim(); loadUsers(); }, 250);
    });

    handleForm(form, async (d) => {
      await api('/api/admin/users', {
        method: 'POST',
        body: { ...d, age: d.age ? Number(d.age) : null },
      });
      toast('Пользователь создан. Передайте ему временный пароль.', 'success');
      form.reset();
      form.classList.add('hidden');
      loadUsers();
      renderStats();
    });

    $('#users-table').addEventListener('change', async (e) => {
      const sel = e.target.closest('select[data-role-for]');
      if (!sel) return;
      try {
        await api(`/api/admin/users/${sel.dataset.roleFor}`, { method: 'PATCH', body: { role: sel.value } });
        toast('Роль изменена', 'success');
        renderStats();
      } catch (err) {
        toast(err.message, 'error');
      }
      loadUsers();
    });

    $('#users-table').addEventListener('click', async (e) => {
      const b = e.target.closest('[data-action]');
      if (!b) return;
      const uid = b.dataset.id;
      try {
        if (b.dataset.action === 'toggle') {
          await api(`/api/admin/users/${uid}`, { method: 'PATCH', body: { is_active: b.dataset.active !== '1' } });
        }
        if (b.dataset.action === 'delete') {
          if (!confirm(`Удалить пользователя «${b.dataset.name}» и все его данные?`)) return;
          await api(`/api/admin/users/${uid}`, { method: 'DELETE' });
        }
        loadUsers();
        renderStats();
      } catch (err) {
        toast(err.message, 'error');
      }
    });

    loadUsers();
  }

  async function loadUsers() {
    const qs = new URLSearchParams(Object.entries(filter).filter(([, v]) => v));
    const users = await api(`/api/admin/users?${qs}`);
    $('#users-table').innerHTML = users.length
      ? `<table>
          <thead><tr><th>Пользователь</th><th>Роль</th><th>Возраст</th><th>Статус</th><th>Создан</th><th></th></tr></thead>
          <tbody>
            ${users
              .map((u) => {
                const self = u.id === me.id;
                return `
                <tr>
                  <td><strong>${esc(u.avatar)} ${esc(u.name)}</strong>${self ? ' <span class="badge">это вы</span>' : ''}
                    <div class="muted" style="font-size:14px">${esc(u.email)}</div></td>
                  <td>${
                    self
                      ? `<span class="badge role-${u.role}">${ROLES[u.role]}</span>`
                      : `<select data-role-for="${u.id}" aria-label="Роль">${Object.entries(ROLES)
                          .map(([k, v]) => `<option value="${k}" ${u.role === k ? 'selected' : ''}>${v}</option>`)
                          .join('')}</select>`
                  }</td>
                  <td>${u.age ?? '—'}</td>
                  <td>${u.is_active ? '<span class="badge ok">Активен</span>' : '<span class="badge off">Заблокирован</span>'}</td>
                  <td class="muted">${formatDate(u.created_at)}</td>
                  <td class="actions">${
                    self
                      ? ''
                      : `<button class="btn small secondary" data-action="toggle" data-id="${u.id}" data-active="${u.is_active ? 1 : 0}">${u.is_active ? '🔒 Заблокировать' : '🔓 Разблокировать'}</button>
                         <button class="btn small ghost" data-action="delete" data-id="${u.id}" data-name="${esc(u.name)}" aria-label="Удалить">🗑</button>`
                  }</td>
                </tr>`;
              })
              .join('')}
          </tbody>
        </table>`
      : '<p class="muted">Никого не нашлось.</p>';
  }

  // ---------- Курсы ----------
  async function renderCourses() {
    const body = $('#tab-body');
    body.innerHTML = '<p class="muted">Загрузка…</p>';
    const courses = await api('/api/admin/courses');
    body.innerHTML = `
      <div class="card table-wrap">
        <table>
          <thead><tr><th>Курс</th><th>Предмет</th><th>Преподаватель</th><th>Уроков</th><th>Учеников</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            ${courses
              .map(
                (c) => `
                <tr>
                  <td><a href="/course.html?id=${c.id}"><strong>${esc(c.cover)} ${esc(c.title)}</strong></a><div class="muted" style="font-size:14px">${c.min_age}–${c.max_age} лет</div></td>
                  <td>${subjectBadge(c.subject)}</td>
                  <td>${esc(c.teacher.avatar)} ${esc(c.teacher.name)}</td>
                  <td>${c.lessons_count}</td>
                  <td>${c.students_count}</td>
                  <td>${c.is_published ? '<span class="badge ok">Опубликован</span>' : '<span class="badge off">Черновик</span>'}</td>
                  <td class="actions">
                    <button class="btn small secondary" data-pub="${c.id}" data-value="${c.is_published ? 0 : 1}">${c.is_published ? 'Скрыть' : 'Опубликовать'}</button>
                    <a class="btn small ghost" href="/teacher-course.html?id=${c.id}" aria-label="Редактировать">✏️</a>
                  </td>
                </tr>`
              )
              .join('')}
          </tbody>
        </table>
      </div>`;

    body.querySelector('table').addEventListener('click', async (e) => {
      const b = e.target.closest('[data-pub]');
      if (!b) return;
      try {
        await api(`/api/admin/courses/${b.dataset.pub}`, { method: 'PATCH', body: { is_published: b.dataset.value === '1' } });
        renderCourses();
        renderStats();
      } catch (err) {
        toast(err.message, 'error');
      }
    });
  }

  renderStats();
  renderTab();
})();
