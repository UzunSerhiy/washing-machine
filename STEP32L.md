# Шаг 32L — HOME как диалог в MANUAL

Изменены только два файла frontend. Кнопка Point0 зелёная при подтверждённом HOME, красная при отсутствии HOME, янтарная при ошибке/загрузке данных. Нажатие открывает диалог с действующими командами поиска/отмены и диагностикой ESP32. Устаревшее read-only окно Point0 не показывается на MANUAL. AUTO и CALIBRATION не изменены.

Установка из корня проекта:

```bash
unzip -o ~/Downloads/washing-machine-step32l-home-dialog.zip -d .
cd frontend
npm run lint && npm run build
```

Изменений backend, команд частотников, скорости и алгоритма HOME нет.
