use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use serde_json::Value;
use std::path::PathBuf;

/// 通用的 Python 调用桥接
pub struct PyBridge {
    pub python_path: PathBuf,
}

impl PyBridge {
    pub fn new(python_path: PathBuf) -> Self {
        Self { python_path }
    }

    pub fn call(&self, module_name: &str, func_name: &str, args: Value) -> Result<Value, String> {
        Python::with_gil(|py| {
            // 1. 动态设置路径，确保能 import 你的 src-python
            let sys = py.import_bound("sys").map_err(|e| e.to_string())?;
            let path: Vec<String> = sys.getattr("path").unwrap().extract().unwrap();

            let py_src = self.python_path.to_str().unwrap();
            if !path.contains(&py_src.to_string()) {
                sys.getattr("path")
                    .unwrap()
                    .call_method1("append", (py_src,))
                    .unwrap();
            }

            // 2. 导入目标模块
            // 比如如果你传 "storage.get_layout"，这里会处理模块和函数名
            let module = py
                .import_bound(module_name)
                .map_err(|e| format!("Module {} not found: {}", module_name, e))?;

            // 3. 将 JSON 参数转为 Python 字典
            let kwargs = PyDict::new_bound(py);
            if let Value::Object(map) = args {
                for (k, v) in map {
                    kwargs.set_item(k, v.to_string()).unwrap(); // 简单处理，实际可用 json.loads
                }
            }

            // 4. 执行并获取结果
            let result = module
                .call_method(func_name, (), Some(&kwargs))
                .map_err(|e| e.to_string())?;

            // 5. 将结果转回 JSON
            let json_res: String = py
                .import_bound("json")
                .unwrap()
                .call_method1("dumps", (result,))
                .unwrap()
                .extract()
                .unwrap();

            Ok(serde_json::from_str(&json_res).unwrap())
        })
    }
}
