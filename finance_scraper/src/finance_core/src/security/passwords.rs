/// Password security utilities and functions.

use base64::{
    engine::general_purpose::URL_SAFE_NO_PAD,
    Engine,
};
use pbkdf2::pbkdf2_hmac;
use rand::TryRngCore;
use rand::rngs::OsRng;
use sha2::Sha256;
use subtle::ConstantTimeEq;


const ITERATIONS: u32       = 310_000;
const SALT_LENGTH: usize    = 16;
const HASH_LENGTH: usize    = 32;


fn encode_part(value: &[u8]) -> String {
    URL_SAFE_NO_PAD.encode(value)
}

fn decode_part(value: &str) -> Result<Vec<u8>, ()> {
    URL_SAFE_NO_PAD
        .decode(value)
        .map_err(|_| ())
}

pub fn hash_password(password: &str) -> Result<String, String> {
    let mut salt = [0u8; SALT_LENGTH];

    OsRng
        .try_fill_bytes(&mut salt)
        .map_err(|_| "failed to generate secure random salt".to_string())?;

    let mut digest = [0u8; HASH_LENGTH];

    pbkdf2_hmac::<Sha256>(
        password.as_bytes(),
        &salt,
        ITERATIONS,
        &mut digest,
    );

    Ok(format!(
        "pbkdf2_sha256${}${}${}",
        ITERATIONS,
        encode_part(&salt),
        encode_part(&digest),
    ))
}

pub fn verify_password(
    password: &str,
    encoded_password: &str,
) -> bool {
    let parts: Vec<&str> = encoded_password.split('$').collect();

    if parts.len() != 4 { return false; }

    let algorithm = parts[0];
    let iterations_text = parts[1];
    let encoded_salt = parts[2];
    let encoded_digest = parts[3];

    if algorithm != "pbkdf2_sha256" { return false; }

    let iterations: u32 = match iterations_text.parse() {
        Ok(value) => value,
        Err(_)    => return false,
    };
    if iterations == 0 || iterations > 10_000_000 { return false; }

    let salt = match decode_part(encoded_salt) {
        Ok(value) => value,
        Err(_)    => return false,
    };

    let expected = match decode_part(encoded_digest) {
        Ok(value) => value,
        Err(_)    => return false,
    };

    let mut actual = [0u8; HASH_LENGTH];
    pbkdf2_hmac::<Sha256>(
        password.as_bytes(),
        &salt,
        iterations,
        &mut actual,
    );
    actual.as_slice().ct_eq(expected.as_slice()).into()
}
