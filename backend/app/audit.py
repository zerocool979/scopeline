from .models import AuditLog


def log(db, user, action: str, entity: str = "", entity_id: int | None = None,
        detail: str = "", username: str | None = None):
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=(user.username if user else (username or "-"))[:64],
        action=action, entity=entity, entity_id=entity_id, detail=(detail or "")[:1000],
    ))
