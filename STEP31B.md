# №31Б — RS485 fault admission tests

Five mocked tests exercise the `Machine` motion preflight and monitoring paths when a GAIN fault-register read raises `TimeoutError` on any of three drives. They assert that a communication failure latches a software fault, best-effort STOP is attempted, reconnection alone does not clear the latch, and a failed STOP does not erase the original fault. No hardware commands are issued.

These tests do **not** establish that a drive already running stops when the bus is lost, nor that the periodic monitor is scheduled at a safe frequency. A wired E-STOP and an independently validated safe-stop architecture remain necessary.
