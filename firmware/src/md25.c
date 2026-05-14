#include "md25.h"
#include "pico/stdlib.h"

// ---------------------------------------------------------------------------
// Low-level I2C helpers
// ---------------------------------------------------------------------------

static int md25_write_reg(uint8_t reg, uint8_t value) {
    uint8_t buf[2] = {reg, value};
    return i2c_write_timeout_us(MD25_I2C_PORT, MD25_ADDR, buf, 2, false, I2C_TIMEOUT_US);
}

static int md25_read_reg(uint8_t reg, uint8_t *value) {
    int ret = i2c_write_timeout_us(MD25_I2C_PORT, MD25_ADDR, &reg, 1, true, I2C_TIMEOUT_US);
    if (ret < 0) return ret;
    return i2c_read_timeout_us(MD25_I2C_PORT, MD25_ADDR, value, 1, false, I2C_TIMEOUT_US);
}

static int32_t md25_read_encoder(uint8_t start_reg) {
    uint8_t buf[4] = {0};
    int ret = i2c_write_timeout_us(MD25_I2C_PORT, MD25_ADDR, &start_reg, 1, true, I2C_TIMEOUT_US);
    if (ret < 0) return 0;
    ret = i2c_read_timeout_us(MD25_I2C_PORT, MD25_ADDR, buf, 4, false, I2C_TIMEOUT_US);
    if (ret < 0) return 0;

    return ((int32_t)buf[0] << 24) |
           ((int32_t)buf[1] << 16) |
           ((int32_t)buf[2] << 8)  |
           ((int32_t)buf[3]);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

bool md25_init(void) {
    i2c_init(MD25_I2C_PORT, MD25_I2C_FREQ);
    gpio_set_function(MD25_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(MD25_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(MD25_SDA_PIN);
    gpio_pull_up(MD25_SCL_PIN);

    // Check if MD25 responds
    uint8_t dummy;
    int ret = i2c_read_timeout_us(MD25_I2C_PORT, MD25_ADDR, &dummy, 1, false, I2C_TIMEOUT_US);
    if (ret < 0) return false;

    // Mode 0: individual motor control, unsigned (0=rev, 128=stop, 255=fwd)
    md25_write_reg(MD25_REG_MODE, 0);

    // Disable motor timeout (we handle watchdog in software)
    md25_write_reg(MD25_REG_COMMAND, MD25_CMD_DISABLE_TIMEOUT);

    // Reset encoders
    md25_write_reg(MD25_REG_COMMAND, MD25_CMD_RESET_ENCODERS);

    return true;
}

void md25_set_motors(uint8_t speed1, uint8_t speed2) {
    md25_write_reg(MD25_REG_SPEED1, speed1);
    md25_write_reg(MD25_REG_SPEED2, speed2);
}

void md25_stop(void) {
    md25_set_motors(MD25_SPEED_STOP, MD25_SPEED_STOP);
}

int32_t md25_read_encoder1(void) {
    return md25_read_encoder(MD25_REG_ENC1A);
}

int32_t md25_read_encoder2(void) {
    return md25_read_encoder(MD25_REG_ENC2A);
}

void md25_reset_encoders(void) {
    md25_write_reg(MD25_REG_COMMAND, MD25_CMD_RESET_ENCODERS);
}

uint8_t md25_read_battery(void) {
    uint8_t val = 0;
    md25_read_reg(MD25_REG_BATTERY, &val);
    return val;
}

uint8_t md25_read_current1(void) {
    uint8_t val = 0;
    md25_read_reg(MD25_REG_CURRENT1, &val);
    return val;
}

uint8_t md25_read_current2(void) {
    uint8_t val = 0;
    md25_read_reg(MD25_REG_CURRENT2, &val);
    return val;
}

void md25_set_acceleration(uint8_t accel) {
    if (accel < 1) accel = 1;
    if (accel > 10) accel = 10;
    md25_write_reg(MD25_REG_ACCEL, accel);
}
