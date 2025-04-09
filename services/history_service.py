import psycopg2
from datetime import datetime

class ConversationHistoryService:
    def __init__(self, db_config):
        self.db_config = db_config
    
    def log_interaction(self, user_id, query, response, sources):
        """Store conversation context"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO training_history 
                    (user_id, query, response, sources, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, query, response, str(sources), datetime.now(datetime.now().tzinfo)))
                conn.commit()
    
    def get_history(self, user_id, limit=3):
        """Retrieve conversation context"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT query, response 
                    FROM training_history 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (user_id, limit))
                return cur.fetchall()