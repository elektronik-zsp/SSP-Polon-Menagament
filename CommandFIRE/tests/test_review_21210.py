"""Regression tests for the 2.12.10 review; DPAPI is mocked on Linux."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import cf_crypto

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class ReviewTests(unittest.TestCase):
    def test_partial_protocol_reference_and_full_validation(self):
        data = copy.deepcopy(server.EMPTY_DB)
        data['panels'] = [{'id': 'C1'}]
        data['faults'] = [{'id': 'F1', 'panelId': 'C1', 'sourceProtocolId': 'H1'}]
        server.validate_database(copy.deepcopy(data), partial=True)
        with self.assertRaisesRegex(ValueError, 'źródłowy'):
            server.validate_database(copy.deepcopy(data))
        data['history'] = [{'id': 'H1', 'panelId': 'C2'}]
        data['panels'].append({'id': 'C2'})
        with self.assertRaisesRegex(ValueError, 'źródłowy'):
            server.validate_database(data, partial=True)

    def test_admin_setup_preserves_encryption_and_backup(self):
        admin = module('utworz_admina')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); key = b'k' * 32
            (root/'config.json').write_text(json.dumps({'database': 'service.cfdb'}))
            (root/'cfdb-key.dpapi').write_bytes(b'wrapped')
            original = cf_crypto.encrypt(server.encode(copy.deepcopy(server.EMPTY_DB)), key)
            (root/'service.cfdb').write_bytes(original)
            with patch.object(admin, 'ROOT', root), patch('cf_crypto.unprotect_windows', return_value=key), patch('builtins.input', side_effect=['admin','Test Administrator']), patch('getpass.getpass', return_value='TestPassword123!'):
                admin.main()
            updated = (root/'service.cfdb').read_bytes()
            self.assertTrue(updated.startswith(cf_crypto.MAGIC))
            self.assertEqual(server.decode_database(cf_crypto.decrypt(updated,key))['users'][0]['username'],'admin')
            self.assertEqual((root/'service.cfdb.przed-kontami.bak').read_bytes(),original)

    def provision(self, root):
        return {'action':'new','path':str(root/'service.cfdb'),'admin':{'username':'admin','display':'Test Administrator','password_hex':'TestPassword123!'.encode().hex()}}

    def test_dpapi_failure_does_not_create_database(self):
        setup=module('konfigurator_cfdb')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(setup,'ROOT',root), patch.object(setup,'protect_windows',side_effect=OSError('DPAPI unavailable')):
                with self.assertRaisesRegex(OSError,'DPAPI'):setup.run(self.provision(root))
            self.assertFalse((root/'service.cfdb').exists())
            self.assertFalse((root/'cfdb-key.dpapi').exists())

    def test_invalid_config_is_detected_before_creation(self):
        setup=module('konfigurator_cfdb')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config.json').write_text('[]')
            with patch.object(setup,'ROOT',root):
                with self.assertRaises(ValueError):setup.run(self.provision(root))
            self.assertFalse((root/'service.cfdb').exists())

    def test_database_write_failure_keeps_recovery_key(self):
        setup=module('konfigurator_cfdb')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);actual=setup.atomic_write
            def write(path,data):
                if path.suffix=='.cfdb':raise OSError('Disk unavailable')
                actual(path,data)
            with patch.object(setup,'ROOT',root), patch.object(setup,'protect_windows',side_effect=lambda k:b'wrapped'+k), patch.object(setup,'atomic_write',side_effect=write):
                with self.assertRaisesRegex(OSError,'Disk unavailable'):setup.run(self.provision(root))
            self.assertEqual(len((root/'cfdb-key.dpapi').read_bytes()),39)

    def test_new_and_join_use_same_database_key(self):
        setup=module('konfigurator_cfdb')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(setup,'ROOT',root), patch.object(setup,'protect_windows',side_effect=lambda k:b'wrapped'+k), patch.object(setup,'unprotect_windows',side_effect=lambda v:v[7:]):
                result=setup.run(self.provision(root))
                raw=(root/'service.cfdb').read_bytes()
                key=bytes.fromhex(result['recovery'])
                self.assertEqual(server.decode_database(cf_crypto.decrypt(raw,key))['users'][0]['username'],'admin')
                setup.run({'action':'join','path':str(root/'service.cfdb'),'key':key.hex()})
                self.assertEqual((root/'service.cfdb').read_bytes(),raw)

if __name__=='__main__':unittest.main()
