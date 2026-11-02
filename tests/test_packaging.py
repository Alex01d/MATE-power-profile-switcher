"""Exercise installation and removal in an isolated staging directory."""

import ast
import configparser
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path('opt/mate-power-profile-switcher')
REGISTRATIONS = (
    Path('usr/share/dbus-1/services/org.mate.panel.applet.LocalPowerProfilesAppletFactory.service'),
    Path('usr/share/mate-panel/applets/org.mate.panel.LocalPowerProfilesApplet.mate-panel-applet'),
)


class PackagingTests(unittest.TestCase):
    def run_script(self, name, stage):
        return subprocess.run(
            ['bash', str(ROOT / name)], check=True, capture_output=True, text=True,
            env={**os.environ, 'DESTDIR': str(stage)},
        )

    def test_install_update_and_remove_preserve_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            self.run_script('install.sh', stage)
            runtime = stage / RUNTIME
            self.assertEqual((runtime / 'power-profile-switcher.py').read_bytes(),
                             (ROOT / 'power-profile-switcher.py').read_bytes())
            self.assertEqual((runtime / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
            for name in ('power-profile-switcher.py', 'panel-item.py', 'install.sh',
                         'uninstall.sh', 'configure-tuned.sh'):
                self.assertEqual((runtime / name).stat().st_mode & 0o777, 0o755)
            for registration in REGISTRATIONS:
                config = configparser.ConfigParser()
                config.read(stage / registration)
                key = ('D-BUS Service', 'Exec') if registration.suffix == '.service' else ('Applet Factory', 'Location')
                self.assertEqual(config[key[0]][key[1]],
                                 '/opt/mate-power-profile-switcher/power-profile-switcher.py')
            extra = runtime / 'local-notes.txt'
            extra.write_text('Keep this local file.\n')
            self.run_script('install.sh', stage)
            self.assertTrue(extra.exists())
            self.run_script('uninstall.sh', stage)
            self.assertEqual(extra.read_text(), 'Keep this local file.\n')
            self.assertFalse((runtime / 'power-profile-switcher.py').exists())
            for registration in REGISTRATIONS:
                self.assertFalse((stage / registration).exists())

    def test_clean_uninstall_removes_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            self.run_script('install.sh', stage)
            self.run_script('uninstall.sh', stage)
            self.assertFalse((stage / RUNTIME).exists())

    def test_relative_staging_path_is_rejected(self):
        for name in ('install.sh', 'uninstall.sh'):
            result = subprocess.run(['bash', str(ROOT / name)],
                                    env={**os.environ, 'DESTDIR': 'relative'},
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('absolute', result.stderr)

    def test_python_sources_and_embedded_scripts_parse(self):
        for source in ROOT.glob('*.py'):
            ast.parse(source.read_text(), filename=str(source))
        for script in ROOT.glob('*.sh'):
            for block in re.findall(r"<<'PY'\n(.*?)\nPY", script.read_text(), re.S):
                ast.parse(block, filename=str(script))

    def test_tuned_example_enables_firmware_max_power_and_boost(self):
        config = configparser.ConfigParser()
        config.read(ROOT / 'examples/tuned/legion-max-power/tuned.conf')
        self.assertEqual(config['acpi']['platform_profile'], 'max-power')
        self.assertEqual(config['cpu']['boost'], '1')
        self.assertEqual(config['cpu']['energy_performance_preference'], 'performance')


if __name__ == '__main__':
    unittest.main()
