from app.models import AdminAudit


def log_admin(db, admin, action, target_user_id=None, detail=None):
    """Adds a line to the admin activity log. The caller commits."""
    db.add(
        AdminAudit(
            admin_id=admin.id,
            action=action,
            target_user_id=target_user_id,
            detail=detail,
        )
    )