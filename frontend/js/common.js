// Общие утилиты для всех страниц: запросы к API, шапка, уведомления, безопасный вывод текста.

const SUBJECTS = {
  english: { label: 'Английский', emoji: '🇬🇧' },
  math: { label: 'Математика', emoji: '🔢' },
};
const ROLES = { admin: 'Администратор', teacher: 'Преподаватель', student: 'Ученик' };
const AVATARS = ['🙂', '🦊', '🐼', '🐯', '🐸', '🦄', '🐙', '🐧', '🚀', '⭐', '🦖', '🐝'];

// Экранирование — ВСЕ данные с сервера вставляем в HTML только через esc()
function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      'X-Requested-With': 'fetch', // сервер отклоняет изменяющие запросы без этого заголовка (CSRF)
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === 'string' ? data.detail : 'Что-то пошло не так');
    err.status = res.status;
    throw err;
  }
  return data;
}

const params = new URLSearchParams(location.search);
const $ = (sel, root = document) => root.querySelector(sel);

function toast(message, type = '') {
  let box = $('#toasts');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toasts';
    box.setAttribute('role', 'status');
    document.body.append(box);
  }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  box.append(el);
  setTimeout(() => el.remove(), 3500);
}

// Мини-разметка для текста уроков: # заголовок, - список, **жирный**, *курсив*.
// Сначала экранируем, потом добавляем свои теги — так учитель не сможет вставить скрипт.
function renderRichText(text) {
  const inline = (s) =>
    esc(s)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>');
  const out = [];
  let list = null;
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trim();
    if (line.startsWith('- ')) {
      list ??= [];
      list.push(`<li>${inline(line.slice(2))}</li>`);
      continue;
    }
    if (list) {
      out.push(`<ul>${list.join('')}</ul>`);
      list = null;
    }
    if (!line) continue;
    if (line.startsWith('# ')) out.push(`<h3>${inline(line.slice(2))}</h3>`);
    else out.push(`<p>${inline(line)}</p>`);
  }
  if (list) out.push(`<ul>${list.join('')}</ul>`);
  return out.join('');
}

// Та же разметка, но в одну строку (для текста вопросов)
function renderInline(text) {
  return renderRichText(String(text || '').replace(/\n+/g, ' ')).replace(/^<p>|<\/p>$/g, '');
}

function starsHtml(n, max = 3) {
  return `<span class="stars" aria-label="${n} из ${max} звёзд">${'★'.repeat(n)}<span class="empty">${'★'.repeat(max - n)}</span></span>`;
}

function progressHtml(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  return `<div class="progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div style="width:${pct}%"></div></div>`;
}

function subjectBadge(subject) {
  const s = SUBJECTS[subject] || { label: subject, emoji: '' };
  return `<span class="badge ${esc(subject)}">${s.emoji} ${esc(s.label)}</span>`;
}

function courseCardHtml(c, extra = '', href = `/course.html?id=${c.id}`) {
  return `
    <a class="card course-card ${esc(c.subject)}" href="${href}">
      <div class="cover">${esc(c.cover)}</div>
      <div class="meta">${subjectBadge(c.subject)}<span class="badge">${c.min_age}–${c.max_age} лет</span></div>
      <h3>${esc(c.title)}</h3>
      <p>${esc(c.description)}</p>
      <div class="meta muted">${esc(c.teacher.avatar)} ${esc(c.teacher.name)} · ${c.lessons_count} ${plural(c.lessons_count, 'урок', 'урока', 'уроков')}</div>
      ${extra}
    </a>`;
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

function homeFor(user) {
  if (!user) return '/';
  return { admin: '/admin.html', teacher: '/teacher.html', student: '/student.html' }[user.role];
}

let currentUser = null;

async function loadUser() {
  try {
    currentUser = (await api('/api/auth/me')).user;
  } catch {
    currentUser = null;
  }
  renderHeader();
  return currentUser;
}

// Пускаем на страницу только нужные роли; остальных — на вход или в свой кабинет
async function guard(...roles) {
  const user = await loadUser();
  if (!user) {
    location.href = `/login.html?next=${encodeURIComponent(location.pathname + location.search)}`;
    throw new Error('redirect');
  }
  if (roles.length && !roles.includes(user.role)) {
    location.href = homeFor(user);
    throw new Error('redirect');
  }
  return user;
}

function renderHeader() {
  const header = $('#site-header');
  if (!header) return;
  const u = currentUser;
  const links = [['/catalog.html', '📚 Курсы']];
  if (u?.role === 'student') links.push(['/student.html', '🎒 Мои курсы']);
  if (u?.role === 'teacher' || u?.role === 'admin') links.push(['/teacher.html', '🧑‍🏫 Преподавание']);
  if (u?.role === 'admin') links.push(['/admin.html', '🛡️ Админка']);

  header.className = 'site-header';
  header.innerHTML = `
    <div class="inner">
      <a class="logo" href="/">🦉 <span>Умники</span></a>
      <nav class="nav">
        ${links
          .map(([href, label]) => `<a href="${href}" class="${location.pathname === href ? 'active' : ''}">${label}</a>`)
          .join('')}
      </nav>
      <div class="user-box">
        ${
          u
            ? `<span class="avatar">${esc(u.avatar)}</span><span class="name">${esc(u.name)}</span>
               <button class="btn small secondary" id="logout-btn">Выйти</button>`
            : `<a class="btn small secondary" href="/login.html">Войти</a>
               <a class="btn small" href="/register.html">Регистрация</a>`
        }
      </div>
    </div>`;

  $('#logout-btn')?.addEventListener('click', async () => {
    await api('/api/auth/logout', { method: 'POST' });
    location.href = '/';
  });
}

// Помощник для форм: собирает значения, блокирует кнопку на время запроса, показывает ошибки
function handleForm(form, onSubmit) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    btn && (btn.disabled = true);
    try {
      await onSubmit(Object.fromEntries(new FormData(form)), form);
    } catch (err) {
      if (err.message !== 'redirect') toast(err.message, 'error');
    } finally {
      btn && (btn.disabled = false);
    }
  });
}

function formatDate(iso) {
  return new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric',
  });
}
