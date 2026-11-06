#![forbid(unsafe_code)]
#![allow(non_camel_case_types)]

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyValueError};
use pyo3::prelude::*;
use pyo3::pybacked::PyBackedBytes;
use pyo3::types::PyBytes;
use zlib_rs::{
    Deflate, DeflateConfig, DeflateFlush, Inflate, InflateError, InflateFlush, Status, Strategy,
};

create_exception!(_zlib_rust, error, PyException);

fn deflate_flush(mode: u8) -> PyResult<DeflateFlush> {
    match mode {
        0 => Ok(DeflateFlush::NoFlush),
        1 => Ok(DeflateFlush::PartialFlush),
        2 => Ok(DeflateFlush::SyncFlush),
        3 => Ok(DeflateFlush::FullFlush),
        4 => Ok(DeflateFlush::Finish),
        5 => Ok(DeflateFlush::Block),
        _ => Err(error::new_err("Invalid flush mode")),
    }
}

fn counter_delta(after: u64, before: u64) -> usize {
    // Old engines use 32-bit counters on Windows; each call handles at most 1 GiB.
    (after as u32).wrapping_sub(before as u32) as usize
}

#[pyclass]
struct Encoder {
    state: Deflate,
}

#[pymethods]
impl Encoder {
    #[new]
    fn new(
        level: i32,
        wbits: i32,
        dictionary: PyBackedBytes,
        mem_level: i32,
        strategy: i32,
    ) -> PyResult<Self> {
        let config = DeflateConfig {
            level,
            window_bits: wbits,
            mem_level,
            strategy: Strategy::try_from(strategy)
                .map_err(|_| PyValueError::new_err("Invalid strategy"))?,
            ..DeflateConfig::default()
        };
        let mut state = Deflate::new_with_config(config);
        if !dictionary.is_empty() {
            state
                .set_dictionary(dictionary.as_ref())
                .map_err(|err| error::new_err(err.as_str()))?;
        }
        Ok(Self { state })
    }

    fn process<'py>(
        &mut self,
        py: Python<'py>,
        input: PyBackedBytes,
        mode: u8,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let flush = deflate_flush(mode)?;
        let output = py.detach(|| {
            let mut output = Vec::new();
            let mut offset = 0;
            loop {
                let mut buffer = [0u8; 16384];
                let before_in = self.state.total_in();
                let before_out = self.state.total_out();
                let end = input.len().min(offset + (1 << 30));
                let current_flush = if end < input.len() {
                    DeflateFlush::NoFlush
                } else {
                    flush
                };
                let status = self
                    .state
                    .compress(&input[offset..end], &mut buffer, current_flush)
                    .map_err(|err| error::new_err(err.as_str()))?;
                let consumed = counter_delta(self.state.total_in(), before_in);
                let written = counter_delta(self.state.total_out(), before_out);
                offset += consumed;
                output.extend_from_slice(&buffer[..written]);
                if status == Status::StreamEnd || (offset == input.len() && written < buffer.len())
                {
                    break;
                }
                if consumed == 0 && written == 0 {
                    return Err(error::new_err("Compressor made no progress"));
                }
            }
            Ok::<_, PyErr>(output)
        })?;
        Ok(PyBytes::new(py, &output))
    }
}

#[pyclass]
struct Decoder {
    state: Inflate,
    dictionary: PyBackedBytes,
}

#[pymethods]
impl Decoder {
    #[new]
    fn new(wbits: i32, dictionary: PyBackedBytes) -> PyResult<Self> {
        let mut state = Inflate::new(wbits >= 0, wbits.unsigned_abs() as u8);
        if wbits < 0 && !dictionary.is_empty() {
            state
                .set_dictionary(dictionary.as_ref())
                .map_err(|err| error::new_err(err.as_str()))?;
        }
        Ok(Self { state, dictionary })
    }

    fn process<'py>(
        &mut self,
        py: Python<'py>,
        input: PyBackedBytes,
        max_length: usize,
        flushing: bool,
    ) -> PyResult<(Bound<'py, PyBytes>, usize, bool)> {
        let (output, consumed, finished) = py.detach(|| {
            let mut output = Vec::new();
            let mut offset = 0;
            let mut finished = false;
            loop {
                let remaining = if max_length == 0 {
                    16384
                } else {
                    (max_length - output.len()).min(16384)
                };
                if remaining == 0 {
                    break;
                }
                let mut buffer = vec![0u8; remaining];
                let before_in = self.state.total_in();
                let before_out = self.state.total_out();
                let end = input.len().min(offset + (1 << 30));
                let flush = if flushing && end == input.len() {
                    InflateFlush::Finish
                } else {
                    InflateFlush::SyncFlush
                };
                let result = self
                    .state
                    .decompress(&input[offset..end], &mut buffer, flush);
                let consumed = counter_delta(self.state.total_in(), before_in);
                let written = counter_delta(self.state.total_out(), before_out);
                offset += consumed;
                output.extend_from_slice(&buffer[..written]);
                let status = match result {
                    Err(InflateError::NeedDict { .. })
                        if !flushing && !self.dictionary.is_empty() =>
                    {
                        self.state
                            .set_dictionary(self.dictionary.as_ref())
                            .map_err(|err| error::new_err(err.as_str()))?;
                        continue;
                    }
                    result => result.map_err(|err| {
                        error::new_err(self.state.error_message().unwrap_or(err.as_str()))
                    })?,
                };
                if status == Status::StreamEnd {
                    finished = true;
                    break;
                }
                if consumed == 0 && written == 0 {
                    break;
                }
            }
            Ok::<_, PyErr>((output, offset, finished))
        })?;
        Ok((PyBytes::new(py, &output), consumed, finished))
    }
}

#[pyfunction]
fn adler32(py: Python<'_>, data: PyBackedBytes, value: u32) -> u32 {
    py.detach(|| zlib_rs::adler32::adler32(value, data.as_ref()))
}

#[pyfunction]
fn crc32(py: Python<'_>, data: PyBackedBytes, value: u32) -> u32 {
    py.detach(|| zlib_rs::crc32::crc32(value, data.as_ref()))
}

#[pyfunction]
fn adler32_combine(first: u32, second: u32, length: u64) -> u32 {
    zlib_rs::adler32::adler32_combine(first, second, length)
}

#[pyfunction]
fn crc32_combine(first: u32, second: u32, length: i64) -> PyResult<u32> {
    if length < 0 {
        return Err(PyValueError::new_err("length must be non-negative"));
    }
    Ok(zlib_rs::crc32::crc32_combine(first, second, length as u64))
}

#[pymodule]
fn _zlib_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("error", m.py().get_type::<error>())?;
    m.add_class::<Encoder>()?;
    m.add_class::<Decoder>()?;
    m.add_function(wrap_pyfunction!(adler32, m)?)?;
    m.add_function(wrap_pyfunction!(crc32, m)?)?;
    m.add_function(wrap_pyfunction!(adler32_combine, m)?)?;
    m.add_function(wrap_pyfunction!(crc32_combine, m)?)?;
    Ok(())
}
