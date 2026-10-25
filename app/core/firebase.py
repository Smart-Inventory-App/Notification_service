import json

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

_app = None

ANDROID_NOTIFICATION_ICON = "notification_icon"
BRAND_COLOR = "#2CC4B4"
WEB_NOTIFICATION_ICON = "/notification-icon-192.png"


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
        # Marca de Smart Inventory en el pop-up: ícono chico de la barra de estado de Android (el recurso que
        # genera el plugin de expo-notifications a partir de assets/notification-icon.png) y su color,
        # y el ícono de la notificación en el navegador.
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(icon=ANDROID_NOTIFICATION_ICON, color=BRAND_COLOR)
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(icon=WEB_NOTIFICATION_ICON)
        ),
        token=token
    )
    return messaging.send(message, app=app)
