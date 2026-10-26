import os
import re

from flask import Flask, abort, request
from markupsafe import escape

app = Flask(__name__)  # creates the web app

# Secret comes from the environment, never the code. Fail securely if missing.
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set")
app.config["SECRET_KEY"] = secret_key

# Allow list, only letters and spaces, 1 to 50 characters
NAME_PATTERN = re.compile(r"^[A-Za-z ]{1,50}$")


@app.route("/")  # tells Flask which URL to listen to, home page
def home():
    return "<h1>Secure Flask App</h1><p>Try /greet?name=Muskan</p>"


@app.route("/greet")  # takes user input, so this is what attackers target
def greet():
    name = request.args.get("name", "")
    if not NAME_PATTERN.fullmatch(name):
        abort(400, description="Invalid name. Name must be 1 to 50 letters or spaces.")
    return f"<p>Hello, {escape(name)}!</p>"


@app.route("/health")  # Kubernetes uses this in Week 3 to check the app is alive
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":  # runs only on this laptop, not the network
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="127.0.0.1", port=port, debug=False)