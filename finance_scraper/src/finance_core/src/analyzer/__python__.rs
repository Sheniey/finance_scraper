
// use pyo3::prelude::*;
// use pyo3::exceptions::PyRuntimeError;
// use super::metrics;

// pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
//     let py = parent.py();
//     let module = PyModule::new(py, "analyzer")?;

//     module.add_function(wrap_pyfunction!(hash_password, &module)?)?;
//     module.add_function(wrap_pyfunction!(verify_password, &module)?)?;

//     parent.add_submodule(&module)?;

//     let sys = py.import("sys")?;
//     let modules = sys.getattr("modules")?;
//     modules.set_item("finance_core.analyzer", &module)?;

//     Ok(())
// }
