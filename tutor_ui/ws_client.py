import asyncio
import json

import websockets
from PyQt5.QtCore import QThread, pyqtSignal


class TutorWSClient(QThread):
    message_received = pyqtSignal(dict)
    connection_failed = pyqtSignal(str)

    def __init__(self, ws_url: str):
        super().__init__()
        self.ws_url = ws_url
        self._running = True

    def stop(self) -> None:
        self._running = False

    async def _listen(self):
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    while self._running:
                        raw = await ws.recv()
                        self.message_received.emit(json.loads(raw))
            except Exception as ex:
                self.connection_failed.emit(str(ex))
                await asyncio.sleep(2)

    def run(self):
        asyncio.run(self._listen())
