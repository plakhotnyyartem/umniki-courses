// Сортировка списка перетаскиванием за «ручку».
// Pointer Events вместо HTML5 drag-and-drop: одинаково работают мышь, палец и стилус.
// С клавиатуры: фокус на ручке (Tab) и стрелки ↑/↓.
//
// sortable(container, { items, handle, onChange(ids) })
//   items  — селектор элементов списка (прямые потомки container) с атрибутом data-sort-id
//   handle — селектор ручки внутри элемента
//   onChange получает новый порядок id после каждого перемещения

function sortable(container, { items = '[data-sort-id]', handle = '.drag-handle', onChange }) {
  const list = () => [...container.children].filter((el) => el.matches(items));
  const order = () => list().map((el) => Number(el.dataset.sortId));
  let drag = null;

  container.addEventListener('pointerdown', (e) => {
    const h = e.target.closest(handle);
    if (!h || e.button !== 0 || !container.contains(h)) return;
    const item = h.closest(items);
    if (!item || item.parentElement !== container) return;
    e.preventDefault(); // не выделять текст и не начинать прокрутку на тач-экране
    h.setPointerCapture(e.pointerId);
    drag = { item, handle: h, before: order().join() };
    item.classList.add('dragging');
    document.body.classList.add('is-sorting');
  });

  container.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const y = e.clientY;
    // Автопрокрутка, если тянем к краю экрана
    if (y < 70) scrollBy(0, -12);
    else if (y > innerHeight - 70) scrollBy(0, 12);

    const others = list().filter((el) => el !== drag.item);
    const target = others.find((el) => {
      const r = el.getBoundingClientRect();
      return y < r.top + r.height / 2;
    });
    if (target) {
      if (drag.item.nextElementSibling !== target) target.before(drag.item);
    } else if (others.length) {
      const last = others[others.length - 1];
      if (last.nextElementSibling !== drag.item) last.after(drag.item);
    }
  });

  const finish = () => {
    if (!drag) return;
    const { item, before } = drag;
    drag = null;
    item.classList.remove('dragging');
    document.body.classList.remove('is-sorting');
    if (order().join() !== before) onChange(order(), item);
  };
  container.addEventListener('pointerup', finish);
  container.addEventListener('pointercancel', finish);

  // Ручка может лежать внутри <summary> — клик по ней не должен сворачивать/разворачивать урок
  container.addEventListener('click', (e) => {
    if (e.target.closest(handle)) e.preventDefault();
  });

  container.addEventListener('keydown', (e) => {
    const h = e.target.closest(handle);
    if (!h || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
    const item = h.closest(items);
    if (!item || item.parentElement !== container) return;
    e.preventDefault();
    const all = list();
    const i = all.indexOf(item);
    const j = e.key === 'ArrowUp' ? i - 1 : i + 1;
    if (j < 0 || j >= all.length) return;
    if (e.key === 'ArrowUp') all[j].before(item);
    else all[j].after(item);
    h.focus();
    onChange(order(), item);
  });
}
