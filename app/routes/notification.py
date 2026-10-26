from fastapi import APIRouter, status
from fastapi.security import HTTPBearer
from app.schemas.notification import NotificationBase
from app.core.firebase import send_push
from app.core.email import send_email

router = APIRouter(prefix="/notification", tags=["notification"])

@router.post("/send_notification", status_code=status.HTTP_200_OK)
async def send_notification(
        data: NotificationBase
):
    send_push(data.token, data.title, data.body)
    send_email(
        data.email, data.title, data.body,
        kind=data.kind, product_name=data.product_name, days=data.days, units=data.units,
    )
    return {"message": "Notification sent successfully"}

