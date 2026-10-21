/* PaintGuide — вспомогательный скрипт админ-панели */

/**
 * Поле выбора краски в конструкторе шагов.
 *
 * В справочнике несколько тысяч красок. Если отрисовывать их в выпадающем
 * списке для каждого из ~150 слотов, страница редактора разрастается до
 * мегабайтов. Поэтому список подсказок собирается на клиенте из одного
 * JSON-блока, а в скрытое поле кладётся идентификатор краски.
 */
(() => {
  const node = document.getElementById('paint-index');
  if (!node) return;

  let index;
  try {
    index = JSON.parse(node.textContent);
  } catch (error) {
    return;
  }
  if (!index || !Array.isArray(index.paints)) return;

  const brandNames = index.brands || {};

  // Собираем список подсказок один раз на страницу.
  const list = document.createElement('datalist');
  list.id = 'pg-paint-list';
  for (const paint of index.paints) {
    const option = document.createElement('option');
    option.value = `${brandNames[paint.b] || ''} · ${paint.n} (${paint.c})`;
    list.appendChild(option);
  }
  document.body.appendChild(list);

  // Карта «подпись → идентификатор». Основная подпись и короткая.
  const byLabel = new Map();
  for (const paint of index.paints) {
    const full = `${brandNames[paint.b] || ''} · ${paint.n} (${paint.c})`;
    byLabel.set(full, paint.i);
    byLabel.set(`${paint.n} (${paint.c})`, paint.i);
  }

  const inputs = document.querySelectorAll('[data-paint-input]');
  if (!inputs.length) return;

  inputs.forEach((input) => {
    const hidden = document.querySelector(`[data-paint-value][name="${input.dataset.paintHidden}"]`);
    if (!hidden) return;

    const resolve = () => {
      const value = input.value.trim();
      if (!value) {
        hidden.value = '';
        input.removeAttribute('data-invalid');
        return;
      }
      const found = byLabel.get(value);
      if (found !== undefined) {
        hidden.value = String(found);
        input.removeAttribute('data-invalid');
      } else {
        hidden.value = '';
        input.setAttribute('data-invalid', '1');
      }
    };

    input.addEventListener('change', resolve);
    input.addEventListener('blur', resolve);
    // Значение могло прийти с сервера — сразу приводим его к каноническому виду.
    if (input.value && !hidden.value) resolve();
  });
})();
