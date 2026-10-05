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

    def test_no_trigger_academic_case(self):
        """Should classify academic complaint below threshold (score < 5)."""
        body = {"text": "Hari ini capek banget belajar matematika"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "No Trigger")
        self.assertEqual(res["total_score"], 3)
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "capek")

    def test_yellow_zone_case(self):
        """Should classify 'ga ada gunanya lagi' as 'Yellow Zone' with score 6.5."""
        body = {"text": "Aku ga ada gunanya lagi"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Yellow Zone")
        self.assertEqual(res["total_score"], 6.5)
        
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "ada guna")
        self.assertEqual(res["matched_keywords"][0]["weight"], 6.5)
        self.assertEqual(res["matched_keywords"][0]["zone"], "Yellow")

    def test_overlap_suppression_tidak_ada_gunanya(self):
        """Should count 'tidak ada gunanya' as 6.5 (suppressing 'guna')."""
        body = {"text": "tidak ada gunanya"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["total_score"], 6.5)
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "ada guna")

    def test_overlap_suppression_capek_hidup(self):
        """Should count 'capek hidup' as 7 (suppressing 'capek')."""
        body = {"text": "capek hidup"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["total_score"], 7)
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "capek hidup")

    def test_overlap_suppression_lelah_hidup(self):
        """Should count 'lelah hidup' as 6.5 (suppressing 'lelah')."""
        body = {"text": "lelah hidup"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["total_score"], 6.5)
        self.assertEqual(len(res["matched_keywords"]), 1)
        self.assertEqual(res["matched_keywords"][0]["stem"], "lelah hidup")

    def test_unbounded_repetition_capek_capek(self):
        """Should count 'capek capek' as 6 (3 + 3) across distinct token positions."""
        body = {"text": "capek capek"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["total_score"], 6)
        self.assertEqual(len(res["matched_keywords"]), 2)
        self.assertEqual(res["matched_keywords"][0]["stem"], "capek")
        self.assertEqual(res["matched_keywords"][1]["stem"], "capek")

    def test_red_zone_explicit_override(self):
        """Should classify suicide mention as 'Red Zone' due to explicit Red keyword override."""
        body = {"text": "Aku ingin akhiri hidup ini"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Red Zone")
        self.assertEqual(res["total_score"], 10)
        self.assertEqual(res["matched_keywords"][0]["stem"], "akhir hidup")
        self.assertEqual(res["matched_keywords"][0]["zone"], "Red")

    def test_red_zone_score_accumulation(self):
        """Should classify accumulative yellow keywords as 'Red Zone' if score >= 15."""
        body = {"text": "Capek hidup, lelah hidup, bosan hidup terus"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "Red Zone")
        self.assertEqual(res["total_score"], 20.5)

    def test_negation_handling_skip(self):
        """Should skip Red Zone trigger when negated ('Aku tidak mau bunuh diri')."""
        body = {"text": "Aku tidak mau bunuh diri"}
        headers = {"X-APPIKS-NLP-KEY": self.api_token}
        res = self.send_post("/api/analyze", body, headers=headers, expected_status=200)
        
        self.assertEqual(res["zone_status"], "No Trigger")
        self.assertEqual(res["total_score"], 0)
        self.assertEqual(len(res["matched_keywords"]), 0)

    def test_swagger_html_unauthenticated(self):
        """Should return Swagger UI HTML page at /docs without requiring an API key."""
        url = f"{self.base_url}/docs"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            html = response.read().decode('utf-8')
            self.assertIn("swagger-ui", html)
            self.assertIn("SwaggerUIBundle", html)

    def test_swagger_json_unauthenticated(self):
        """Should return Swagger OpenAPI spec JSON at /docs/api.json without requiring an API key."""
        url = f"{self.base_url}/docs/api.json"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            spec = json.loads(response.read().decode('utf-8'))
            self.assertEqual(spec["openapi"], "3.0.0")
            self.assertEqual(spec["info"]["title"], "APPIKS NLP Mental Distress Classifier API")

if __name__ == '__main__':
    unittest.main()
