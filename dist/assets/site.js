(() => {
  const search = document.querySelector('#project-search');
  const grid = document.querySelector('.project-grid');
  const filters = [...document.querySelectorAll('[data-filter]')];
  const empty = document.querySelector('#no-results');
  if (!search || !grid) return;

  let category = 'todos';
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  function update() {
    const term = normalize(search.value);
    let visible = 0;
    for (const card of grid.querySelectorAll('.project-card')) {
      const matches = (category === 'todos' || card.dataset.category === category)
        && normalize(card.dataset.search).includes(term);
      card.hidden = !matches;
      if (matches) visible++;
    }
    empty.hidden = visible > 0;
  }
  for (const button of filters) button.addEventListener('click', () => {
    category = button.dataset.filter;
    for (const item of filters) {
      const active = item === button;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-pressed', String(active));
    }
    update();
  });
  search.addEventListener('input', update);
  document.addEventListener('forja:projects-updated', update);
})();
