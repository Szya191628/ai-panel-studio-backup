"""Test configuration."""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import PanelDB


@pytest.fixture
def db():
    """Create a test database."""
    test_db_path = ":memory:"
    return PanelDB(test_db_path)


@pytest.fixture
def conn(db):
    """Create a test connection."""
    conn = db.connect()
    yield conn
    conn.close()
