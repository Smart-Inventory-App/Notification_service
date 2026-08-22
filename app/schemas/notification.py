from pydantic import BaseModel

class NotificationBase(BaseModel):
    title: str
    body: str
    token: str
    email: str