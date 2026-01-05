import psycopg2
from psycopg2.pool import SimpleConnectionPool
from app.config import DATABASE_URL

# Create pool at startup
# Tune numbers based on expected load
POOL_MIN = 1
POOL_MAX = 10

_connection_pool = SimpleConnectionPool(
    POOL_MIN,
    POOL_MAX,
    dsn=DATABASE_URL,
    sslmode="require"
)

def get_connection():
    """
    Get a database connection from the pool.
    MUST be returned using put_connection().
    """
    return _connection_pool.getconn()

def put_connection(conn):
    """
    Return a connection to the pool.
    """
    _connection_pool.putconn(conn)
