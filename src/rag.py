import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


LLM_MODEL = "gemini-2.5-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
COLLECTION_NAME = "docs"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "sample-docs"


def load_chunks():
    chunks = []

    for path in sorted(DOCS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue

        text = path.read_text(encoding="utf-8")
        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]

        for paragraph in paragraphs:
            chunks.append({"text": paragraph, "source": path.name})

    return chunks


def main():
    if len(sys.argv) < 2:
        raise SystemExit(f'Usage: {sys.executable} src/rag.py "your question"')

    question = " ".join(sys.argv[1:])

    load_dotenv(PROJECT_ROOT / ".env")
    gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    chunks = load_chunks()
    if not chunks:
        raise SystemExit(f"No documents found in {DOCS_DIR}")

    # Embed every chunk once during ingestion.
    chunk_texts = [chunk["text"] for chunk in chunks]
    embedding_response = gemini.models.embed_content(
        model=EMBED_MODEL,
        contents=chunk_texts,
    )
    chunk_vectors = [embedding.values for embedding in embedding_response.embeddings]

    # Qdrant stores vectors and their source information in memory for this run.
    vector_size = len(chunk_vectors[0])
    qdrant = QdrantClient(":memory:")
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    points = []
    for point_id, (chunk, vector) in enumerate(zip(chunks, chunk_vectors)):
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={"text": chunk["text"], "source": chunk["source"]},
            )
        )
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)

    # Embed the question with the same model, then retrieve by vector index.
    question_response = gemini.models.embed_content(
        model=EMBED_MODEL,
        contents=[question],
    )
    question_vector = question_response.embeddings[0].values
    search_result = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=question_vector,
        limit=3,
        with_payload=True,
    )
    matches = search_result.points

    context_parts = []
    for index, match in enumerate(matches, start=1):
        context_parts.append(f"[{index}] {match.payload['text']}")
    context = "\n\n".join(context_parts)

    prompt = f"""Answer the question using ONLY the context below.
If the answer is not in the context, say so.

Context:
{context}

Question: {question}
Answer:"""

    answer = gemini.models.generate_content(model=LLM_MODEL, contents=prompt)

    print("\n--- ANSWER ---")
    print(answer.text)
    print("\n--- SOURCES ---")
    for number, match in enumerate(matches, start=1):
        source = match.payload["source"]
        snippet = match.payload["text"].replace("\n", " ")[:120]
        print(f"[{number}] {source}: {snippet}...")


if __name__ == "__main__":
    main()
