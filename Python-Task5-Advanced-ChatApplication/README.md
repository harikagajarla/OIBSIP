# Advanced Chat Application

**Gajarla Harika — Python Programming Internship — Task 5: Advanced Chat Application**

A standard-library Python 3.12+ desktop chat app using Tkinter, raw TCP sockets, threads, newline-delimited JSON, and SQLite. It supports secure account registration/login, multiple rooms, persistent recent history, timestamps, emoji shortcodes, and a focus-aware in-app notification banner.

## Architecture and folders

`client/` contains the socket client and Tkinter interface. `server/` contains the threaded TCP server. `common/` provides framing, emoji, and security helpers. `database/` is the SQLite persistence layer; its generated `chat.db` is intentionally ignored. `tests/` includes core and two-client socket integration tests. `screenshots/` documents where demonstration images belong.

## Install and run

No third-party packages are required. Optionally create a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python run_server.py
```

In **two other terminals** in this project folder, run `python run_client.py` twice. Register two accounts, log both in, create a room in one client, join it in both clients, then exchange messages. Join/switching a room loads its last 50 messages chronologically. Use `:)`, `:(`, `:D`, `;)`, `<3`, `:smile:`, `:heart:`, `:thumbsup:`, or `:fire:`; the server saves resolved emoji.

## SQLite schema

`users(id, username, salt, password_hash, created_at)`, `rooms(id, name, created_by, created_at)`, `memberships(user_id, room_id)`, and `messages(id, room_id, sender, body, timestamp)`. All queries are parameterized and access is protected by a lock.

## Security and limits

Passwords are salted with random 16-byte salts and hashed using PBKDF2-HMAC-SHA256 (310,000 iterations); plaintext passwords are not stored. This app **does not encrypt network traffic**: raw TCP has no TLS and this is not end-to-end encrypted. Run it on trusted networks only. A future version could add TLS, rate limiting, password-reset flows, richer room permissions, and automated GUI testing.

## Testing

```powershell
python -m unittest discover -s tests -v
python -m compileall -q common database server client run_server.py run_client.py
```

The integration suite starts an isolated server on a temporary port, registers/logs in two independent TCP clients, creates and joins a room, verifies live room-only delivery, emoji conversion, persisted history, malformed JSON handling, and login enforcement. GUI imports are tested separately where a desktop display is available; launching `run_client.py` is the manual visual verification step.

## Screenshots

Place real demonstration screenshots in `screenshots/`: login, two clients in a shared room, history after rejoin, and the unfocused-window notification banner. The project deliberately includes no fabricated screenshots.
