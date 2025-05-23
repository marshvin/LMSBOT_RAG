import os
from typing import Any, Dict, List
from flask import Blueprint, jsonify, current_app, request

# JWT
import jwt
import psycopg2
from urllib.parse import urlparse

MOODLE_JWT_SECRET = os.getenv("MOODLE_JWT_SECRET", "your_jwt_secret_here") 
# Get Moodle user ID from JWT token
def extract_moodle_user_id():
    auth_header = request.headers.get('Authorization', None)
    if not auth_header:
        return None
    try:
        # Expect header like: Authorization: Bearer <token>
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, MOODLE_JWT_SECRET, algorithms=["HS256"])
        # Moodle user id assumed in payload, e.g., 'user_id' or 'sub'
        return payload.get('user_id') or payload.get('sub')
    except Exception as e:
        print(f"JWT decode error: {e}")
        return None 

# Connection to the db
def get_db():
    """
    Parse the database URL and return a psycopg2 connection.
    Example db_url: postgresql://user:pass@host:port/dbname
    """
    db_url: str = os.getenv("DATABASE_URL")
    result = urlparse(db_url)
    username = result.username
    password = result.password
    database = result.path[1:]  # skip leading /
    hostname = result.hostname
    port = result.port

    conn = psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    return conn



quiz_bp = Blueprint('quiz', __name__, url_prefix='/api')



@quiz_bp.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    try:
        data = request.get_json()

        # Ensure it's a dictionary and contains the keys we need
        if not isinstance(data, dict) or "mcqs" not in data or "user_answers" not in data:
            return jsonify({"error": "Invalid payload format. Must contain 'mcqs' and 'user_answers'."}), 400

        mcqs = data["mcqs"]
        user_answers = data["user_answers"]

        result = evaluate_and_store_mcq_score(mcqs, user_answers)
        if "error" in result:
            return jsonify(result), result.get("status_code", 400)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


def evaluate_and_store_mcq_score(mcqs: List[Dict[str, Any]], user_answers: List[str]) -> Dict[str, Any]:
    """
    Evaluate the user's answers and store the result in the database.

    Args:
        mcqs: List of MCQs with correct answers.
        user_answers: List of answers submitted by the user.

    Returns:
        Dict with score and results.
    """
    user_id = extract_moodle_user_id()
    if not user_id:
        return {"error": "Unauthorized", "status_code": 401}

    score = 0
    for i, mcq in enumerate(mcqs):
        correct = mcq.get("answer")
        given = user_answers[i] if i < len(user_answers) else None
        if correct == given:
            score += 1

    total = len(mcqs)

    try:
        conn = get_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO quiz_results (user_id, score, total, timestamp)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (user_id, score, total)
                )
    except Exception as e:
        print(f"DB insert error: {e}")
        return {"error": "Database error", "status_code": 500}
    finally:
        if conn:
            conn.close()

    return {
        "score": score,
        "total": total,
        "message": "Score saved successfully",
        "user_id": user_id
    }
@quiz_bp.route("/get_quiz_results", methods=["GET"])
def get_quiz_results():
    """
    Get quiz results for the logged-in user.
    """
    user_id = extract_moodle_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized", "status_code": 401})

    try:
        conn = get_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT score, total, timestamp
                    FROM quiz_results
                    WHERE user_id = %s
                    """,
                    (user_id,)
                )
                results = cur.fetchall()
    except Exception as e:
        print(f"DB fetch error: {e}")
        return jsonify({"error": "Database error", "status_code": 500})
    finally:
        if conn:
            conn.close()

    return jsonify({
        "results": [
            {
                "score": row[0],
                "total": row[1],
                "timestamp": row[2]
            } for row in results
        ]
    })