# app/core/vector_store.py
from typing import List, Dict, Any

class VectorStore:
    def __init__(self): ...
    async def upsert_code_embeddings(self, items: List[Dict[str, Any]]): return 0
    async def search_similar(self, query_embedding: list, k: int = 5): return []
