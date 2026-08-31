import json
import urllib.request
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TTSNode(Node):

    def __init__(self):
        super().__init__("tts_node")

        self.subscription = self.create_subscription(
            String,
            "/robot_response",
            self.response_callback,
            10
        )

        self.get_logger().info("TTS Node Started.")

    def response_callback(self, msg):
        text = msg.data.strip()

        if not text:
            return

        self.get_logger().info(
            f"Speaking: {text}"
        )

        data = json.dumps({
            "text": text,
            "language": "en"
        }).encode("utf-8")

        request = urllib.request.Request(
            "http://127.0.0.1:8770/synthesize",
            data=data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                wav_data = response.read()

            process = subprocess.Popen(
                ["aplay", "-q", "-"],
                stdin=subprocess.PIPE
            )

            process.communicate(wav_data)

            self.get_logger().info(
                "Speech finished."
            )

        except Exception as error:
            self.get_logger().error(
                f"TTS failed: {error}"
            )


def main(args=None):

    rclpy.init(args=args)

    node = TTSNode()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
