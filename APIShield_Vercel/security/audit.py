from datetime import datetime, timezone
from flask_login import current_user
from database.db import get_db


def log_event(resource_type, resource_id, action, decision, reason, *, commit=True, anonymous=False):
    """Only fixed metadata. Never log credentials, cookies, request bodies, or tokens."""
    authenticated = not anonymous and current_user.is_authenticated
    db = get_db()
    db.execute(
        "INSERT INTO security_events(user_id, company_id, resource_type, resource_id, action, decision, reason, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (current_user.id if authenticated else None,
         current_user.company_id if authenticated else None,
         resource_type, str(resource_id) if resource_id is not None else None,
         action, decision, reason, datetime.now(timezone.utc).isoformat(timespec="milliseconds")),
    )
    if commit:
        db.commit()
