"""Offline SSP: Python 3.10+, standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = {"port": 8765, "database": "db_polon_ssp.json", "open_browser": True}


def atomic_write(path, content):
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_database(data):
    if not isinstance(data, dict) or any(not isinstance(data.get(k), list) for k in ('panels', 'faults', 'history')):
        raise ValueError('Baza musi zawierać listy panels, faults i history.')
    for key in ('panels', 'faults', 'history'):
        if any(not isinstance(row, dict) or not isinstance(row.get('id'), str) for row in data[key]):
            raise ValueError('Nieprawidłowe rekordy: ' + key)
        ids = [row['id'] for row in data[key]]
        if len(ids) != len(set(ids)):
            raise ValueError('Powtórzone identyfikatory: ' + key)
    return data


def decode_database(raw):
    # HTA exported UTF-16; regular JSON exports use UTF-8.
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return validate_database(json.loads(raw.decode(encoding)))


def make_server(root, port):
    config_path = root / 'config.json'
    if not config_path.exists():
        atomic_write(config_path, json.dumps(DEFAULT_CONFIG, indent=2).encode())
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    filename = config.get('database', DEFAULT_CONFIG['database'])
    if not isinstance(filename, str) or '/' in filename or '\\' in filename or ':' in filename or not filename.endswith('.json') or filename.lower() == 'config.json':
        raise ValueError('database musi być nazwą pliku JSON w folderze aplikacji (inną niż config.json).')
    database = root / filename
    if database.is_symlink():
        raise ValueError('Baza nie może być dowiązaniem symbolicznym.')
    selected_port = config.get('port', 8765) if port is None else port
    if type(selected_port) is not int or not 0 <= selected_port <= 65535:
        raise ValueError('Nieprawidłowy port.')

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, content_type='application/json; charset=utf-8'):
            body = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def trusted(self, write=False):
            expected = '127.0.0.1:' + str(self.server.server_port)
            origin = self.headers.get('Origin')
            return (self.headers.get('Host') == expected
                    and (origin is None or origin == 'http://' + expected)
                    and self.headers.get('Sec-Fetch-Site') not in ('cross-site',)
                    and (not write or self.headers.get('X-SSP-Client') == 'local'))

        def current(self):
            if not database.exists():
                return None, None, None
            raw = database.read_bytes()
            return decode_database(raw), hashlib.sha256(raw).hexdigest(), raw

        def do_GET(self):
            if not self.trusted():
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            try:
                if self.path in ('/', '/index.html'):
                    return self.respond(200, (root / 'index.html').read_bytes(), 'text/html; charset=utf-8')
                if self.path == '/api/database':
                    data, revision, _ = self.current()
                    return self.respond(200, {'database': data, 'revision': revision})
                self.respond(404, {'error': 'Nie znaleziono.'})
            except (ValueError, OSError) as error:
                self.respond(500, {'error': 'Nie można odczytać bazy: ' + str(error)})

        def do_PUT(self):
            if not self.trusted(write=True):
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path != '/api/database':
                return self.respond(404, {'error': 'Nie znaleziono.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20 * 1024 * 1024:
                    return self.respond(413, {'error': 'Limit pliku wynosi 20 MB.'})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or 'revision' not in payload:
                    raise ValueError('Brak wersji bazy.')
                data = validate_database(payload.get('database'))
                _, revision, old = self.current()
                if payload['revision'] != revision:
                    return self.respond(409, {'error': 'Baza zmieniła się w innym oknie lub na dysku. Odśwież stronę.'})
                raw = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
                if old is not None:
                    atomic_write(database.with_suffix('.json.bak'), old)
                atomic_write(database, raw)
                self.respond(200, {'revision': hashlib.sha256(raw).hexdigest()})
            except (ValueError, OSError) as error:
                self.respond(400, {'error': 'Nie zapisano bazy: ' + str(error)})

    server = HTTPServer(('127.0.0.1', selected_port), Handler)
    server.timeout = 10
    return server, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    try:
        server, config = make_server(ROOT, args.port)
        url = 'http://127.0.0.1:' + str(server.server_port)
        print('SSP Polon: ' + url + '\nZostaw to okno otwarte. Ctrl+C kończy pracę.', flush=True)
        if config.get('open_browser', True) and not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (OSError, ValueError) as error:
        print('Nie można uruchomić aplikacji: ' + str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
