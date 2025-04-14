import os

folder = "rag_components"
files = [
    "__init__.py",
    "document_processor.py",
    "pinecone_client.py",
    "embedding_service.py",
    "rag_engine.py",
    "youtube_loader.py"
]

os.makedirs(folder, exist_ok=True)

for file in files:
    path = os.path.join(folder, file)
    with open(path, "w") as f:
        f.write("# " + file)
