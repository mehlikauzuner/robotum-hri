import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import LaserScan


class DirectionSafety(Node):

    def __init__(self):
        super().__init__('direction_safety')

        self.scan = None
        self.last_linear_x = 0.0
        self.last_angular_z = 0.0
        self.last_safe_msg = None

        # Robot engelden bu mesafeye gelmeden duracak
        self.safety_distance = 0.35

        # Hareket yönü için kontrol edilen alan
        self.front_angle = math.radians(30)
        self.rear_angle = math.radians(30)

        self.cmd_sub = self.create_subscription(
            TwistStamped,
            '/cmd_vel_unsafe',
            self.cmd_callback,
            10
        )

        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        self.cmd_pub = self.create_publisher(
            TwistStamped,
            '/cmd_vel',
            10
        )

        self.get_logger().info(
            f'Direction Safety Node started - '
            f'safety distance: {self.safety_distance:.2f} m'
        )

    def scan_callback(self, msg):
        self.scan = msg

        # Robot geri hareket halindeyken sürekli arka kontrol yap
        if self.last_linear_x < 0.0:

            if self.rear_obstacle_detected():

                stop_msg = TwistStamped()
                stop_msg.header.frame_id = 'base_link'

                stop_msg.twist.linear.x = 0.0
                stop_msg.twist.angular.z = 0.0

                self.last_linear_x = 0.0
                self.last_angular_z = 0.0

                self.get_logger().warning(
                    'CONTINUOUS STOP BACKWARD! REAR OBSTACLE TOO CLOSE'
                )

                self.cmd_pub.publish(stop_msg)

        # Robot ileri hareket ederken lazer sürekli kontrol edilir
        if (
            self.last_safe_msg is not None
            and self.last_safe_msg.twist.linear.x > 0.0
            and self.front_obstacle_detected()
        ):
            stop_msg = TwistStamped()
            stop_msg.header = self.last_safe_msg.header
            stop_msg.header.stamp = self.get_clock().now().to_msg()

            stop_msg.twist.linear.x = 0.0
            stop_msg.twist.linear.y = 0.0
            stop_msg.twist.linear.z = 0.0

            # Dönüşü engelleme, sadece ileri hareketi kes
            stop_msg.twist.angular = self.last_safe_msg.twist.angular

            self.get_logger().warning(
                'EMERGENCY STOP! OBSTACLE DETECTED WHILE MOVING'
            )

            self.cmd_pub.publish(stop_msg)

            # Robot artık ileri gitmiyor olarak işaretle
            self.last_safe_msg = stop_msg

    def get_min_distance_in_sector(self, start_angle, end_angle):

        if self.scan is None:
            return None

        valid_ranges = []

        for i, r in enumerate(self.scan.ranges):

            if not math.isfinite(r):
                continue

            if r < self.scan.range_min or r > self.scan.range_max:
                continue

            angle = self.scan.angle_min + i * self.scan.angle_increment

            # Açıyı 0 -> 2π aralığına getir
            angle = angle % (2 * math.pi)

            start = start_angle % (2 * math.pi)
            end = end_angle % (2 * math.pi)

            # Normal sektör veya 0 derecesini geçen sektör
            if start <= end:
                in_sector = start <= angle <= end
            else:
                in_sector = angle >= start or angle <= end

            if in_sector:
                valid_ranges.append(r)

        if not valid_ranges:
            return None

        return min(valid_ranges)


    def front_obstacle_detected(self):

        min_distance = self.get_min_distance_in_sector(
            -self.front_angle,
            self.front_angle
        )

        self.get_logger().info(
            f'FRONT CHECK: min_distance={min_distance}, '
            f'safety_distance={self.safety_distance}'
        )

        if (
            min_distance is not None
            and min_distance < self.safety_distance
        ):
            self.get_logger().warning(
                f'FRONT OBSTACLE: {min_distance:.2f} m'
            )
            return True

        return False

    def rear_obstacle_detected(self):

        # Lidar'da arka taraf 150° - 210° aralığıdır
        min_distance = self.get_min_distance_in_sector(
            math.radians(150),
            math.radians(210)
        )

        self.get_logger().info(
            f'REAR CHECK: min_distance={min_distance}, '
            f'safety_distance={self.safety_distance}'
        )

        if (
            min_distance is not None
            and min_distance < self.safety_distance
        ):
            self.get_logger().warning(
                f'REAR OBSTACLE: {min_distance:.2f} m'
            )
            return True

        return False


    def cmd_callback(self, msg):

        safe_msg = TwistStamped()

        safe_msg.header = msg.header
        safe_msg.twist = msg.twist

        linear_x = msg.twist.linear.x
        angular_z = msg.twist.angular.z

        self.last_linear_x = linear_x
        self.last_angular_z = angular_z

        self.get_logger().info(
            f'CMD RECEIVED: linear.x={linear_x:.2f}, '
            f'angular.z={angular_z:.2f}'
        )

        # İLERİ hareket
        if linear_x > 0.0:

            if self.front_obstacle_detected():

                safe_msg.twist.linear.x = 0.0

                self.get_logger().warning(
                    'STOP FORWARD! FRONT OBSTACLE TOO CLOSE'
                )

        # GERİ hareket
        elif linear_x < 0.0:

            if self.rear_obstacle_detected():

                safe_msg.twist.linear.x = 0.0

                self.get_logger().warning(
                    'STOP BACKWARD! REAR OBSTACLE TOO CLOSE'
                )

        # Sadece dönme komutuysa angular.z değiştirilmez
        # Böylece robot engelden güvenli yöne döndürülebilir.
        if angular_z != 0.0:
            self.get_logger().debug(
                f'ROTATION ALLOWED: angular.z={angular_z:.2f}'
            )

        self.get_logger().warning(
            f'PUBLISHING SAFE CMD: linear.x={safe_msg.twist.linear.x:.2f}'
        )

        self.cmd_pub.publish(safe_msg)

        # Son yayınlanan komutu sakla.
        # Böylece scan_callback robot hareket ederken
        # sürekli güvenlik kontrolü yapabilir.
        self.last_safe_msg = safe_msg


def main(args=None):

    rclpy.init(args=args)

    node = DirectionSafety()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
