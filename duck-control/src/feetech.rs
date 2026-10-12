//! Feetech-specific joint direction mapping.
//!
//! The installed servos are mounted so their electrical position direction is
//! opposite to the software joint convention. Keep this correction here rather
//! than changing the shared bus or Dynamixel mapping.

use std::f64::consts::PI;

const COUNTS: u16 = 4096;
const MAX_RAW: u16 = COUNTS - 1;

/// Mirror a Feetech raw position around the 2048 midpoint.
pub fn mirror_raw(raw: u16) -> u16 {
    (COUNTS - (raw & MAX_RAW)) & MAX_RAW
}

/// Convert a Feetech present-position register to the software joint angle.
pub fn angle_from_raw(raw: u16) -> f64 {
    let mirrored = mirror_raw(raw);
    (2.0 * PI * f64::from(mirrored) / f64::from(COUNTS)) - PI
}

/// Convert a software joint angle to the Feetech goal-position register.
pub fn raw_from_angle(angle: f64) -> u16 {
    let normalized = ((angle + PI) / (2.0 * PI)).clamp(0.0, f64::from(MAX_RAW) / f64::from(COUNTS));
    mirror_raw((normalized * f64::from(COUNTS)).round() as u16)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mirrors_around_midpoint() {
        assert_eq!(mirror_raw(0), 0);
        assert_eq!(mirror_raw(1000), 3096);
        assert_eq!(mirror_raw(2048), 2048);
        assert_eq!(mirror_raw(3000), 1096);
        assert_eq!(mirror_raw(4095), 1);
    }

    #[test]
    fn angle_direction_is_reversed() {
        assert!(angle_from_raw(1000) > 0.0);
        assert!(angle_from_raw(3000) < 0.0);
        assert!(angle_from_raw(2048).abs() < 1e-12);
    }

    #[test]
    fn conversion_round_trips() {
        for raw in [0, 1, 1000, 1024, 2048, 3000, 4095] {
            let angle = angle_from_raw(raw);
            assert_eq!(raw_from_angle(angle), raw);
        }
    }
}
