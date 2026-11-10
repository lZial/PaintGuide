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

// Всплывающий выбор вишлиста при добавлении краски.
// Кнопки .js-add-to-wishlist открывают панель #wishlist-chooser рядом с собой,
// а форма панели шлёт цель (краска или уровень гайда) на /wishlist/add.
(() => {
  const chooser = document.getElementById('wishlist-chooser');
  if (!chooser) return;

  const targetPaint = document.getElementById('chooser-target-paint');
  const targetGuide = document.getElementById('chooser-target-guide');
  const targetVariant = document.getElementById('chooser-target-variant');
  const nextField = document.getElementById('chooser-next');
  const cancelButton = document.getElementById('chooser-cancel');
  const listSelect = chooser.querySelector('select[name="wishlist_id"]');

  let activeButton = null;

  const hide = () => {
    chooser.style.display = 'none';
    activeButton = null;
  };

  const show = (button) => {
    activeButton = button;
    targetPaint.value = button.dataset.wishlistPaint || '';
    targetGuide.value = button.dataset.wishlistGuide || '';
    targetVariant.value = button.dataset.wishlistVariant || '';
    nextField.value = button.dataset.next || window.location.href;

    const rect = button.getBoundingClientRect();
    const panelWidth = chooser.offsetWidth || 280;
    const panelHeight = chooser.offsetHeight || 260;
    const viewWidth = document.documentElement.clientWidth;
    const viewHeight = document.documentElement.clientHeight;

    chooser.style.display = 'block';
    chooser.style.left = Math.min(Math.max(rect.left, 8), viewWidth - panelWidth - 8) + 'px';
    chooser.style.top = Math.min(rect.bottom + 8, viewHeight - panelHeight - 8) + 'px';

    if (listSelect && !listSelect.options.length) {
      // У пользователя ещё нет вишлистов — предложим создать.
      chooser.querySelector('button[type="submit"]').disabled = true;
    } else {
      chooser.querySelector('button[type="submit"]').disabled = false;
    }
  };

  document.querySelectorAll('.js-add-to-wishlist').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      show(button);
    });
  });

  cancelButton.addEventListener('click', hide);

  // Закрыть при клике снаружи панели.
  document.addEventListener('click', (event) => {
    if (
      chooser.style.display === 'block' &&
      !chooser.contains(event.target) &&
      activeButton &&
      !activeButton.contains(event.target)
    ) {
      hide();
    }
  });
})();
