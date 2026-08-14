import time
import unittest
import json
import urllib.request
import urllib.parse
from madgrav.kernel import Kernel
from madgrav.network.web_server import WebServer


class TestWebRemoteController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = Kernel("MadGrav", "0.0.0-testing", "MadGrav", ignore_settings=True)
        cls.kernel.root.device = "dummy"
        cls.server_module = WebServer(cls.kernel.root, "web_server_test", port=0)
        # Wait for thread to bind port
        for _ in range(50):
            if cls.server_module.httpd is not None and hasattr(cls.server_module.httpd, "server_address"):
                break
            time.sleep(0.05)
        cls.port = cls.server_module.actual_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server_module.stop_server()

    def test_get_mobile_remote_html(self):
        req = urllib.request.Request(f"{self.base_url}/")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("MadGrav", content)
            self.assertIn("Télécommande", content)
            self.assertIn("d-pad", content.lower())

    def test_api_status(self):
        req = urllib.request.Request(f"{self.base_url}/api/status")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("status", data)
            self.assertIn("x", data)
            self.assertIn("y", data)

    def test_api_jog_and_control(self):
        token = self.server_module.csrf_token
        # Jog X +10
        jog_data = json.dumps({"axis": "X", "distance": 10.0, "csrf_token": token}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/jog",
            data=jog_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res.get("success"))

        # Control Home
        ctrl_data = json.dumps({"action": "origin", "csrf_token": token}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/control",
            data=ctrl_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res.get("success"))


if __name__ == "__main__":
    unittest.main()
