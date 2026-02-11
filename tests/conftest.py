"""
Shared pytest fixtures for ty_learn tests.
"""
import os
import pytest
from dotenv import load_dotenv

# Load .env once for all tests
load_dotenv()


@pytest.fixture(scope="session")
def db_conn():
    """Provide a real DB connection for integration tests.
    
    Shared across the session to avoid connection churn.
    Rolled back after each test via the `db_txn` fixture.
    """
    from core.database import get_connection_raw, return_connection
    conn = get_connection_raw()
    yield conn
    return_connection(conn)


@pytest.fixture
def db_txn(db_conn):
    """Wrap each test in a transaction that gets rolled back.
    
    Usage:
        def test_something(db_txn):
            cur = db_txn.cursor()
            cur.execute("INSERT INTO ...")
            # Automatically rolled back after test
    """
    db_conn.rollback()  # Clear any pending state
    yield db_conn
    db_conn.rollback()  # Roll back whatever the test did
