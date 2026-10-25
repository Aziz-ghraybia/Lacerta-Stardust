import asyncio
import threading
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERVICE_UUID      = "0000ff00-0000-1000-8000-00805f9b34fb"
COMMAND_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"


class BleClient:
    def __init__(self, on_signal, on_connected, on_disconnected):
        self.on_signal       = on_signal
        self.on_connected    = on_connected
        self.on_disconnected = on_disconnected

        self._client: BleakClient | None = None
        self._connected      = False
        self._disconnecting  = False   # guard against double-fire

        # One persistent event loop that lives for the app's lifetime
        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True
        )
        self._thread.start()

    # ------------------------------------------------------------------ #
    #  Persistent loop — runs forever in background thread               #
    # ------------------------------------------------------------------ #

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def connect(self, address: str):
        if self._connected:
            return
        asyncio.run_coroutine_threadsafe(
            self._connect_and_listen(address), self._loop
        )

    def disconnect(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._do_disconnect(), self._loop
            )

    @property
    def connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    #  Internal async logic                                               #
    # ------------------------------------------------------------------ #

    async def _connect_and_listen(self, address: str):
        self._disconnecting = False

        def handle_disconnect(_: BleakClient):
            if not self._disconnecting:
                self._disconnecting = True
                self._connected = False
                self.on_disconnected()

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"[BLE] Attempt {attempt}/{max_attempts}...")
                self._client = BleakClient(
                    address,
                    disconnected_callback=handle_disconnect,
                    timeout=15.0
                )
                await self._client.connect()

                # Only check connection state — no artificial delay
                if not self._client.is_connected:
                    print(f"[BLE] Dropped immediately on attempt {attempt}")
                    if attempt < max_attempts:
                        await asyncio.sleep(0.3)  # Short pause before retry
                        continue
                    else:
                        self.on_disconnected()
                        return

                await self._client.start_notify(
                    COMMAND_CHAR_UUID, self._handle_notification
                )

                self._connected = True
                self.on_connected()
                print("[BLE] Connected and subscribed")
                return  # Exit — handle_disconnect callback handles the rest

            except BleakError as e:
                print(f"[BLE] Attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(0.3)  # Short pause before retry
                else:
                    self._connected = False
                    self.on_disconnected()
            except Exception as e:
                print(f"[BLE] Unexpected error on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(0.3)
                else:
                    self._connected = False
                    self.on_disconnected()

    def _handle_notification(self, sender, data: bytearray):
        signal = data.decode("utf-8").strip()
        print(f"[BLE] Signal received: {signal}")
        if signal in ("NEXT", "PREV"):
            self.on_signal(signal)
        elif signal == "DISCONNECT":
            print("[BLE] Android disconnecting cleanly")
            asyncio.run_coroutine_threadsafe(
                self._do_disconnect(), self._loop
            )

    async def _do_disconnect(self):
        if self._disconnecting:
            return
        self._disconnecting = True
        self._connected = False
        try:
            if self._client and self._client.is_connected:
                await self._client.disconnect()
        except Exception as e:
            print(f"[BLE] Disconnect error (safe to ignore): {e}")
        finally:
            self.on_disconnected()
