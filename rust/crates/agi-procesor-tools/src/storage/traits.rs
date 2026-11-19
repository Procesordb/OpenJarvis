//! MemoryBackend trait for all storage backends.

use agi_procesor_core::{AgiProcesorError, RetrievalResult};
use serde_json::Value;

pub trait MemoryBackend: Send + Sync {
    fn backend_id(&self) -> &str;
    fn store(
        &self,
        content: &str,
        source: &str,
        metadata: Option<&Value>,
    ) -> Result<String, AgiProcesorError>;
    fn retrieve(
        &self,
        query: &str,
        top_k: usize,
    ) -> Result<Vec<RetrievalResult>, AgiProcesorError>;
    fn delete(&self, doc_id: &str) -> Result<bool, AgiProcesorError>;
    fn clear(&self) -> Result<(), AgiProcesorError>;
    fn count(&self) -> Result<usize, AgiProcesorError>;
}
