/**
 * micro-ROS MD25 Motor Controller Node
 *
 * Runs on Raspberry Pi Pico. Communicates with MD25 via I2C and exposes
 * ROS 2 topics through micro-ROS over USB serial.
 *
 * Subscriptions:
 *   cmd_vel (geometry_msgs/Twist) — linear.x and angular.z drive the motors
 *
 * Publishers (all @ 10 Hz):
 *   encoder_left     (std_msgs/Int32)   — left wheel encoder ticks
 *   encoder_right    (std_msgs/Int32)   — right wheel encoder ticks
 *   battery_voltage  (std_msgs/Float32) — battery volts
 *   current_left     (std_msgs/Float32) — left motor amps
 *   current_right    (std_msgs/Float32) — right motor amps
 *
 * Design:
 *   - Mode 0 (individual motor speeds) for direct differential drive control
 *   - cmd_vel is converted to left/right motor speeds using unicycle model
 *   - A software watchdog stops motors if no cmd_vel received within 500ms
 *   - Publishers run at 10 Hz from the main loop
 */

#include <stdio.h>
#include <math.h>

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>

#include <geometry_msgs/msg/twist.h>
#include <std_msgs/msg/int32.h>
#include <std_msgs/msg/float32.h>

#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "pico_uart_transports.h"
#include "md25.h"

// ---------------------------------------------------------------------------
// Debug LED (GP25 on standard Pico)
// ---------------------------------------------------------------------------
#define LED_PIN 25

static void led_init(void) {
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_put(LED_PIN, 0);
}

static void led_toggle(void) {
    gpio_put(LED_PIN, !gpio_get(LED_PIN));
}

// ---------------------------------------------------------------------------
// Robot physical parameters (tune to your chassis)
// ---------------------------------------------------------------------------
#define WHEEL_SEPARATION    0.38f   // metres between wheel centres
#define MAX_LINEAR_VEL      1.0f    // m/s at full motor speed
#define CMD_VEL_TIMEOUT_MS  500     // watchdog timeout

// ---------------------------------------------------------------------------
// Publishing rate
// ---------------------------------------------------------------------------
#define PUBLISH_PERIOD_MS   100     // 10 Hz

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------
static rcl_subscription_t sub_cmd_vel;
static rcl_publisher_t pub_enc_left;
static rcl_publisher_t pub_enc_right;
static rcl_publisher_t pub_battery;
static rcl_publisher_t pub_cur_left;
static rcl_publisher_t pub_cur_right;

static geometry_msgs__msg__Twist msg_cmd_vel;
static std_msgs__msg__Int32 msg_enc_left;
static std_msgs__msg__Int32 msg_enc_right;
static std_msgs__msg__Float32 msg_battery;
static std_msgs__msg__Float32 msg_cur_left;
static std_msgs__msg__Float32 msg_cur_right;

static absolute_time_t last_cmd_vel_time;

// ---------------------------------------------------------------------------
// Convert Twist (linear.x, angular.z) to MD25 motor bytes
// ---------------------------------------------------------------------------
static void twist_to_motors(float linear, float angular, uint8_t *m1, uint8_t *m2) {
    float v_left  = linear - angular * (WHEEL_SEPARATION / 2.0f);
    float v_right = linear + angular * (WHEEL_SEPARATION / 2.0f);

    // Clamp to max velocity range
    float scale = fmaxf(fabsf(v_left), fabsf(v_right));
    if (scale > MAX_LINEAR_VEL) {
        v_left  = v_left  / scale * MAX_LINEAR_VEL;
        v_right = v_right / scale * MAX_LINEAR_VEL;
    }

    // Map to MD25 Mode 0: 0=full reverse, 128=stop, 255=full forward
    int16_t left_byte  = (int16_t)(128.0f + (v_left  / MAX_LINEAR_VEL) * 127.0f);
    int16_t right_byte = (int16_t)(128.0f + (v_right / MAX_LINEAR_VEL) * 127.0f);

    if (left_byte < 0) left_byte = 0;
    if (left_byte > 255) left_byte = 255;
    if (right_byte < 0) right_byte = 0;
    if (right_byte > 255) right_byte = 255;

    *m1 = (uint8_t)left_byte;
    *m2 = (uint8_t)right_byte;
}

