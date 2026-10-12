//! Optional I2C LSM6DSV16X input for boards that do not carry `imu_to_dxl`.
//!
//! This module is deliberately separate from the Dynamixel IMU decoder. The original
//! `imu_to_dxl` path remains unchanged; this path is selected only by configuration.

use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::path::PathBuf;

use crate::imu::ImuData;
use crate::io::{ImuStale, IoError, Result};

const I2C_SLAVE: libc::c_ulong = 0x0703;
const WHO_AM_I: u8 = 0x0f;
const CTRL1_XL: u8 = 0x10;
const CTRL2_G: u8 = 0x11;
const CTRL3_C: u8 = 0x12;
const STATUS_REG: u8 = 0x1e;
const OUTX_L_G: u8 = 0x22;
const OUTX_L_A: u8 = 0x28;
const WHO_AM_I_VALUE: u8 = 0x70;

/// The tested ZERO 3 wiring: I2C bus 4, SA0/SDO strapped low.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct I2cImuConfig {
    pub bus: u8,
    pub address: u16,
}

pub struct I2cImu {
    file: std::fs::File,
    last: Option<ImuData>,
    stale: ImuStale,
    samples: u32,
}

impl I2cImu {
    pub fn open(config: I2cImuConfig) -> Result<Self> {
        let path = PathBuf::from(format!("/dev/i2c-{}", config.bus));
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&path)
            .map_err(|e| IoError::Port {
                path: path.display().to_string(),
                source: e,
            })?;

        let result =
            unsafe { libc::ioctl(file.as_raw_fd(), I2C_SLAVE, config.address as libc::c_uint) };
        if result < 0 {
            return Err(IoError::Bus(format!(
                "select I2C slave 0x{:02x} on {}: {}",
                config.address,
                path.display(),
                std::io::Error::last_os_error()
            )));
        }

        let mut imu = Self {
            file,
            last: None,
            stale: ImuStale::default(),
            samples: 0,
        };
        let who = imu.read_reg(WHO_AM_I)?;
        if who != WHO_AM_I_VALUE {
            return Err(IoError::Bus(format!(
                "unexpected LSM6DSV16X WHO_AM_I 0x{who:02x}, expected 0x{WHO_AM_I_VALUE:02x}"
            )));
        }

        // BDU + register auto-increment, then the same 60 Hz configuration used during
        // board bring-up. These writes are volatile and are intentionally repeated at open.
        imu.write_reg(CTRL3_C, 0x44)?;
        imu.write_reg(0x17, 0x40)?;
        imu.write_reg(0x18, 0x08)?;
        imu.write_reg(0x16, 0x01)?;
        imu.write_reg(0x15, 0x61)?;
        imu.write_reg(CTRL1_XL, 0x06)?;
        imu.write_reg(CTRL2_G, 0x06)?;

