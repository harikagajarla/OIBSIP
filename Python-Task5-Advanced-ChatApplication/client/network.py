import queue, socket, threading
from common.protocol import encode

class ChatClient:
    def __init__(self): self.sock=None; self.events=queue.Queue(); self.lock=threading.Lock(); self.connected=False
    def connect(self, host, port):
        self.sock=socket.create_connection((host, int(port)), timeout=5); self.sock.settimeout(None); self.connected=True
        threading.Thread(target=self._receive, daemon=True).start()
    def send(self, action, **payload):
        if not self.connected: raise ConnectionError("Not connected to server.")
        with self.lock: self.sock.sendall(encode({"action":action, **payload}))
    def _receive(self):
        buffer=b""
        try:
            while self.connected:
                chunk=self.sock.recv(4096)
                if not chunk: raise ConnectionError("Server disconnected.")
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer=buffer.split(b"\n", 1)
                    import json; self.events.put(json.loads(line.decode("utf-8")))
        except (OSError, ValueError, ConnectionError) as exc: self.events.put({"event":"connection", "ok":False, "message":str(exc)})
        finally: self.connected=False
    def close(self):
        self.connected=False
        if self.sock:
            try: self.sock.close()
            except OSError: pass
