
use pyo3::prelude::*;

mod security;

#[pymodule]
fn finance_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    security::__python__::register(m)?;
    Ok(())
}
