import logging
from server.chat_server import ChatServer
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server=ChatServer(); print(f"Server listening on {server.host}:{server.port}")
    try: server.start()
    except KeyboardInterrupt: pass
    finally: server.stop()
