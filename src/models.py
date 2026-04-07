"""
models.py — MongoDB migration shim

All models are now stored in MongoDB (PyMongo).
This file is kept for compatibility but no longer uses SQLAlchemy.
See src/database.py for the MongoDB connection.
See src/services/ for all data access logic.
"""

# No SQLAlchemy — nothing to import.
# Kept as a placeholder so any stale imports don't break.
