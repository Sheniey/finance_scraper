
use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use super::passwords;

#[pyfunction]
pub fn hash_password(password: &str) -> PyResult<String> {
    passwords::hash_password(password)
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
pub fn verify_password(
    password: &str,
    encoded_password: &str,
) -> bool {
    passwords::verify_password(
        password,
        encoded_password,
    )
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = parent.py();
    let module = PyModule::new(py, "security")?;

    module.add_function(wrap_pyfunction!(hash_password, &module)?)?;
    module.add_function(wrap_pyfunction!(verify_password, &module)?)?;

    parent.add_submodule(&module)?;

    let sys = py.import("sys")?;
    let modules = sys.getattr("modules")?;
    modules.set_item("finance_core.security", &module)?;

    Ok(())
}
