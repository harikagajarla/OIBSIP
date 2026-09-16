import json, socket, tempfile, threading, time, unittest
from pathlib import Path
from server.chat_server import ChatServer

class WireClient:
    def __init__(self, port): self.s=socket.create_connection(("127.0.0.1",port)); self.buffer=b""
    def send(self, **message): self.s.sendall((json.dumps(message)+"\n").encode())
    def recv(self):
        while b"\n" not in self.buffer: self.buffer+=self.s.recv(4096)
        line,self.buffer=self.buffer.split(b"\n",1); return json.loads(line)
    def close(self): self.s.close()

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.server=ChatServer(port=0,database_path=Path(self.tmp.name)/"chat.db"); self.thread=threading.Thread(target=self.server.start,daemon=True); self.thread.start()
        for _ in range(50):
            if self.server.running.is_set(): break
            time.sleep(.02)
    def tearDown(self): self.server.stop(); self.thread.join(1); self.tmp.cleanup()
    def request(self,c,**payload): c.send(**payload); return c.recv()
    def test_two_clients_room_message_and_history(self):
        a,b=WireClient(self.server.port),WireClient(self.server.port)
        try:
            self.assertTrue(self.request(a,action="register",username="alice",password="secret7")["ok"]); self.assertTrue(self.request(b,action="register",username="bob",password="secret7")["ok"])
            self.assertTrue(self.request(a,action="login",username="alice",password="secret7")["ok"]); self.assertTrue(self.request(b,action="login",username="bob",password="secret7")["ok"])
            created=self.request(a,action="create_room",name="Study"); self.assertTrue(created["ok"]); rid=created["room_id"]
            self.assertTrue(self.request(a,action="join_room",room_id=rid)["ok"]); self.assertTrue(self.request(b,action="join_room",room_id=rid)["ok"])
            a.send(action="chat",body="Hello :) :fire:"); ma,mb=a.recv(),b.recv(); self.assertEqual(ma["body"],"Hello 🙂 🔥"); self.assertEqual(mb["body"],"Hello 🙂 🔥")
            history=self.request(b,action="join_room",room_id=rid)["history"]; self.assertEqual(history[-1]["body"],"Hello 🙂 🔥")
        finally: a.close(); b.close()
    def test_malformed_and_requires_login(self):
        c=WireClient(self.server.port)
        try:
            c.s.sendall(b"broken\n"); self.assertFalse(c.recv()["ok"]); self.assertFalse(self.request(c,action="rooms")["ok"])
        finally: c.close()
