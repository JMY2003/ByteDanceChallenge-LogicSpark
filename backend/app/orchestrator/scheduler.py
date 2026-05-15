"""Scheduler extension point.

The MVP runs synchronously through FastAPI. This module exists so Redis/Celery,
Dramatiq or Temporal integration can reuse the same DAG executor contract.
"""

