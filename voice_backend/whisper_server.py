import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import whisper


HOST = "127.0.0.1"
PORT = 8766

print("Loading Whisper Small model...")
model = whisper.load_model("small")
print("Whisper Small model loaded.")


class WhisperHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )
        self.end_headers()

    def do_POST(self):

        if self.path != "/transcribe":
            self.send_json(
                {"error": "Unknown endpoint"},
                status=404,
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            audio_data = self.rfile.read(content_length)

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as temp_file:

                temp_file.write(audio_data)
                audio_path = temp_file.name

            print("Transcribing audio...")

            result = model.transcribe(
                audio_path,
                fp16=False,
            )

            text = result["text"].strip()
            language = result["language"]

            print(f"Language: {language}")
            print(f"Text: {text}")

            self.send_json(
                {
                    "text": text,
                    "language": language,
                }
            )

        except Exception as error:

            print(f"ERROR: {error}")

            self.send_json(
                {
                    "error": str(error),
                },
                status=500,
            )

        finally:

            if "audio_path" in locals() and os.path.exists(audio_path):
                os.remove(audio_path)


if __name__ == "__main__":

    server = HTTPServer(
        (HOST, PORT),
        WhisperHandler,
    )

    print(
        f"Whisper server running at "
        f"http://{HOST}:{PORT}"
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping Whisper server...")

    finally:
        server.server_close()