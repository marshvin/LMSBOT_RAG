import json
import requests

def run_querry():
    url = "http://localhost:5000/api/query"  # Replace with your actual endpoint URL

    # Load the sample data from the file
    payload = {
        "query": "How does climate change affect agriculture?",
        "filters": {
            "source_type": "youtube"
        }
    }

    response = requests.post(url, json=payload)

    print("Response status code:", response.status_code)
    print("Response JSON:", response.json())
        

if __name__ == "__main__":
    run_querry()
