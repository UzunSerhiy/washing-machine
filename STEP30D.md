# Шаг 30Д — защита от устаревшего RUN

Добавлено поколение `_motion_generation`. RUN запоминает поколение и наличие аварийной блокировки до ожидания `_roller_lock`; непосредственно под блокировкой отклоняется команда, если поколение изменилось или при поступлении уже была авария. Поколение изменяется при обнаружении аварии, ошибке отправки команды, запуске REAL с постоянной блокировкой и успешном подтверждении восстановления.

Проверка охватывает `Machine.start_brush`, `start_roller_forward`, `start_roller_reverse`. HOME/AUTO/CALIBRATION вызывают эти методы, но отдельная защита на уровне начала длительных сценариев и HTTP-запросов **ещё не реализована**. Это не аппаратная функция безопасности.

Проверить:

```bash
unzip -o ~/Downloads/washing-machine-step30d-stale-run.zip -d .
docker compose exec backend python -m pytest -q tests/test_step30d_stale_motion_generation.py
docker compose exec backend python -m pytest -q
```

До полной проверки не коммитить и не проводить аппаратные испытания движения.
