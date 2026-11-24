import json

from app import db
from app.ds.stack import Stack
from app.models import EntryAction


def build_undo_stack(user_id):
    """Build the user's undo stack in chronological database order."""
    actions = (
        EntryAction.query.filter_by(user_id=user_id)
        .order_by(EntryAction.created_at.asc(), EntryAction.id.asc())
        .all()
    )
    stack = Stack()
    for action in actions:
        stack.push(action)
    return stack


def record_action(user_id, action, payload):
    """Persist an undo action in the same transaction as its caller."""
    entry = EntryAction(
        user_id=user_id,
        aksi=action,
        payload_json=json.dumps(payload, separators=(",", ":"), sort_keys=True),
    )
    db.session.add(entry)
    return entry
