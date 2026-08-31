from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import subprocess
import tempfile

HOST = "127.0.0.1"
PORT = 8770

BASE_DIR = Path("/home/mehlika/robotum-hri-github")

MODELS = {
    "tr": BASE_DIR / "tts_models/tr_TR/tr_TR-dfki-medium.onnx",
    "en": BASE_DIR / "tts_models/en_US/en_US-lessac-medium.onnx",
    "pl": BASE_DIR / "tts_models/pl_PL/pl_PL-gosia-medium.onnx",
}

PIPER = Path("/home/mehlika/whisper-env/bin/piper")


class TTSHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_error(404, "Endpoint not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            text = data.get("text", "").strip()
            language = data.get("language", "en").lower()

            if not text:
                self.send_error(400, "Text is empty")
                return

            if language not in MODELS:
                self.send_error(
                    400,
                    f"Unsupported language: {language}. "
                    f"Supported: {', '.join(MODELS.keys())}"
                )
                return

            model = MODELS[language]

            if not model.exists():
                self.send_error(500, f"Model not found: {model}")
                return

            if not PIPER.exists():
                self.send_error(500, f"Piper not found: {PIPER}")
                return

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp_file:
                output_wav = Path(temp_file.name)

            command = [
                str(PIPER),
                "-m",
                str(model),
                "-f",
                str(output_wav),
            ]

            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                capture_output=True,
            )

            wav_data = output_wav.read_bytes()
            output_wav.unlink(missing_ok=True)

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_data)))
            self.end_headers()
            self.wfile.write(wav_data)

            print(
                f"TTS: language={language}, "
                f"text={text}"
            )

        except Exception as error:
            print(f"TTS ERROR: {error}")
            self.send_error(500, str(error))

    def log_message(self, format, *args):
        print(f"[TTS HTTP] {format % args}")


if __name__ == "__main__":
    print("Starting Robotum TTS server...")
    print(f"Supported languages: {', '.join(MODELS.keys())}")
    print(f"TTS server running at http://{HOST}:{PORT}")

    server = HTTPServer((HOST, PORT), TTSHandler)
    server.serve_forever()
