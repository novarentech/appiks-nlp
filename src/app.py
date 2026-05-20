import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.classifier import classify_weighted

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load API configuration
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    logger.warning("API_TOKEN is not set in environment variables. Requests might fail authentication if no token is configured.")

@app.before_request
def authenticate_request():
    """
    Authenticate request using the custom header X-APPIKS-NLP-KEY.
    """
    # Expose a health check endpoint without authentication
    if request.path == "/health" or request.path == "/":
        return

    client_key = request.headers.get("X-APPIKS-NLP-KEY")
    
    if not client_key:
        logger.warning(f"Authentication failed: Missing header from IP {request.remote_addr}")
        return jsonify({"error": "API Key is missing."}), 401
        
    if client_key != API_TOKEN:
        logger.warning(f"Authentication failed: Invalid key from IP {request.remote_addr}")
        return jsonify({"error": "Invalid API Key."}), 401

@app.route("/health", methods=["GET"])
def health_check():
    """
    Basic health check endpoint.
    """
    return jsonify({"status": "healthy"}), 200

@app.route("/api/analyze", methods=["POST"])
def analyze_text():
    """
    Endpoint to analyze mental distress level in Indonesian text.
    Expects JSON body: {"text": "string"}
    Returns JSON: {"zone_status": "string", "total_score": int, "matched_keywords": []}
    """
    if not request.is_json:
        return jsonify({"error": "Request content type must be application/json."}), 400

    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in request body."}), 400

    text = data["text"]
    if not isinstance(text, str):
        return jsonify({"error": "'text' field must be a string."}), 400

    try:
        zone_status, matched_keywords, total_score, _ = classify_weighted(text)
        
        # Structure the response precisely according to the spec:
        # {"zone_status": "string", "total_score": int, "matched_keywords": []}
        response = {
            "zone_status": zone_status,
            "total_score": total_score,
            "matched_keywords": matched_keywords
        }
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing text analysis: {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error occurred while processing the request."}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found."}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed."}), 405

if __name__ == "__main__":
    # For local development run
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting developer server on {host}:{port}")
    app.run(host=host, port=port, debug=True)
