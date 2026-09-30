import json

from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock
from app.core.email import send_email 
from app.core import firebase 
from app.main import app

def test_send_email_success():
    with patch("smtplib.SMTP") as mock_smtp:

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_email("destinatario@test.com", "Asunto", "Cuerpo del mensaje")


        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

def test_send_email_no_config(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.SMTP_HOST", None)
    monkeypatch.setattr("app.core.config.settings.SMTP_USER", None)

    result = send_email("dest@test.com", "Asunto", "Body")
    assert result is None

def test_get_app_existing_app(monkeypatch):
    monkeypatch.setattr("firebase_admin._apps", [True])
    with patch("firebase_admin.get_app", return_value="fake_app"):
        app = firebase._get_app()
        assert app == "fake_app"

def test_get_app_initialize(monkeypatch):
    monkeypatch.setattr("firebase_admin._apps", [])

    with patch("firebase_admin.initialize_app", return_value="fake_app"):
        app = firebase._get_app()
        assert app == "fake_app"


def test_send_push_success():
    fake_token = "abc123"

    with patch("app.core.firebase._get_app", return_value="fake_app"), \
         patch("app.core.firebase.messaging.send") as mock_send:
        mock_send.return_value = "mock_message_id"

        result = firebase.send_push(fake_token, "Hola", "Mensaje de prueba")

        assert result == "mock_message_id"
        mock_send.assert_called_once()

def test_send_push_failure():
    with patch("app.core.firebase._get_app", return_value="fake_app"), \
         patch("app.core.firebase.messaging.send") as mock_send:
        mock_send.side_effect = Exception("Invalid token")

        with pytest.raises(Exception) as excinfo:
            firebase.send_push("bad_token", "Hola", "Mensaje de prueba")

        assert "Invalid token" in str(excinfo.value)

client = TestClient(app)

def test_send_notification_success():
    payload = {
        "token": "fake_token",
        "title": "Prueba",
        "body": "Mensaje de prueba",
        "email": "dest@test.com"
    }

    with patch("app.routes.notification.send_push") as mock_push, \
         patch("app.routes.notification.send_email") as mock_email:
        mock_push.return_value = "mock_message_id"
        mock_email.return_value = None

        response = client.post("/notification/send_notification", json=payload)

        assert response.status_code == 200
        assert response.json() == {"message": "Notification sent successfully"}
        mock_push.assert_called_once_with("fake_token", "Prueba", "Mensaje de prueba")
        mock_email.assert_called_once_with("dest@test.com", "Prueba", "Mensaje de prueba")