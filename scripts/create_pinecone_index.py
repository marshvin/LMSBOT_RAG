import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

def create_index():
    # Load environment variables
    load_dotenv()
    
    # Initialize Pinecone with new syntax
    pc = Pinecone(
        api_key=os.getenv('PINECONE_API_KEY')
    )
    
    # Get index name from environment
    index_name = os.getenv('PINECONE_INDEX_NAME')
    
    # Check if index already exists
    if index_name in pc.list_indexes().names():
        print(f"Index '{index_name}' already exists")
        return
    
    try:
        # Create the index with new syntax
        pc.create_index(
            name=index_name,
            dimension=384,  # all-MiniLM-L6-v2 dimension size
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region=os.getenv('PINECONE_ENVIRONMENT')  # us-east-1
            )
        )
        print(f"Successfully created index: {index_name}")
    except Exception as e:
        print(f"Error creating index: {str(e)}")

if __name__ == "__main__":
    create_index()