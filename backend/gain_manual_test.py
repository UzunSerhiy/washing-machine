from app.services.modbus.client import ModbusClient
from app.services.modbus.gain import GainDrive

PORT = "/dev/ttyUSB0"
DEVICE_ID = 1

client = ModbusClient(
    port=PORT,
    baudrate=9600,
)

try:
    if not client.connect():
        print("Error connecting for RS485")
        raise SystemExit(1)
    print("RS485 connected")

    drive = GainDrive(client=client, device_id=DEVICE_ID)

    status = drive.get_status()
    frequency = drive.get_frequency()
    fault = drive.get_fault()

    print(f"Status: {status}")
    print(f"Frequncy: {frequency: .2f} Hz")
    print(f"Fault: {fault}")

finally:
    client.close()
    print("RS485 disconnected")
