"""build/patches/y2dj-storage-guard.patch: Rockbox never starts while its home on
internal storage is unavailable.

After a CDJ session, Android restarted the START_STICKY Rockbox service while
the Y2's internal storage was still shared over USB. Rockbox found no
config.cfg, ran on default settings and began saving them over the real ones.

The helper is compiled from the patch against a stand-in android.os.Environment
(needs a JDK; skipped otherwise). The guard's placement is checked statically.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT
from test_catalog_paths import added, file_sections

PATCH = os.path.join(ROOT, 'build', 'patches', 'y2dj-storage-guard.patch')
SERVICE = 'android/src/org/rockbox/RockboxService.java'

ENVIRONMENT = '''package android.os;
public class Environment {
    public static final String MEDIA_MOUNTED = "mounted";
    public static String state = MEDIA_MOUNTED;
    public static String getExternalStorageState() { return state; }
}
'''

HARNESS = '''import android.os.Environment;
import java.io.File;

public class GuardTest {
%s
    static int failures = 0;
    static void check(boolean ok, String what) {
        System.out.println((ok ? "ok   " : "FAIL ") + what);
        if (!ok) failures++;
    }

    public static void main(String[] args) {
        String[][] cases = {
            {"mounted", "true"}, {"shared", "false"}, {"checking", "false"},
            {"unmounted", "false"}, {"removed", "false"}, {"bad_removal", "false"},
        };
        for (String[] c : cases) {
            Environment.state = c[0];
            check(rockboxHomeReady() == Boolean.parseBoolean(c[1]),
                  "state " + c[0] + " -> " + c[1]);
        }
        System.out.println(failures + " failure(s)");
        System.exit(failures == 0 ? 0 : 1);
    }
}
'''


def service_lines():
    with open(PATCH) as f:
        return file_sections(f.read())[SERVICE]


def javac_works():
    if shutil.which('javac') is None or shutil.which('java') is None:
        return False
    return subprocess.run(['javac', '-version'], capture_output=True).returncode == 0


class StorageGuardPlacementTest(unittest.TestCase):
    def setUp(self):
        self.text = '\n'.join(service_lines())

    def test_guard_runs_before_rockbox_starts(self):
        guard = self.text.index('+        if (!rockbox_running && !rockboxHomeReady())')
        start = self.text.index('         if (!rockbox_running)\n             startService();')
        self.assertLess(guard, start)

    def test_guard_stops_the_service_and_logs(self):
        block = added(service_lines(), 'if (!rockbox_running && !rockboxHomeReady())', 'return;')
        self.assertIn('stopSelf();', block)
        self.assertIn('RockboxService:deny start, internal storage not ready', block)
        self.assertLess(block.index('stopSelf();'), block.index('return;'))

    def test_checks_rockbox_home_on_internal_storage(self):
        helper = added(service_lines(), 'static boolean rockboxHomeReady()',
                       'home.canWrite();') + '    }\n'
        self.assertIn('new File("/storage/sdcard0")', helper)
        self.assertIn('Environment.MEDIA_MOUNTED.equals(Environment.getExternalStorageState())',
                      helper)


@unittest.skipUnless(javac_works(), 'needs a JDK')
class StorageGuardBehaviourTest(unittest.TestCase):
    def test_only_mounted_storage_lets_rockbox_start(self):
        helper = added(service_lines(), 'static boolean rockboxHomeReady()',
                       'home.canWrite();') + '    }\n'
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'android', 'os'))
            with open(os.path.join(tmp, 'android', 'os', 'Environment.java'), 'w') as f:
                f.write(ENVIRONMENT)
            # The stand-in for /storage/sdcard0 must be a writable directory.
            home = os.path.join(tmp, 'sdcard0')
            os.makedirs(home)
            with open(os.path.join(tmp, 'GuardTest.java'), 'w') as f:
                f.write(HARNESS % helper.replace('/storage/sdcard0', home))
            r = subprocess.run(['javac', '-d', tmp, os.path.join(tmp, 'android', 'os', 'Environment.java'),
                                os.path.join(tmp, 'GuardTest.java')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run(['java', '-cp', tmp, 'GuardTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('0 failure(s)', r.stdout)

            # And no home directory means no start, even when mounted.
            os.rmdir(home)
            r = subprocess.run(['java', '-cp', tmp, 'GuardTest'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('FAIL state mounted -> true', r.stdout)


if __name__ == '__main__':
    unittest.main()
