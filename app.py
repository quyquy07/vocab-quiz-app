import io
import os
import re
import zipfile

from flask import Flask, render_template, request, send_file

from dictionary import lookup_word

app = Flask(__name__)
AUDIO_DIR = os.path.join(app.static_folder, "audio")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    raw = request.form.get("words", "")
    words = [w.strip() for w in re.split(r"[,\n\r]+", raw) if w.strip()]
    results = [lookup_word(w) for w in words]
    return render_template("quiz.html", results=results)


@app.route("/download-zip", methods=["POST"])
def download_zip():
    # Only serve files that actually live inside static/audio; take the
    # basename of each requested path to block any directory traversal.
    requested = request.form.getlist("audio")
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in requested:
            name = os.path.basename(rel)
            path = os.path.join(AUDIO_DIR, name)
            if os.path.isfile(path):
                zf.write(path, name)
    mem.seek(0)
    return send_file(
        mem,
        mimetype="application/zip",
        as_attachment=True,
        download_name="audio.zip",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
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
