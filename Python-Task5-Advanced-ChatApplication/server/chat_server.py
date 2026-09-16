import logging, socket, threading
from pathlib import Path
from common.emoji import resolve_emoji
from common.protocol import ProtocolError, decode_line, encode
from database.storage import ChatDatabase

LOG = logging.getLogger(__name__)

class ChatServer:
    def __init__(self, host="127.0.0.1", port=5000, database_path=None):
        self.host, self.port = host, port
        self.db = ChatDatabase(database_path or Path(__file__).parents[1] / "database" / "chat.db")
        self.clients, self.lock, self.running, self.sock = {}, threading.RLock(), threading.Event(), None
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port)); self.sock.listen(); self.sock.settimeout(.25); self.port = self.sock.getsockname()[1]; self.running.set()
        while self.running.is_set():
            try: client, address = self.sock.accept()
            except socket.timeout: continue
            except OSError: break
            threading.Thread(target=self._handle_client, args=(client, address), daemon=True).start()
    def stop(self):
        self.running.clear()
        if self.sock:
            try: self.sock.close()
            except OSError: pass
        with self.lock:
            handlers = list(self.clients.values())
        for handler in handlers: handler.close()
        self.db.close()
    def _handle_client(self, sock, address):
        handler = ClientHandler(self, sock, address)
        handler.run()
    def add_client(self, username, handler):
        with self.lock: self.clients[username] = handler
    def remove_client(self, handler):
        if handler.username:
            with self.lock:
                if self.clients.get(handler.username) is handler: self.clients.pop(handler.username, None)
    def broadcast(self, room_id, message):
        members = self.db.room_members(room_id)
        with self.lock: recipients = [self.clients[u] for u in members if u in self.clients]
        for client in recipients: client.send(message)

class ClientHandler:
    def __init__(self, server, sock, address): self.server, self.sock, self.address, self.username, self.current_room, self.send_lock = server, sock, address, None, None, threading.Lock()
    def send(self, message):
        try:
            with self.send_lock: self.sock.sendall(encode(message))
        except OSError: self.close()
    def reply(self, ok, message, **data): self.send({"event":"response", "ok":ok, "message":message, **data})
    def close(self):
        self.server.remove_client(self)
        try: self.sock.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        try: self.sock.close()
        except OSError: pass
    def run(self):
        self.sock.settimeout(None); buffer = b""
        try:
            while self.server.running.is_set():
                chunk = self.sock.recv(4096)
                if not chunk: break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try: self.dispatch(decode_line(line))
                    except ProtocolError as exc: self.reply(False, str(exc))
                    except Exception: LOG.exception("Client request failed"); self.reply(False, "Server could not process the request.")
        except OSError: pass
        finally: self.close()
    def dispatch(self, msg):
        action = msg["action"]
        if action == "register":
            ok, text = self.server.db.register(msg.get("username", ""), msg.get("password", "")); self.reply(ok, text); return
        if action == "login":
            ok, text = self.server.db.login(msg.get("username", ""), msg.get("password", ""))
            if ok: self.username = msg["username"].strip(); self.server.add_client(self.username, self)
            self.reply(ok, text, username=self.username, rooms=self.server.db.rooms()); return
        if action == "ping": self.reply(True, "pong"); return
        if not self.username: self.reply(False, "Please log in first."); return
        if action == "logout": self.reply(True, "Logged out."); self.close(); return
        if action == "rooms": self.reply(True, "Rooms loaded.", rooms=self.server.db.rooms()); return
        if action == "create_room":
            ok, text, room_id = self.server.db.create_room(msg.get("name", ""), self.username); self.reply(ok, text, room_id=room_id); return
        if action == "join_room":
            ok, text, room, history = self.server.db.join_room(self.username, msg.get("room_id"))
            if ok: self.current_room = room["id"]
            self.reply(ok, text, room=room, history=history); return
        if action == "chat":
            body = msg.get("body", "").strip()
            if not self.current_room: self.reply(False, "Join a room before sending a message.")
            elif not body: self.reply(False, "Message cannot be empty.")
            elif len(body) > 2000: self.reply(False, "Message is too long.")
            else:
                body = resolve_emoji(body); stamp = self.server.db.save_message(self.current_room, self.username, body)
                self.server.broadcast(self.current_room, {"event":"chat", "room_id":self.current_room, "sender":self.username, "body":body, "timestamp":stamp})
