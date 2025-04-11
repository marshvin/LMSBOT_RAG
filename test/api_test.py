import os
import sys
import pytest
from flask import Flask
from unittest.mock import patch, MagicMock
import importlib.metadata

# Ensure parent folder is in sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Patch werkzeug.__version__ if needed (for older dependencies)
import werkzeug
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = importlib.metadata.version("werkzeug")

# Import after path fixes
from api import routes


@pytest.fixture
def app():
    """Create a Flask test app with blueprint registered"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(routes.api)
    return app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_doc():
    """Return a mock document object similar to Pinecone results"""
    mock = MagicMock()
    mock.text = "This is the document content."
    mock.metadata = {
        "source_type": "youtube",
        "url": "https://youtube.com/example",
        "start_time": 30,
        "title": "Test Video"
    }
    mock.score = 0.95
    return mock


@patch("services.vector_service")
@patch("services.llm_service")
def test_valid_query(mock_llm, mock_vector, client, mock_doc):
    mock_vector.query_index.return_value = [mock_doc]
    mock_llm.generate.return_value = "This is the AI-generated answer."

    payload = {
        "query": "What is climate change?",
        "filters": {"source_type": "youtube"}
    }

    response = client.post("/query", json=payload)
    data = response.get_json()

    assert response.status_code == 200
    assert data["answer"] == "This is the AI-generated answer."
    assert "sources" in data and len(data["sources"]) > 0
    assert data["sources"][0]["type"] == "youtube"
    assert "query_id" in data


@patch("services.vector_service")
def test_missing_query_key(mock_vector, client):
    response = client.post("/query", json={"no_query": "..."})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Missing 'query' in request body"


@patch("services.vector_service")
def test_empty_query_string(mock_vector, client):
    response = client.post("/query", json={"query": "   "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Query cannot be empty"


@patch("services.vector_service")
@patch("services.llm_service")
def test_internal_server_error(mock_llm, mock_vector, client):
    mock_vector.query_index.side_effect = Exception("Something went wrong")

    payload = {"query": "Trigger error"}
    response = client.post("/query", json=payload)
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "Failed to process query"
    assert data["details"] == "Something went wrong"
