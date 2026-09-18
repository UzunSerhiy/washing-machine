from pymodbus.client import ModbusSerialClient


class ModbusClient:
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
    ):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )

    def connect(self) -> bool:
        return self.client.connect()

    def close(self) -> None:
        self.client.close()

    def read_register(
        self,
        address: int,
        device_id: int,
    ) -> int:
        result = self.client.read_holding_registers(
            address=address,
            count=1,
            device_id=device_id,
        )

        if result.isError():
            raise RuntimeError(
                f"Modubus read error: "
                f"address=0x{address:04X}, "
                f"device_id={device_id}, "
                f"response={result}"
            )
        return result.registers[0]

    def write_register(
        self,
        address: int,
        value: int,
        device_id: int,
    ) -> None:
        result = self.client.write_register(
            address=address,
            value=value,
            device_id=device_id,
        )

        if result.isError():
            raise RuntimeError(
                f"Modbus write error: "
                f"address=0x{address:04X}, "
                f"value={value}, "
                f"device_id={device_id}, "
                f"response={result}"
            )
