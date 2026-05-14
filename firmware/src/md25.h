#ifndef MD25_H
#define MD25_H

#include <stdint.h>
#include <stdbool.h>
#include "hardware/i2c.h"

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
#define MD25_I2C_PORT   i2c0
#define MD25_SDA_PIN    0
#define MD25_SCL_PIN    1
#define MD25_I2C_FREQ   100000      // 100 kHz
#define MD25_ADDR       0x58        // 7-bit (0xB0 >> 1)
#define I2C_TIMEOUT_US  100000      // 100 ms

// ---------------------------------------------------------------------------
// Register addresses
// ---------------------------------------------------------------------------
#define MD25_REG_SPEED1     0x00
#define MD25_REG_SPEED2     0x01
#define MD25_REG_ENC1A      0x02
#define MD25_REG_ENC2A      0x06
#define MD25_REG_BATTERY    0x0A
#define MD25_REG_CURRENT1   0x0B
#define MD25_REG_CURRENT2   0x0C
#define MD25_REG_SW_REV     0x0D
#define MD25_REG_ACCEL      0x0E
#define MD25_REG_MODE       0x0F
#define MD25_REG_COMMAND    0x10

// ---------------------------------------------------------------------------
// Command values
// ---------------------------------------------------------------------------
#define MD25_CMD_RESET_ENCODERS     0x20
#define MD25_CMD_DISABLE_SPEED_REG  0x30
#define MD25_CMD_ENABLE_SPEED_REG   0x31
#define MD25_CMD_DISABLE_TIMEOUT    0x32
#define MD25_CMD_ENABLE_TIMEOUT     0x33

// ---------------------------------------------------------------------------
// Mode 0 constants (individual motor control, unsigned 0-255, 128=stop)
// ---------------------------------------------------------------------------
#define MD25_SPEED_STOP     128

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

/// Initialise I2C and configure MD25 in Mode 0 (individual motor speeds).
/// Returns true if the MD25 responds on the bus.
bool md25_init(void);

/// Write individual motor speeds (0=full rev, 128=stop, 255=full fwd).
void md25_set_motors(uint8_t speed1, uint8_t speed2);

/// Stop both motors.
void md25_stop(void);

/// Read encoder 1 count (signed 32-bit).
int32_t md25_read_encoder1(void);

/// Read encoder 2 count (signed 32-bit).
int32_t md25_read_encoder2(void);

/// Reset both encoder counts to zero.
void md25_reset_encoders(void);

/// Read battery voltage in decivolts (e.g. 121 = 12.1V).
uint8_t md25_read_battery(void);

/// Read motor 1 current in deci-amps (e.g. 25 = 2.5A).
uint8_t md25_read_current1(void);

/// Read motor 2 current in deci-amps.
uint8_t md25_read_current2(void);

/// Set acceleration rate (1-10). Default is 5.
void md25_set_acceleration(uint8_t accel);

#endif // MD25_H
