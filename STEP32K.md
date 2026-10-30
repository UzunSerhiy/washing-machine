# Step 32K — исправление сборки 32J

1. Добавлено поле `awaiting_stop_confirmation` в тип `CalibrationHomeStatus`.
2. Создан `backend/.dockerignore`: исключает runtime-файл состояния аварий из контекста сборки. Файл на диске не удаляется.

Из корня проекта:

```bash
unzip -o ~/Downloads/washing-machine-step32k-build-fix.zip -d .
cd frontend && npm run lint && npm run build
cd .. && docker compose up -d --build backend
```

В случае, если Docker продолжает сообщать `permission denied`, проверь права доступа к каталогу `backend` и поддержку `.dockerignore` используемой версией Docker. Не удаляй состояние аварий и не сбрасывай E15.
