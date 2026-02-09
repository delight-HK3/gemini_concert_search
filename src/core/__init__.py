"""Core module"""
from .config import settings
from .database import get_db, init_db
from .external_database import get_external_db, init_external_db

__all__ = ['settings', 'get_db', 'init_db', 'get_external_db', 'init_external_db']