        tracing::info!(
            bus = config.bus,
            address = format_args!("0x{:02x}", config.address),
            "LSM6DSV16X I2C IMU ready"
        );
        Ok(imu)
    }

    fn read_reg(&mut self, register: u8) -> Result<u8> {
        let mut value = [0u8; 1];
        self.file.write_all(&[register]).map_err(|e| {
            IoError::Bus(format!("write LSM6DSV16X register 0x{register:02x}: {e}"))
        })?;
        self.file
            .read_exact(&mut value)
            .map_err(|e| IoError::Bus(format!("read LSM6DSV16X register 0x{register:02x}: {e}")))?;
        Ok(value[0])
    }

    fn write_reg(&mut self, register: u8, value: u8) -> Result<()> {
        self.file
            .write_all(&[register, value])
            .map_err(|e| IoError::Bus(format!("write LSM6DSV16X register 0x{register:02x}: {e}")))
    }

    fn read_block(&mut self, register: u8, data: &mut [u8]) -> Result<()> {
        self.file.write_all(&[register]).map_err(|e| {
            IoError::Bus(format!("select LSM6DSV16X register 0x{register:02x}: {e}"))
        })?;
        self.file
            .read_exact(data)
            .map_err(|e| IoError::Bus(format!("read LSM6DSV16X block 0x{register:02x}: {e}")))
    }

    fn decode_i16(lo: u8, hi: u8) -> f64 {
        f64::from(i16::from_le_bytes([lo, hi]))
    }

    fn decode_sample(&mut self) -> Result<ImuData> {
        let mut gyro = [0u8; 6];
        let mut accel = [0u8; 6];
        self.read_block(OUTX_L_G, &mut gyro)?;
        self.read_block(OUTX_L_A, &mut accel)?;

        // LSM6DSV16X defaults used above: ±250 dps (8.75 mdps/LSB), ±2 g
        // (0.061 mg/LSB). The accelerometer reports specific force, so negate it
        // to obtain the gravity vector expected by robotd.
        let gyro_sensor = [
            Self::decode_i16(gyro[0], gyro[1]) * 0.00875 * std::f64::consts::PI / 180.0,
            Self::decode_i16(gyro[2], gyro[3]) * 0.00875 * std::f64::consts::PI / 180.0,
            Self::decode_i16(gyro[4], gyro[5]) * 0.00875 * std::f64::consts::PI / 180.0,
        ];
        let gyro = sensor_to_trunk(gyro_sensor);
        let accel_sensor = [
            -Self::decode_i16(accel[0], accel[1]) * 0.000061 * 9.80665,
            -Self::decode_i16(accel[2], accel[3]) * 0.000061 * 9.80665,
            -Self::decode_i16(accel[4], accel[5]) * 0.000061 * 9.80665,
        ];
        let accel = sensor_to_trunk(accel_sensor);

        let norm = (accel[0] * accel[0] + accel[1] * accel[1] + accel[2] * accel[2]).sqrt();
        let gravity = if norm > 0.1 {
            [accel[0] / norm, accel[1] / norm, accel[2] / norm]
        } else {
            [0.0, 0.0, -1.0]
        };

        Ok(ImuData {
            gyro,
            gravity,
            quat: quat_from_gravity(gravity),
        })
    }

    pub fn read(&mut self) -> Result<ImuData> {
        let status = self.read_reg(STATUS_REG)?;
        let sample = self.decode_sample()?;
        if status & 0x07 == 0 {
            if let Some(last) = self.last {
                self.stale.total = self.stale.total.saturating_add(1);
                self.stale.run = self.stale.run.saturating_add(1);
                return Ok(last);
            }
        } else {
            self.stale.run = 0;
            self.samples = self.samples.saturating_add(1);
        }
        self.last = Some(sample);
        Ok(sample)
    }

    pub fn stale(&self) -> ImuStale {
        self.stale
    }

    pub fn ready(&self) -> bool {
        self.samples >= 25
    }
}

/// Match the mounting convention of the current ZERO 3 I2C IMU installation.
///
/// The board is mounted with sensor Z along trunk X, sensor Y along trunk Y, and
/// sensor X opposite trunk Z. Keeping this transform in one place makes the I2C
/// backend produce `ImuData` whose upright gravity is `[0, 0, -1]`.
fn sensor_to_trunk(v: [f64; 3]) -> [f64; 3] {
    [v[2], v[1], -v[0]]
}

/// A zero-yaw quaternion mapping the measured body gravity to world down.
fn quat_from_gravity(g: [f64; 3]) -> [f64; 4] {
    let down = [0.0, 0.0, -1.0];
    let dot = (g[0] * down[0] + g[1] * down[1] + g[2] * down[2]).clamp(-1.0, 1.0);
    let cross = [
        g[1] * down[2] - g[2] * down[1],
        g[2] * down[0] - g[0] * down[2],
        g[0] * down[1] - g[1] * down[0],
    ];
    let norm = (cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]).sqrt();
    if norm < 1e-9 {
        return if dot >= 0.0 {
            [1.0, 0.0, 0.0, 0.0]
        } else {
            [0.0, 1.0, 0.0, 0.0]
        };
    }
    let angle = dot.acos();
    let half = angle / 2.0;
    let s = half.sin() / norm;
    [half.cos(), cross[0] * s, cross[1] * s, cross[2] * s]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mounting_transform_matches_current_i2c_installation() {
        assert_eq!(sensor_to_trunk([1.0, 2.0, 3.0]), [3.0, 2.0, -1.0]);
    }

    #[test]
    fn measured_zero_g_mount_is_upright_after_transform() {
        // In this mounting, an upright robot measures gravity along sensor +X after
        // converting specific force to gravity, which maps to trunk -Z.
        let gravity = sensor_to_trunk([9.80665, 0.0, 0.0]);
        assert_eq!(gravity, [0.0, 0.0, -9.80665]);
    }
}
