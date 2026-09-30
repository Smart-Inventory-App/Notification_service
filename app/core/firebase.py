import json

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

_app = None


def _get_app():
    global _app
    if _app is None:
        if firebase_admin._apps:
            _app = firebase_admin.get_app()
        else:
            cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS))
            _app = firebase_admin.initialize_app(cred)
    return _app


def send_push(token: str, title: str, body: str):
    app = _get_app()
    message = messaging.Message(
        notification=messaging.Notification(title, body),
        token=token
    )
    return messaging.send(message, app=app)
