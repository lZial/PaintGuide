/* PaintGuide — всплывающие подсказки не должны выходить за границы окна.
 *
 * Панель позиционируется средствами CSS относительно своего владельца
 * (элемент с data-popup-anchor), а скрипт уточняет положение:
 *
 *   • прижимает панель к краю окна, если та полностью не помещается;
 *   • переворачивает её вниз, если сверху не хватает места;
 *   • ограничивает высоту, когда панель не помещается ни в одну сторону.
 *
 * Разметка:
 *
 *   <span data-popup-anchor>
 *     <span data-popup>…</span>
 *   </span>
 */

(() => {
  const EDGE = 8; // минимальный отступ от края окна
  const GAP = 8; // зазор между панелью и владельцем

  const panels = document.querySelectorAll('[data-popup]');
  if (!panels.length) return;

  const ownerOf = (panel) => panel.closest('[data-popup-anchor]') || panel.parentElement;

  const place = (panel) => {
    const owner = ownerOf(panel);
    if (!owner) return;

    // Сбрасываем предыдущие правки, чтобы измерить панель «как есть».
    panel.classList.remove('is-flipped', 'is-clamped');
    panel.style.setProperty('--popup-shift', '0px');
    panel.style.removeProperty('--popup-max-height');

    const viewWidth = document.documentElement.clientWidth;
    const viewHeight = document.documentElement.clientHeight;

    const ownerRect = owner.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();

    const roomAbove = ownerRect.top - GAP - EDGE;
    const roomBelow = viewHeight - ownerRect.bottom - GAP - EDGE;

    if (panelRect.height > roomAbove) {
      if (panelRect.height <= roomBelow) {
        // Сверху не помещается — раскрываем панель вниз.
        panel.classList.add('is-flipped');
      } else {
        // Нигде целиком не помещается — ужимаем по месту и разрешаем прокрутку.
        const room = Math.max(roomAbove, roomBelow);
        panel.style.setProperty('--popup-max-height', `${Math.max(room, 80)}px`);
        panel.classList.add('is-clamped');
        if (roomBelow > roomAbove) panel.classList.add('is-flipped');
      }
    }

    // Горизонталь: панель не должна выходить за края окна.
    const rect = panel.getBoundingClientRect();
    let shift = 0;
    if (rect.left < EDGE) {
      shift = EDGE - rect.left;
    } else if (rect.right > viewWidth - EDGE) {
      shift = viewWidth - EDGE - rect.right;
    }
    if (shift) {
      // Владелец может быть масштабирован (например, при наведении),
      // поэтому экранное смещение переводим в локальные координаты.
      const scale = panel.offsetWidth ? rect.width / panel.offsetWidth : 1;
      panel.style.setProperty('--popup-shift', `${shift / scale}px`);
    }
  };

  let frame = 0;
  const placeAll = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      panels.forEach(place);
    });
  };

  panels.forEach((panel) => {
    const owner = ownerOf(panel);
    if (!owner) return;
    owner.addEventListener('mouseenter', () => place(panel));
    owner.addEventListener('focusin', () => place(panel));
  });

  // При прокрутке и изменении размера окна место сверху и снизу меняется —
  // пересчитываем положение открытых панелей.
  window.addEventListener('scroll', placeAll, { passive: true });
  window.addEventListener('resize', placeAll);
})();