// ---------------------------------------------------------------------------
// cmd_vel subscription callback
// ---------------------------------------------------------------------------
static void cmd_vel_callback(const void *msg_in) {
    const geometry_msgs__msg__Twist *twist = (const geometry_msgs__msg__Twist *)msg_in;

    uint8_t m1, m2;
    twist_to_motors((float)twist->linear.x, (float)twist->angular.z, &m1, &m2);
    md25_set_motors(m1, m2);

    last_cmd_vel_time = get_absolute_time();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
int main() {
    led_init();
    sleep_ms(2000);

    // Fast blink = booted OK
    for (int i = 0; i < 6; i++) {
        led_toggle();
        sleep_ms(100);
    }
    gpio_put(LED_PIN, 0);

    // Initialise MD25 (non-blocking)
    bool md25_ok = md25_init();
    if (!md25_ok) {
        for (int i = 0; i < 4; i++) {
            led_toggle();
            sleep_ms(500);
        }
    }
    gpio_put(LED_PIN, 1);

    // micro-ROS transport (USB serial)
    rmw_uros_set_custom_transport(
        true,
        NULL,
        pico_serial_transport_open,
        pico_serial_transport_close,
        pico_serial_transport_write,
        pico_serial_transport_read
    );

    // Wait for agent
    gpio_put(LED_PIN, 0);
    while (true) {
        led_toggle();
        sleep_ms(200);
        if (rmw_uros_ping_agent(100, 1) == RCL_RET_OK) break;
    }
    gpio_put(LED_PIN, 1);

    // --- micro-ROS init ---
    rcl_allocator_t allocator = rcl_get_default_allocator();
    rclc_support_t support;
    (void)rclc_support_init(&support, 0, NULL, &allocator);

    rcl_node_t node;
    (void)rclc_node_init_default(&node, "md25_base_controller", "", &support);

    // --- Subscriber ---
    (void)rclc_subscription_init_default(
        &sub_cmd_vel, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
        "cmd_vel"
    );

    // --- Publishers (namespaced under hardware interface) ---
    (void)rclc_publisher_init_default(
        &pub_enc_left, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "wheel/left/encoder"
    );
    (void)rclc_publisher_init_default(
        &pub_enc_right, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "wheel/right/encoder"
    );
    (void)rclc_publisher_init_default(
        &pub_battery, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
        "battery/voltage"
    );
    (void)rclc_publisher_init_default(
        &pub_cur_left, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
        "wheel/left/current"
    );
    (void)rclc_publisher_init_default(
        &pub_cur_right, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32),
        "wheel/right/current"
    );

    // --- Executor: 1 subscription ---
    rclc_executor_t executor;
    (void)rclc_executor_init(&executor, &support.context, 1, &allocator);
    (void)rclc_executor_add_subscription(&executor, &sub_cmd_vel, &msg_cmd_vel, &cmd_vel_callback, ON_NEW_DATA);

    // Initialise watchdog
    last_cmd_vel_time = get_absolute_time();

    // --- Main loop ---
    absolute_time_t last_publish = get_absolute_time();
    while (true) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));

        int64_t since_publish = absolute_time_diff_us(last_publish, get_absolute_time()) / 1000;
        if (since_publish >= PUBLISH_PERIOD_MS) {
            last_publish = get_absolute_time();

            // Watchdog
            int64_t elapsed = absolute_time_diff_us(last_cmd_vel_time, get_absolute_time()) / 1000;
            if (elapsed > CMD_VEL_TIMEOUT_MS) {
                md25_stop();
            }

            // Publish all sensor data
            msg_enc_left.data = md25_read_encoder1();
            (void)rcl_publish(&pub_enc_left, &msg_enc_left, NULL);

            msg_enc_right.data = md25_read_encoder2();
            (void)rcl_publish(&pub_enc_right, &msg_enc_right, NULL);

            msg_battery.data = (float)md25_read_battery() / 10.0f;
            (void)rcl_publish(&pub_battery, &msg_battery, NULL);

            msg_cur_left.data = (float)md25_read_current1() / 10.0f;
            (void)rcl_publish(&pub_cur_left, &msg_cur_left, NULL);

            msg_cur_right.data = (float)md25_read_current2() / 10.0f;
            (void)rcl_publish(&pub_cur_right, &msg_cur_right, NULL);

            led_toggle();
        }
    }

    return 0;
}
