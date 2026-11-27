"""Local development only; use a production WSGI server behind TLS for deployment."""
from wsgiref.simple_server import make_server
from Server.service import application_from_env

if __name__ == "__main__":
    with make_server("127.0.0.1", 8765, application_from_env()) as server:
        print("Shield development server on 127.0.0.1:8765")
        server.serve_forever()
