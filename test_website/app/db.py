import psycopg2
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

def get_connection():
    return psycopg2.connect(
        SUPABASE_URL.replace("https://", ""),
        user="postgres",
        password=SUPABASE_SERVICE_KEY,
        sslmode="require"
    )
