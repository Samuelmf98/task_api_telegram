import psycopg2
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def create_table_if_not_exists():
    try:

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'messages')"
        )
        table_exists = cur.fetchone()[0]

        if not table_exists:
            cur.execute(
                """
                CREATE TABLE messages (
                    id SERIAL PRIMARY KEY,
                    message_question VARCHAR,
                    message_content VARCHAR,
                    role VARCHAR,
                    created_date TIMESTAMP
                );
            """
            )
            conn.commit()

        cur.close()
        conn.close()
    except Exception as e:
        print("Error al crear la tabla:", e)
