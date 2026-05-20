from flask import Flask, request, jsonify
from logging.handlers import RotatingFileHandler
import logging
import os
import traceback
from datetime import datetime

app = Flask(__name__)

# Resolve logs directory relative to this file, not the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

ERRORS_LOG = os.path.join(LOGS_DIR, "errors.log")
AUDIT_LOG = os.path.join(LOGS_DIR, "audit.log")

# --- Error Logger ---
error_handler = RotatingFileHandler(ERRORS_LOG, maxBytes=5_000_000, backupCount=5)
error_handler.setLevel(logging.DEBUG)
error_handler.setFormatter(logging.Formatter("%(message)s"))

error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.DEBUG)
error_logger.addHandler(error_handler)

# --- Audit Logger ---
audit_handler = RotatingFileHandler(AUDIT_LOG, maxBytes=5_000_000, backupCount=5)
audit_handler.setFormatter(logging.Formatter("%(message)s"))

audit_logger = logging.getLogger("audit_logger")
audit_logger.setLevel(logging.INFO)
audit_logger.addHandler(audit_handler)


def format_log(data):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    level = data.get("level", "INFO").upper()
    service = data.get("service", "GENERAL")
    message = data.get("message", "")
    user = data.get("user", "unknown")
    stack_trace = data.get("stack_trace", "")

    log = f"[{timestamp}] | LEVEL: {level} | SERVICE: {service} | USER: {user} | MESSAGE: {message}"
    if stack_trace:
        log += f"\n  TRACE: {stack_trace}"
    return log


@app.route("/log", methods=["POST"])
def log():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data:
            return jsonify({"error": "message field is required"}), 400

        entry = format_log(data)
        level = data.get("level", "INFO").upper()

        if level in ("ERROR", "CRITICAL", "WARNING"):
            error_logger.error(entry)
        else:
            error_logger.info(entry)

        return jsonify({"status": "logged", "entry": entry}), 200

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/audit", methods=["POST"])
def audit():
    try:
        data = request.get_json(force=True)
        required = ["user", "command", "classification", "action", "status"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = (
            f"[{timestamp}] | USER: {data['user']} | COMMAND: {data['command']} | "
            f"CLASSIFICATION: {data['classification']} | ACTION: {data['action']} | STATUS: {data['status']}"
        )
        audit_logger.info(entry)
        return jsonify({"status": "logged", "entry": entry}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logs", methods=["GET"])
def get_logs():
    log_type = request.args.get("type", "errors")
    lines = int(request.args.get("lines", 50))
    file_map = {"errors": ERRORS_LOG, "audit": AUDIT_LOG}
    path = file_map.get(log_type)

    if not path or not os.path.exists(path):
        return jsonify({"logs": []}), 200

    with open(path, "r") as f:
        all_lines = f.readlines()

    return jsonify({"logs": [l.strip() for l in all_lines[-lines:]]}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AiPipeline Logger", "time": datetime.utcnow().isoformat()}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
