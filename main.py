import os
from flask import Flask, request, jsonify
from process import run

app = Flask(__name__)

@app.get("/")
def health():
    return "grant-drafting-assistant up", 200

@app.post("/run")
def run_process():
    payload = request.get_json(force=True) or {}
    result = run(payload)
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
