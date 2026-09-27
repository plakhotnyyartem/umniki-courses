(async () => {
  const user = await guard();
  const app = $('#app');
  const id = Number(params.get('id'));

  let lesson;
  try {
    lesson = await api(`/api/lessons/${id}`);
  } catch (err) {
    app.innerHTML = `<div class="empty-state"><div class="icon">🔒</div><h2>${esc(err.message)}</h2><a class="btn" href="/catalog.html">К каталогу</a></div>`;
    return;
  }
  document.title = `${lesson.title} — Умники`;
  const isStudent = user.role === 'student';

  app.innerHTML = `
    <p><a href="/course.html?id=${lesson.course.id}">← ${esc(lesson.course.title)}</a></p>
    <div class="meta" style="margin-bottom:8px">${subjectBadge(lesson.course.subject)}<span class="badge">Урок ${lesson.index} из ${lesson.total_lessons}</span>
      ${lesson.progress ? `<span class="badge ok">Пройден ${starsHtml(lesson.progress.stars)}</span>` : ''}</div>
    <h1>${esc(lesson.title)}</h1>

    <article class="card lesson-content">
      ${lesson.video_embed ? `<div class="video"><iframe src="${esc(lesson.video_embed)}" title="Видео к уроку" allowfullscreen loading="lazy"></iframe></div>` : ''}
      ${renderRichText(lesson.content) || '<p class="muted">Текст урока пока не добавлен.</p>'}
    </article>

    <section id="quiz" style="margin-top:24px"></section>

    <nav class="lesson-nav">
      ${lesson.prev_id ? `<a class="btn secondary" href="/lesson.html?id=${lesson.prev_id}">← Предыдущий</a>` : '<span></span>'}
      ${lesson.next_id ? `<a class="btn secondary" href="/lesson.html?id=${lesson.next_id}">Следующий →</a>` : ''}
    </nav>`;

  const quiz = $('#quiz');

  if (!lesson.questions.length) {
    if (isStudent) {
      quiz.innerHTML = `<div class="card result-box"><button class="btn success" id="finish">✅ Я прочитал(а) урок</button></div>`;
      $('#finish').addEventListener('click', () => submit([]));
    }
    return;
  }

  quiz.innerHTML = `
    <form class="card" id="quiz-form">
      <h2>📝 Проверь себя</h2>
      ${lesson.questions
        .map(
          (q, qi) => `
          <fieldset class="quiz-q" style="border:0;padding:0;margin:0 0 18px">
            <legend class="q-text">${qi + 1}. ${renderInline(q.text)}</legend>
            ${q.kind === 'text' ? textAnswerHtml(q, qi) : choiceHtml(q, qi)}
          </fieldset>`
        )
        .join('')}
      ${isStudent ? '<button class="btn" type="submit">Проверить ответы</button>' : '<p class="muted">Вы видите тест как преподаватель: отмечены правильные ответы.</p>'}
      <div id="result"></div>
    </form>`;

  function choiceHtml(q, qi) {
    return `<div class="options">${q.options
      .map(
        (o, oi) => `
        <label class="option" data-q="${qi}" data-o="${oi}">
          <input type="radio" name="q${qi}" value="${oi}" ${!isStudent && oi === q.correct_index ? 'checked' : ''} ${isStudent ? '' : 'disabled'}>
          ${esc(o)}
        </label>`
      )
      .join('')}</div>`;
  }

  function textAnswerHtml(q, qi) {
    // Преподаватель видит принятые варианты вместо пустого поля
    const value = isStudent ? '' : q.accepted.join(' / ');
    return `
      <div class="text-answer" data-q="${qi}">
        <input type="text" name="q${qi}" value="${esc(value)}" maxlength="200" placeholder="Напиши ответ…"
               autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Ответ на вопрос ${qi + 1}" ${isStudent ? '' : 'disabled'}>
        <div class="answer-hint" aria-live="polite"></div>
      </div>`;
  }

  if (!isStudent) return;

  $('#quiz-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const answers = lesson.questions.map((q, qi) => {
      if (q.kind === 'text') {
        const value = e.target.querySelector(`input[name="q${qi}"]`).value.trim();
        return value || null;
      }
      const checked = e.target.querySelector(`input[name="q${qi}"]:checked`);
      return checked ? Number(checked.value) : null;
    });
    if (answers.includes(null) && !confirm('Ты ответил(а) не на все вопросы. Всё равно проверить?')) return;
    submit(answers);
  });

  async function submit(answers) {
    try {
      const res = await api(`/api/lessons/${lesson.id}/submit`, { method: 'POST', body: { answers } });
      showResult(res);
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  function showResult(res) {
    // Подсвечиваем правильные и неправильные ответы
    clearMarks();
    res.results.forEach((r, qi) => {
      const textBox = document.querySelector(`.text-answer[data-q="${qi}"]`);
      if (textBox) {
        textBox.classList.add(r.correct ? 'correct' : 'wrong');
        textBox.querySelector('.answer-hint').innerHTML = r.correct
          ? '✅ Верно!'
          : `Правильный ответ: <strong>${esc(r.expected)}</strong>`;
        return;
      }
      document.querySelectorAll(`.option[data-q="${qi}"]`).forEach((el) => {
        const oi = Number(el.dataset.o);
        const chosen = el.querySelector('input').checked;
        if (oi === r.correct_index) el.classList.add('correct');
        else if (chosen) el.classList.add('wrong');
      });
    });

    const cheers = ['Попробуй ещё раз — у тебя получится! 💪', 'Неплохо! Можно ещё лучше 🙂', 'Отлично! 👏', 'Идеально! Ты супер! 🏆'];
    const box = $('#result') || quiz;
    box.innerHTML = `
      <div class="result-box">
        <div class="big-stars">${starsHtml(res.stars)}</div>
        ${res.total ? `<h3>${res.score} из ${res.total} правильно</h3>` : '<h3>Урок пройден!</h3>'}
        <p>${cheers[res.stars]}</p>
        <div class="meta" style="justify-content:center">
          ${res.total ? '<button class="btn secondary" type="button" id="retry">🔁 Ещё раз</button>' : ''}
          ${lesson.next_id ? `<a class="btn" href="/lesson.html?id=${lesson.next_id}">Следующий урок →</a>` : `<a class="btn" href="/course.html?id=${lesson.course.id}">К курсу</a>`}
        </div>
      </div>`;
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    $('#retry')?.addEventListener('click', () => {
      clearMarks();
      $('#quiz-form').reset();
      box.innerHTML = '';
      quiz.scrollIntoView({ behavior: 'smooth' });
    });
  }

  function clearMarks() {
    document.querySelectorAll('.option, .text-answer').forEach((el) => el.classList.remove('correct', 'wrong'));
    document.querySelectorAll('.answer-hint').forEach((el) => (el.textContent = ''));
  }
})();
