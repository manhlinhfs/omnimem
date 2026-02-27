import argparse
import chromadb
from chromadb.utils import embedding_functions
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".omnimem_db")

def search_memory(query, n_results=5, full=False, as_json=False):
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)
    
    results = collection.query(query_texts=[query], n_results=n_results)
    
    if not results['documents'] or not results['documents'][0]:
        if as_json:
            print(json.dumps([]))
        else:
            print("No results found in OmniMem.")
        return

    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    ids = results['ids'][0]
    
    if as_json:
        out_data = []
        for i, doc in enumerate(documents):
            out_data.append({
                "id": ids[i],
                "distance": distances[i] if distances else 0.0,
                "content": doc,
                "metadata": metadatas[i] if metadatas else {}
            })
        print(json.dumps(out_data, ensure_ascii=False, indent=2))
        return

    print(f"""
[OmniMem Search]: '{query}'""")
    print("""
--- FOUND MEMORIES ---""")
    for i, doc in enumerate(documents):
        meta = metadatas[i] if metadatas else {}
        dist = distances[i] if distances else 0.0
        print(f"[{i+1}] ID: {ids[i]} (Distance: {dist:.4f})")
        print(f"""Content:
{doc}""" if full else f"Content: {doc[:200]}..." if len(doc) > 200 else f"Content: {doc}")
        print(f"""Source: {meta.get('source', 'N/A')} | Time: {meta.get('timestamp', 'N/A')}
""" + "-"*30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search OmniMem's knowledge base")
    parser.add_argument("query", help="The search query")
    parser.add_argument("--n", type=int, default=5, help="Number of results")
    parser.add_argument("--full", action="store_true", help="Print full content without truncating")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()
    search_memory(args.query, args.n, args.full, args.json)
