import unittest
import threading
import time
import json
import urllib.request
import urllib.error
import os
import sys

# Ensure parent directory is in path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import app
import src.app as app_module

class TestNLPAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure app for testing
        app.config['TESTING'] = True
        
        # Start Flask app on a test port (5001) in a background thread
        cls.server_thread = threading.Thread(
            target=lambda: app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
        )
        cls.server_thread.daemon = True
        cls.server_thread.start()
        
        # Allow the background server a moment to spin up
        time.sleep(1)
        
        cls.base_url = 'http://127.0.0.1:5001'
        cls.api_token = 'test_token_secret_123'
        
        # Override the API token inside the running module for predictable test execution
        app_module.API_TOKEN = cls.api_token

    def send_post(self, path, body, headers=None, expected_status=200):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode('utf-8')
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)
            
        req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, expected_status)
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, expected_status)
            return json.loads(e.read().decode('utf-8'))

    def test_missing_api_key(self):
        """Should fail with 401 if authentication header is missing."""
        body = {"text": "Hello world"}
        res = self.send_post("/api/analyze", body, headers={}, expected_status=401)
        self.assertIn("error", res)
        self.assertEqual(res["error"], "API Key is missing.")

    def test_invalid_api_key(self):
        """Should fail with 401 if authentication header is incorrect."""
        body = {"text": "Hello world"}
        headers = {"X-APPIKS-NLP-KEY": "wrong_key_123"}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=401)
        self.assertIn("error", res)
        self.assertEqual(res["error"], "Invalid API Key.")

    def test_missing_text_field(self):
        """Should fail with 400 if text field is missing."""
        body = {}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=400)
        self.assertIn("error", res)
        self.assertEqual(res["error"], "Missing 'text' field in request body.")

    def test_invalid_text_type(self):
        """Should fail with 400 if text field is not a string."""
        body = {"text": 12345}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=400)
        self.assertIn("error", res)
        self.assertEqual(res["error"], "'text' field must be a string.")

    def test_no_trigger_case(self):
        """Should classify academic complaint as 'No Trigger' with weight 1."""
        body = {"text": "Hari ini capek banget belajar matematika"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "No Trigger")
        self.assertEqual(res["total_score"], 1)
        
        # Check matched keywords structure
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "capek")
        self.assertEqual(res["matched_keywords"][0]["weight"], 1)
        self.assertEqual(res["matched_keywords"][0]["zone"], "Yellow")

    def test_yellow_zone_case(self):
        """Should classify loneliness as 'Yellow Zone' with score 4."""
        body = {"text": "Aku merasa sangat kesepian dan kosong"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Yellow Zone")
        self.assertEqual(res["total_score"], 4)
        
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "kosong")

    def test_red_zone_explicit_override(self):
        """Should classify suicide mention as 'Red Zone' due to explicit high-weight keyword override."""
        body = {"text": "Aku ingin akhiri hidup ini"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Red Zone")
        self.assertEqual(res["total_score"], 9)
        self.assertEqual(res["matched_keywords"][0]["stem"], "akhir")

    def test_red_zone_score_override(self):
        """Should classify accumulative yellow keywords as 'Red Zone' if score >= 10."""
        # capek (1) + guna (5) + sendiri (3) + co-occurrence bonus capek/guna (2) = 11
        body = {"text": "Capek, ga ada gunanya hidup gini, sendirian terus"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Red Zone")
        self.assertEqual(res["total_score"], 11)

if __name__ == '__main__':
    unittest.main()
