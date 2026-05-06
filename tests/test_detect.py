from __future__ import annotations
import unittest
from unittest.mock import MagicMock
from qatrackplus_manager.config.detect import detect_qatrack_version, detect_db_from_settings
from qatrackplus_manager.transport.base import Transport

class TestDetect(unittest.TestCase):
    def setUp(self):
        self.transport = MagicMock(spec=Transport)

    def test_detect_v4_layout(self):
        self.transport.file_exists.side_effect = lambda p: p.endswith("settings.py")
        self.transport.read_file.return_value = "from .local_settings import *"
        
        major, ls_file, dj_mod = detect_qatrack_version(self.transport, "/opt/qatrack")
        
        self.assertEqual(major, 4)
        self.assertIn("local_settings.py", ls_file)
        self.assertEqual(dj_mod, "qatrack.settings")

    def test_detect_v3_layout(self):
        self.transport.file_exists.return_value = False
        self.transport.dir_exists.side_effect = lambda p: p.endswith("settings")
        
        major, ls_file, dj_mod = detect_qatrack_version(self.transport, "/opt/qatrack")
        
        self.assertEqual(major, 3)
        self.assertIn("settings/local_settings.py", ls_file)
        self.assertEqual(dj_mod, "qatrack.settings.local_settings")

    def test_detect_db_postgresql(self):
        self.transport.file_exists.return_value = True
        self.transport.read_file.return_value = "'ENGINE': 'django.db.backends.postgresql',"
        
        config = detect_db_from_settings(self.transport, "/opt/qatrack/local_settings.py")
        self.assertEqual(config['db_type'], "postgresql")

if __name__ == "__main__":
    unittest.main()
