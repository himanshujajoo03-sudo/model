"""
Verification router — POST /verification
Admin actions: verify, reject, flag suspicious, mark duplicate, needs_review.

Per 04_API_CONTRACT.md §14 and 03_KAFKA_CONTRACT.md §6.1.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import get_db
from routers.auth import get_current_admin
from api.services.verification_outbox import enqueue

router = APIRouter(tags=["verification"])

ALLOWED_ACTIONS = {
    "verified",
    "rejected",
    "marked_suspicious",
    "marked_duplicate",
    "needs_review",
}

ACTION_TO_STATUS = {
    "verified": "verified",
    "rejected": "needs_review",  # rejection is a form of needing review
    "marked_suspicious": "suspicious",
    "marked_duplicate": "duplicate",
    "needs_review": "needs_review",
}


class VerificationRequest(BaseModel):
    event_id: str = Field(..., description="UUID of the canonical event to verify")
    action: str = Field(
        ...,
        description="Verification action: verified, rejected, marked_suspicious, marked_duplicate, needs_review",
    )
    performed_by: Optional[str] = Field(None, description="Ignored; authenticated admin identity is authoritative")
    notes: Optional[str] = Field(None, description="Optional human-readable notes")


class VerificationResponse(BaseModel):
    event_id: str
    old_status: str
    new_status: str
    action: str
    performed_by: str
    notes: Optional[str] = None
    performed_at: str
    log_id: str


@router.post("/verification", response_model=VerificationResponse)
async def verify_event(req: VerificationRequest, admin: str = Depends(get_current_admin)):
    """Admin verify/reject/flag action — updates canonical event and logs to verification_log."""

    # Validate action
    if req.action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_ACTION",
                    "message": f"Invalid action: {req.action}. Allowed: {', '.join(sorted(ALLOWED_ACTIONS))}",
                }
            },
        )

    # Validate UUID
    try:
        event_uuid = uuid.UUID(req.event_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_UUID", "message": f"Invalid UUID: {req.event_id}"}},
        )

    new_status = ACTION_TO_STATUS[req.action]
    now = datetime.now(timezone.utc)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # 1. Fetch current status
                cur.execute(
                    "SELECT verification_status FROM canonical_events WHERE canonical_event_id = %s",
                    (str(event_uuid),),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail={
                        "error": {"code": "EVENT_NOT_FOUND", "message": f"Event not found: {req.event_id}"}
                    })
                old_status = row[0] or "pending"

                # 2. Update canonical event
                cur.execute(
                    """UPDATE canonical_events
                       SET verification_status = %s,
                           verified_by = %s,
                           verification_timestamp = %s,
                           updated_at = NOW()
                       WHERE canonical_event_id = %s""",
                    (new_status, req.performed_by, now, str(event_uuid)),
                )

                # 3. Log to verification_log (for each contributing source event)
                cur.execute(
                    "SELECT event_id FROM events WHERE canonical_event_id = %s",
                    (str(event_uuid),),
                )
                source_event_ids = [r[0] for r in cur.fetchall()]

                log_ids = []
                performed_by = admin
                for source_event_id in source_event_ids:
                    entry_id = str(uuid.uuid4())
                    cur.execute(
                        """INSERT INTO verification_log (log_id, event_id, action, performed_by, notes, performed_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (entry_id, str(source_event_id), req.action, performed_by, req.notes, now),
                    )
                    log_ids.append(entry_id)

                outbox_payload = {
                    "event_id": req.event_id, "action": req.action,
                    "old_status": old_status, "new_status": new_status,
                    "performed_by": performed_by, "notes": req.notes,
                    "performed_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                }
                outbox_id = enqueue(conn, req.event_id, req.action, outbox_payload)

                return VerificationResponse(
                    event_id=req.event_id,
                    old_status=old_status,
                    new_status=new_status,
                    action=req.action,
                    performed_by=admin,
                    notes=req.notes,
                    performed_at=now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    log_id=(log_ids[0] if log_ids else outbox_id),
                )

    except HTTPException:
        raise
    except Exception as e:
        import traceback, sys
        # Log the full exception server-side; never expose internals to the client.
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Verification failed — database unavailable. Check the API logs for details.",
                }
            },
        )
