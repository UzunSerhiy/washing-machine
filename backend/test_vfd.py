import time
from pymodbus.client import ModbusSerialClient

PORT = "/dev/ttyUSB0"
SLAVE_ID = 1

FREQUENCY_HZ = 5.0

client = ModbusSerialClient(
    port=PORT,
    baudrate=9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1,
)


def read_status():
    result = client.read_holding_registers(
        address=0x3000,
        count=1,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("Read status Error", result)
        return None

    return result.registers[0]


def read_frequency():
    result = client.read_holding_registers(
        address=0x1001,
        count=1,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("Read frequency error", result)

    return result.registers[0] / 100


try:
    if not client.connect():
        print("Error opening /dev/ttyUSB0")
        raise SystemExit(1)

    print("RS485 connected")

    # -------------------------------------------------
    # 1. Читаем начальное состояние
    # -------------------------------------------------

    status = read_status()
    frequency = read_frequency()

    print(f"Initial status: {status}")
    print(f"Initial frequency: {frequency} Hz")

    # -------------------------------------------------
    # 2. Устанавливаем 50 Hz
    # -------------------------------------------------

    frequency_value = int(FREQUENCY_HZ * 100)

    result = client.write_register(
        address=0x1000,
        value=frequency_value,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("Ошибка установки частоты:", result)
        raise SystemExit(1)

    print(f"Frequency set to {FREQUENCY_HZ} Hz")

    # -------------------------------------------------
    # 3. Команда Forward Run
    # -------------------------------------------------

    result = client.write_register(
        address=0x2000,
        value=0x0001,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("Ошибка запуска:", result)
        raise SystemExit(1)

    print("RUN command sent")

    # -------------------------------------------------
    # 4. Проверяем состояние сразу после запуска
    # -------------------------------------------------

    time.sleep(1)

    status = read_status()
    frequency = read_frequency()

    print(f"Running status: {status}")
    print(f"Running frequency: {frequency} Hz")

    # -------------------------------------------------
    # 5. Работаем 5 секунд
    # -------------------------------------------------

    print("Motor running for 5 seconds...")
    time.sleep(5)

    # -------------------------------------------------
    # 6. Deceleration Stop
    # -------------------------------------------------

    result = client.write_register(
        address=0x2000,
        value=0x0006,
        device_id=SLAVE_ID,
    )

    if result.isError():
        print("Ошибка остановки:", result)
    else:
        print("STOP command sent")

    # -------------------------------------------------
    # 7. Проверяем состояние
    # -------------------------------------------------

    time.sleep(1)

    status = read_status()
    frequency = read_frequency()

    print(f"Final status: {status}")
    print(f"Final frequency: {frequency} Hz")

finally:
    client.close()
    print("RS485 disconected")


result = client.read_holding_registers(
    address=0x3000,
    count=1,
    device_id=1,
)

if result.isError():
    print("Modbus error:", result)
else:
    print("STATUS 3000 =", result.registers[0])

client.close()
