from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Notification, User
from app.schemas.schemas import NotificationReadPayload

router = APIRouter()


@router.get('/{user_id}')
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(50).all()


@router.post('/mark-read')
def mark_notification_read(payload: NotificationReadPayload, db: Session = Depends(get_db)):
    note = db.query(Notification).filter(Notification.id == payload.notification_id).first()
    if not note:
        raise HTTPException(status_code=404, detail='Notification not found')
    note.read = True
    db.commit()
    return {'message': 'Notification marked as read'}
