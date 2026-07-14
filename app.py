import os
import re

from flask import Flask, render_template, request

from dictionary import lookup_word

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    raw = request.form.get("words", "")
    words = [w.strip() for w in re.split(r"[,\n\r]+", raw) if w.strip()]
    results = [lookup_word(w) for w in words]
    return render_template("quiz.html", results=results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
