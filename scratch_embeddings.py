import os, math
from dotenv import load_dotenv
from google import genai

load_dotenv(".env.local")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
EMBED_MODEL = "gemini-embedding-001"

def embed(texts):
    r = client.models.embed_content(model=EMBED_MODEL, contents=texts)
    return [e.values for e in r.embeddings]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)))

# --- Experiment 1: is the length really fixed? ---
samples = [
    "GDPR",
    "A personal data breach must be reported within 72 hours.",
    "Data protection law " * 100,   # deliberately long
]
for s, v in zip(samples, embed(samples)):
    print(f"{len(v)} dims  <-  {s[:45]!r}")

# --- Experiment 2: does meaning beat keywords? ---
query = "How fast must I report a data leak?"
candidates = [
    "A personal data breach must be notified within 72 hours.",  # same meaning, ZERO shared keywords
    "The cat sat on the mat.",                                   # unrelated
    "Payment card data must be encrypted at rest.",              # same domain, different topic
]
qv = embed([query])[0]
ranked = sorted(zip(candidates, embed(candidates)), key=lambda p: cosine(qv, p[1]), reverse=True)

print(f"\nQuery: {query}")
for text, v in ranked:
    print(f"{cosine(qv, v):.3f}  {text}")
