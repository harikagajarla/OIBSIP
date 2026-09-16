import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from common.security import hash_password, verify_password

class ChatDatabase:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._schema()

    def _schema(self):
        with self.lock, self.connection:
            self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memberships (user_id INTEGER NOT NULL REFERENCES users(id), room_id INTEGER NOT NULL REFERENCES rooms(id), PRIMARY KEY(user_id, room_id));
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL REFERENCES rooms(id), sender TEXT NOT NULL, body TEXT NOT NULL, timestamp TEXT NOT NULL);
            """)
            self.connection.execute("INSERT OR IGNORE INTO rooms(name, created_by, created_at) VALUES (?, ?, ?)", ("Lobby", "system", self.now()))

    @staticmethod
    def now(): return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    def close(self):
        with self.lock: self.connection.close()
    def register(self, username, password):
        username = username.strip()
        if not username or len(username) > 30 or not username.replace("_", "").isalnum(): return False, "Use 1-30 letters, numbers, or underscores."
        try: salt, digest = hash_password(password)
        except ValueError as exc: return False, str(exc)
        try:
            with self.lock, self.connection: self.connection.execute("INSERT INTO users(username,salt,password_hash,created_at) VALUES(?,?,?,?)", (username, salt, digest, self.now()))
            return True, "Registration successful."
        except sqlite3.IntegrityError: return False, "That username is already registered."
        except sqlite3.Error: return False, "Database error while registering."
    def login(self, username, password):
        with self.lock:
            row = self.connection.execute("SELECT salt,password_hash FROM users WHERE username=?", (username.strip(),)).fetchone()
        return (True, "Login successful.") if row and verify_password(password, row["salt"], row["password_hash"]) else (False, "Invalid username or password.")
    def rooms(self):
        with self.lock: return [dict(r) for r in self.connection.execute("SELECT id,name,created_by FROM rooms ORDER BY name")]
    def create_room(self, name, creator):
        name = name.strip()
        if not name or len(name) > 40: return False, "Room name must contain 1-40 characters.", None
        try:
            with self.lock, self.connection:
                cur = self.connection.execute("INSERT INTO rooms(name,created_by,created_at) VALUES(?,?,?)", (name, creator, self.now()))
            return True, "Room created.", cur.lastrowid
        except sqlite3.IntegrityError: return False, "A room with that name already exists.", None
    def join_room(self, username, room_id):
        with self.lock:
            room = self.connection.execute("SELECT id,name FROM rooms WHERE id=?", (room_id,)).fetchone()
            user = self.connection.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if not room or not user: return False, "Invalid room.", None, []
            with self.connection: self.connection.execute("INSERT OR IGNORE INTO memberships(user_id,room_id) VALUES(?,?)", (user["id"], room_id))
            history = [dict(r) for r in self.connection.execute("SELECT sender,body,timestamp FROM messages WHERE room_id=? ORDER BY id DESC LIMIT 50", (room_id,))][::-1]
        return True, "Joined room.", dict(room), history
    def save_message(self, room_id, sender, body):
        stamp = self.now()
        with self.lock, self.connection: self.connection.execute("INSERT INTO messages(room_id,sender,body,timestamp) VALUES(?,?,?,?)", (room_id, sender, body, stamp))
        return stamp
    def room_members(self, room_id):
        with self.lock: return [r["username"] for r in self.connection.execute("SELECT u.username FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.room_id=?", (room_id,))]
