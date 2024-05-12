from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket
import json
import datetime
from pymongo import MongoClient
import threading

def connect_to_mongodb():
    client = MongoClient('mongodb://mongo:27017/')
    return client['mydatabase']

def insert_message(data, db):
    collection = db.messages
    message_data = {
        "date": datetime.datetime.now(),
        "username": data['username'],
        "message": data['message']
    }
    collection.insert_one(message_data)

class MyServer(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path in ['', '/']:
            path = '/index.html'
        if path == '/message':
            path = '/message.html'
        if path.endswith(".html") or path in ["/logo.png", "/style.css"]:
            return SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_post_data(post_data)
            if data:
                db = connect_to_mongodb()
                insert_message(data, db)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Message sent successfully")
            else:
                self.send_error(400, "Bad Request")
        else:
            self.send_error(404, "File Not Found")

def parse_post_data(post_data):
    data = post_data.decode('utf-8')
    parsed_data = parse_qs(data)
    if 'username' in parsed_data and 'message' in parsed_data:
        return {
            'username': parsed_data['username'][0],
            'message': parsed_data['message'][0]
        }
    return None

def run(server_class=HTTPServer, handler_class=MyServer, port=3001):  # Adjusted port
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print("Starting web server on port", port)
    httpd.serve_forever()

def start_socket_server(port=5001):  # Adjusted port for socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', port))
    server_socket.listen(5)
    print(f"Socket server listening on port {port}")

    while True:
        conn, addr = server_socket.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data_dict = json.loads(data.decode('utf-8'))
                db = connect_to_mongodb()
                insert_message(data_dict, db)
                conn.sendall(b'Data received and stored')

if __name__ == '__main__':
    db_thread = threading.Thread(target=lambda: run(HTTPServer, MyServer))
    socket_thread = threading.Thread(target=start_socket_server)
    db_thread.start()
    socket_thread.start()

    db_thread.join()
    socket_thread.join()
