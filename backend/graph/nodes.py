"""
LangGraph node functions.

Each node is a function that receives the full AgentState dict and
returns a PARTIAL dict with only the keys it wants to update.
LangGraph merges the returned dict into the state automatically.
The graph is strictly linear: scrape_node → analyze_node → END.
There are no conditional edges and no loops, so infinite cycling
is structurally impossible.

Error convention:
  - If a node fails, it sets state["error"] to a descriptive string.
  - Downstream nodes check for state["error"] and short-circuit if set.
"""

from backend.graph.state import AgentState
from backend.tools.scraper import scrape_url
from backend.tools.analyzer import analyze_legal_text
from backend.tools.chunker import semantic_chunking, retrieve_top_k

# Predefined high-risk legal audit queries for vector search
TARGET_AUDIT_QUERIES = [
    "arbitration clause, class action waiver, governing law, and disputes resolution",
    "data sharing, user tracking, personal data collection, sale to third parties, and privacy",
    "subscription, auto-renewal, cancellations, fees, billing, billing frequency, and refunds",
    "intellectual property ownership, content licenses, account deletion, and service termination"
]


async def scrape_node(state: AgentState) -> dict:
    try:
        markdown = await scrape_url(state["url"])

        # Guard: if the page is nearly empty it's probably not a T&C page
        word_count = len(markdown.split())
        if word_count < 10:
            return {
                "markdown_content": "",
                "error": (
                    f"Page has only {word_count} words. "
                    "This doesn't look like a Terms & Conditions page."
                ),
            }

        return {"markdown_content": markdown, "error": None}

    except Exception as exc:
        return {"markdown_content": "", "error": f"Scrape error: {str(exc)}"}


def analyze_node(state: AgentState) -> dict:
    if state.get("error"):
        return {"error": state["error"]}

    try:
        raw_text = state["markdown_content"]
        word_count = len(raw_text.split())
        
        # Word threshold to trigger RAG pipeline (4,000 words ~ 16,000 characters)
        if word_count >= 4000:
            print(f"[CHUNKER] Large document detected ({word_count} words). Triggering Semantic Chunking & RAG...")
            
            # Step 1: Group sentences into semantically cohesive paragraphs
            chunks = semantic_chunking(raw_text)
            
            if len(chunks) >= 3:
                # Step 2: Retrieve top 3 relevant chunks per audit category
                retrieved_chunks = retrieve_top_k(chunks, TARGET_AUDIT_QUERIES, k=3)
                
                # Step 3: Combine matches into an optimized context
                processed_content = "\n\n---\n\n".join(retrieved_chunks)
                rag_word_count = len(processed_content.split())
                savings = (1 - (rag_word_count / word_count)) * 100
                
                print(f"[RAG] RAG complete. Context reduced from {word_count} to {rag_word_count} words ({savings:.2f}% token savings!).")
            else:
                print("[CHUNKER] Warning: Semantic chunking yielded too few chunks. Falling back to full text.")
                processed_content = raw_text
        else:
            print(f"[RAG] Document is small ({word_count} words). Analyzing full text for maximum precision.")
            processed_content = raw_text


        # Call the LLM Analyzer with the optimized content
        analysis = analyze_legal_text(processed_content)
        
        return {
            "score": analysis["score"],
            "grade": analysis["grade"],
            "summary": analysis["summary"],
            "findings": analysis["findings"],
            "error": None,
        }

    except Exception as exc:
        return {"error": f"Analysis error: {str(exc)}"}