"""
Shared FastAPI dependencies.
"""

from backend.database import get_db

# Re-export for consistent imports
__all__ = ["get_db"]