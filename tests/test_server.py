import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
import server


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'index.html').write_text('SSP')
        self.server, _ = server.make_server(self.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method='GET', data=None, path='/api/database', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, None if data is None else json.dumps(data),
                           headers or {'X-SSP-Client': 'local'})
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body)

    def test_save_reload_backup_and_conflict(self):
        self.assertEqual(self.request(), (200, {'database': None, 'revision': None}))
        db = {'panels': [], 'faults': [], 'history': []}
        status, saved = self.request('PUT', {'revision': None, 'database': db})
        self.assertEqual(status, 200)
        self.assertEqual(self.request()[1]['database'], db)
        db['panels'].append({'id': 'CSP-01', 'location': 'Łódź'})
        self.assertEqual(self.request('PUT', {'revision': saved['revision'], 'database': db})[0], 200)
        self.assertEqual(json.loads((self.root / 'db_polon_ssp.json.bak').read_text())['panels'], [])
        self.assertEqual(self.request('PUT', {'revision': saved['revision'], 'database': db})[0], 409)
        self.assertEqual(self.request()[1]['database'], db)

    def test_corruption_is_not_overwritten(self):
        path = self.root / 'db_polon_ssp.json'
        path.write_text('broken')
        self.assertEqual(self.request()[0], 500)
        self.assertEqual(self.request('PUT', {'revision': None, 'database': {'panels': [], 'faults': [], 'history': []}})[0], 400)
        self.assertEqual(path.read_text(), 'broken')

    def test_private_files_and_cross_origin(self):
        self.assertEqual(self.request(path='/config.json')[0], 404)
        self.assertEqual(self.request(path='/db_polon_ssp.json')[0], 404)
        self.assertEqual(self.request(headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('PUT', {}, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('PUT', {'revision': None, 'database': {} })[0], 400)

    def test_hta_utf16(self):
        db = {'panels': [], 'faults': [], 'history': []}
        (self.root / 'db_polon_ssp.json').write_bytes(json.dumps(db).encode('utf-16'))
        self.assertEqual(self.request()[1]['database'], db)


if __name__ == '__main__':
    unittest.main()
