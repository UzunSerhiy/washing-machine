# Патч 32H — исправление React purity и мигания

- Убирает Date.now() из рендера, исправляет lint и prerender /auto.
- Сохраняет таймер useEffect каждые 500 мс.
- Разрешает метке успешного ответа быть не более чем на 1000 мс новее последнего тика; верхняя граница возраста диагностики 10 секунд остаётся.
- Не меняет backend и аппаратные блокировки.

Установка: unzip -o ~/Downloads/washing-machine-step32h-react-purity-fix.zip -d .
Затем: cd frontend && npm run lint && npm run build
