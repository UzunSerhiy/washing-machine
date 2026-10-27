# №31В — ESP32 HOME freshness integration regressions

Four tests using an in-memory ESP32 sensor and simulated HOME states, without opening serial ports or issuing motor commands:

- Stale triggered state becomes disconnected/untriggered and cannot be used as HOME.
- Repeated reads after timeout do not repeatedly advance connection generation.
- HOME search fails on sensor disconnection.
- HOME search fails on reconnect with a new generation even if the sensor reports a pulse.

These are synchronous regression tests, not proof of physical STOP on lost ESP32 connectivity. Hardware STOP and serial watchdog behavior require separate validation.
