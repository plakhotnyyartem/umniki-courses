(async () => {
  const user = await loadUser();
  const app = $('#app');
  const state = {
    subject: params.get('subject') || '',
    age: params.get('age') || (user?.role === 'student' && user.age ? String(user.age) : ''),
    q: '',
  };

  const ages = Array.from({ length: 10 }, (_, i) => i + 5);
  app.innerHTML = `
    <div class="page-head"><h1>Каталог курсов</h1></div>
    <div class="filters">
      <div class="chips" id="subject-chips">
        <button class="chip" data-subject="">Все</button>
        <button class="chip" data-subject="english">🇬🇧 Английский</button>
        <button class="chip" data-subject="math">🔢 Математика</button>
      </div>
      <select id="age" aria-label="Возраст">
        <option value="">Любой возраст</option>
        ${ages.map((a) => `<option value="${a}">${a} ${plural(a, 'год', 'года', 'лет')}</option>`).join('')}
      </select>
      <input id="q" type="search" placeholder="Поиск по названию…" aria-label="Поиск">
    </div>
    <div class="grid" id="list"></div>`;

  $('#age').value = state.age;

  async function refresh() {
    document.querySelectorAll('#subject-chips .chip').forEach((b) =>
      b.classList.toggle('active', b.dataset.subject === state.subject)
    );
    const qs = new URLSearchParams(Object.entries(state).filter(([, v]) => v));
    history.replaceState(null, '', qs.size ? `?${qs}` : location.pathname);
    const courses = await api(`/api/courses?${qs}`);
    $('#list').innerHTML = courses.length
      ? courses.map((c) => courseCardHtml(c)).join('')
      : `<div class="empty-state" style="grid-column:1/-1"><div class="icon">🔍</div><p>Ничего не нашлось. Попробуйте изменить фильтры.</p></div>`;
  }

  $('#subject-chips').addEventListener('click', (e) => {
    const btn = e.target.closest('.chip');
    if (!btn) return;
    state.subject = btn.dataset.subject;
    refresh();
  });
  $('#age').addEventListener('change', (e) => { state.age = e.target.value; refresh(); });
  let timer;
  $('#q').addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.q = e.target.value.trim(); refresh(); }, 250);
  });

  refresh();
})();
