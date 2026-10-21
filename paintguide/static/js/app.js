/* PaintGuide — клиентская логика */

(() => {
  const menuButton = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#site-nav');

  if (menuButton && navigation) {
    menuButton.addEventListener('click', () => {
      const open = navigation.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
    navigation.addEventListener('click', (event) => {
      if (event.target.closest('a')) {
        navigation.classList.remove('open');
        menuButton.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Подтверждение опасных действий
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  // Смена размера метки сложности при переключении уровня
  document.querySelectorAll('[data-level-switch]').forEach((group) => {
    group.addEventListener('click', (event) => {
      const link = event.target.closest('a');
      if (!link) return;
      event.preventDefault();
      window.location.href = link.href;
    });
  });

  // Автоотправка фильтров каталога при смене селекта
  const catalogForm = document.querySelector('[data-auto-submit]');
  if (catalogForm) {
    catalogForm.querySelectorAll('select').forEach((select) => {
      select.addEventListener('change', () => catalogForm.submit());
    });
  }

  // Подсветка активного пункта навигации по текущему пути
  const path = window.location.pathname;
  document.querySelectorAll('.nav a').forEach((link) => {
    const href = link.getAttribute('href');
    if (!href || href === '/') return;
    if (path === href || path.startsWith(href + '/')) {
      link.classList.add('active');
    }
  });
})();
