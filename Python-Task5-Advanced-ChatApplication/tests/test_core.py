import tempfile, unittest
from pathlib import Path
from common.emoji import resolve_emoji
from common.protocol import ProtocolError, decode_line, encode
from common.security import hash_password, verify_password
from database.storage import ChatDatabase

class CoreTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.db=ChatDatabase(Path(self.tmp.name)/"test.db")
    def tearDown(self): self.db.close(); self.tmp.cleanup()
    def test_password_hashing_and_verification(self):
        salt,digest=hash_password("secret7"); self.assertNotEqual(digest,"secret7"); self.assertTrue(verify_password("secret7",salt,digest)); self.assertFalse(verify_password("wrong",salt,digest))
    def test_registration_login_and_duplicate(self):
        self.assertTrue(self.db.register("alice","secret7")[0]); self.assertFalse(self.db.register("alice","secret7")[0]); self.assertTrue(self.db.login("alice","secret7")[0]); self.assertFalse(self.db.login("alice","wrong")[0])
    def test_rooms_membership_and_history(self):
        self.db.register("alice","secret7"); ok,_,room_id=self.db.create_room("Study","alice"); self.assertTrue(ok); ok,_,room,history=self.db.join_room("alice",room_id); self.assertTrue(ok); self.assertEqual(history,[]); stamp=self.db.save_message(room["id"],"alice","hello"); self.assertIn("T",stamp); self.assertEqual(self.db.join_room("alice",room_id)[3][0]["body"],"hello")
    def test_emoji_and_protocol(self):
        self.assertEqual(resolve_emoji("Hi :) :fire: <3"),"Hi 🙂 🔥 ❤️"); self.assertEqual(decode_line(encode({"action":"ping"})),{"action":"ping"});
        with self.assertRaises(ProtocolError): decode_line(b'{"action":"bad"}')
        with self.assertRaises(ProtocolError): decode_line(b'not json')
