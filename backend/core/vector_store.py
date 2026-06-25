"""Vector store for code embeddings."""
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import faiss
from .code_chunker import CodeChunk


class VectorStore:
    def __init__(self):
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index: Optional[faiss.Index] = None
        self.chunks: List[CodeChunk] = []

    def build_index(self, chunks: List[CodeChunk]):
        if not chunks:
            return

        self.chunks = chunks

        texts = []
        for chunk in chunks:
            text = f"File: {chunk.file_path}\nType: {chunk.chunk_type}\nName: {chunk.name}\n\n{chunk.content[:1500]}"
            texts.append(text)

        print(f"Embedding {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=False, batch_size=32)
        embeddings = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        print(f"Index built with {len(chunks)} chunks")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if self.index is None or not self.chunks:
            return []

        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks) and score > 0.15:
                chunk = self.chunks[idx]
                results.append({
                    'content': chunk.content,
                    'file_path': chunk.file_path,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'chunk_type': chunk.chunk_type,
                    'name': chunk.name,
                    'language': chunk.language,
                    'relevance_score': float(score)
                })

        return results

    def clear(self):
        self.index = None
        self.chunks = []


vector_store = VectorStore()
