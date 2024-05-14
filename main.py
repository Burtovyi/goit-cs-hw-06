import logging
import mimetypes
import socket
from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from multiprocessing import Process
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime


URI_DB = "mongodb://mongodb:27017"
BASE_DIR = Path(__file__).parent
CHUNK_SIZE = 1024
HTTP_PORT = 3000
SOCKET_PORT = 5000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        router = urlparse(self.path).path
        match router:
            case '/':
                self.send_html('index.html')
            case '/message.html':
                self.send_html('message.html')
            case _:
                file = BASE_DIR.joinpath(router[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)
        
    def do_POST(self):
        size = int(self.headers["Content-Length"])
        data = self.rfile.read(size)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
            client_socket.close()
        except socket.error:
            logging.error("Failed to send data")
            
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        filepath = BASE_DIR / filename
        try:
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        except FileNotFoundError:
            logging.error(f"File not found: {filepath}")
            self.send_error(404, "File not found")

    def send_static(self, file):
        self.send_response(200)
        mimetype = mimetypes.guess_type(file)[0] or "text/plain"
        self.send_header("Content-type", mimetype)
        self.end_headers()
        try:
            with open(file, 'rb') as f:
                self.wfile.write(f.read())
        except FileNotFoundError:
            logging.error(f"File not found: {file}")
            self.send_error(404, "File not found")


def save_to_db(data):
    client = MongoClient(URI_DB, server_api=ServerApi('1'))
    db = client.homework
    try:
        data = unquote_plus(data)
        parse_data = dict([i.split("=") for i in data.split("&")])
        parse_data["date"] = datetime.now()
        db.messages.insert_one(parse_data)
    except Exception as e:
        logging.error(e)
    finally:
        client.close()
    
def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), MyServer)
    try:
        logging.info(f"Server started: http://{HTTP_HOST}:{HTTP_PORT}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Server stopped")
        httpd.server_close()
    
def run_socket_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Server started: socket://{SOCKET_HOST}:{SOCKET_PORT}")
    try:
        while True:
            data, addr = s.recvfrom(CHUNK_SIZE)
            logging.info(f"Received from {addr}: {data.decode()}")
            save_to_db(data.decode())
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Server socket stopped")
        s.close()
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(processName)s - %(message)s")
    http_process = Process(target=run_http_server, name="HTTP_Server")
    socket_process = Process(target=run_socket_server, name="SOCKET_Server")
    
    http_process.start()
    socket_process.start()
    
    http_process.join()
    socket_process.join()
