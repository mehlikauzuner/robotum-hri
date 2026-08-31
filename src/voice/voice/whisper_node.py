import os
import tempfile

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import whisper


class WhisperNode(Node):

    def __init__(self):
        super().__init__("whisper_node")

        self.publisher = self.create_publisher(
            String,
            "/user_command",
            10
        )

        self.get_logger().info("Loading Whisper Small model...")

        self.model = whisper.load_model("small")

        self.get_logger().info("Whisper Small model loaded.")
        self.get_logger().info("Whisper Node Started.")

    def transcribe_audio(self, audio_file):
        result = self.model.transcribe(
            audio_file,
            language="en",
            fp16=False
        )

        return result["text"].strip()

    def listen_once(self):
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as temp_file:

            audio_file = temp_file.name

        try:
            command = (
                f"arecord -q -f cd -d 5 "
                f"-t wav {audio_file}"
            )

            os.system(command)

            text = self.transcribe_audio(audio_file)

            if text:
                msg = String()
                msg.data = text

                self.publisher.publish(msg)

                self.get_logger().info(
                    f"Whisper command: {text}"
                )

        finally:
            if os.path.exists(audio_file):
                os.remove(audio_file)


def main(args=None):

    rclpy.init(args=args)

    node = WhisperNode()

    try:
        while rclpy.ok():
            node.listen_once()
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
