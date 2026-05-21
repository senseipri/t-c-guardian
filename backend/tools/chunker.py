"""
Semantic chunking and transient RAG retrieval engine for T&C Guardian.

This module provides two primary functions:
1. semantic_chunking: Splits a long markdown legal document into semantically
   cohesive paragraphs based on sentence embeddings and cosine similarity drops.
2. retrieve_top_k: Performs an in-memory vector search over the generated chunks
   using target queries to pull highly relevant risk clauses.
"""

import re
import numpy as np
from fastembed import TextEmbedding

# Global embedding model cache to avoid reloading for every request
_embedder = None


def get_embedder() -> TextEmbedding:
    """
    Lazy-loads and returns the fastembed TextEmbedding model.
    Uses 'BAAI/bge-small-en-v1.5' by default (quantized ONNX, CPU-optimized, ~100MB).
    """
    global _embedder
    if _embedder is None:
        # Initializing will download the model to cache on first use
        _embedder = TextEmbedding()
    return _embedder


def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into individual sentences and list items.
    Preserves short headings and list structural prefixes (e.g. bullet points)
    without splitting them into fragmented parts.
    """
    if not text:
        return []
    
    paragraphs = text.split('\n')
    sentences = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If it's a heading, standard markdown list element, or very short, keep intact
        if para.startswith('#') or para.startswith(('-', '*', '+')) or len(para) < 60:
            sentences.append(para)
            continue
        
        # Split by standard sentence punctuation followed by spaces
        splits = re.split(r'(?<=[.!?])\s+', para)
        for s in splits:
            s = s.strip()
            if s:
                sentences.append(s)
                
    return sentences


def semantic_chunking(
    text: str,
    min_chunk_size: int = 200,
    max_chunk_size: int = 1500
) -> list[str]:
    """
    Groups document sentences into semantically cohesive chunks by analyzing the
    cosine similarity between consecutive sentence embeddings and placing split
    boundaries where statistical drops occur.

    Args:
        text: The raw scraped legal markdown text.
        min_chunk_size: Minimum characters required to allow a split (prevents tiny chunks).
        max_chunk_size: Maximum characters allowed before forcing a split (prevents giant chunks).

    Returns:
        List of semantically grouped paragraph chunks.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        return sentences

    # 1. Generate sentence embeddings
    embedder = get_embedder()
    embeddings_gen = embedder.embed(sentences)
    embeddings = np.array(list(embeddings_gen))

    # 2. Compute L2 normalized embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10  # prevent division by zero
    norm_embeddings = embeddings / norms

    # 3. Calculate cosine similarities between consecutive sentences
    similarities = []
    for i in range(len(norm_embeddings) - 1):
        sim = float(np.dot(norm_embeddings[i], norm_embeddings[i + 1]))
        similarities.append(sim)

    # 4. Adaptive thresholding: mean - 0.8 * standard_deviation
    if similarities:
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        threshold = mean_sim - 0.8 * std_sim
    else:
        threshold = 0.5

    # 5. Group sentences into chunks based on similarities and size constraints
    chunks = []
    current_chunk = []
    current_len = 0

    for i, sentence in enumerate(sentences):
        current_chunk.append(sentence)
        current_len += len(sentence)

        if i < len(sentences) - 1:
            sim = similarities[i]
            # Split if:
            # - Similarity is below drop threshold AND current chunk is large enough
            # - OR current chunk is exceeding the max size limit
            if (sim < threshold and current_len >= min_chunk_size) or current_len >= max_chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_len = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Clean and return non-empty chunks
    return [c.strip() for c in chunks if c.strip()]


def retrieve_top_k(
    chunks: list[str],
    queries: list[str],
    k: int = 3,
    min_similarity: float = 0.2
) -> list[str]:
    """
    Performs an in-memory vector search over the generated chunks for each query.
    Merges matching chunks and returns them in their original document order to preserve logical flow.

    Args:
        chunks: List of semantic chunks to search from.
        queries: List of search queries (representing audit categories).
        k: Number of top matching chunks to retrieve per query.
        min_similarity: Cut-off threshold to reject irrelevant chunks.

    Returns:
        Deduplicated list of retrieved chunks sorted in their original document order.
    """
    if not chunks or not queries:
        return []

    embedder = get_embedder()

    # Generate embeddings for both chunks and queries
    chunk_embeddings = np.array(list(embedder.embed(chunks)))
    query_embeddings = np.array(list(embedder.embed(queries)))

    # Normalise chunk embeddings
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    chunk_norms[chunk_norms == 0] = 1e-10
    norm_chunks = chunk_embeddings / chunk_norms

    # Normalise query embeddings
    query_norms = np.linalg.norm(query_embeddings, axis=1, keepdims=True)
    query_norms[query_norms == 0] = 1e-10
    norm_queries = query_embeddings / query_norms

    retrieved_indices = set()

    for query_vec in norm_queries:
        # Calculate dot products (cosine similarities because vectors are normalized)
        similarities = np.dot(norm_chunks, query_vec)
        
        # Sort indices in descending order of similarity
        top_indices = np.argsort(similarities)[::-1][:k]
        
        for idx in top_indices:
            # Filter out chunks that are below the minimal relevance threshold
            if similarities[idx] >= min_similarity:
                retrieved_indices.add(int(idx))

    # Sort indices to preserve original sequential document order
    sorted_indices = sorted(list(retrieved_indices))
    
    return [chunks[idx] for idx in sorted_indices]
