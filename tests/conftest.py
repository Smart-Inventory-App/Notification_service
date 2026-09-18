import json
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# `app.core.firebase` inicializa el SDK al importarse, así que las credenciales
# tienen que existir antes de importar la app. Se arma una cuenta de servicio
# falsa con una clave RSA descartable: el SDK la valida pero no sale a la red.
_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_pem = _key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_notification.db")
os.environ.setdefault(
    "FIREBASE_CREDENTIALS",
    json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test",
            "private_key": _pem,
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "0",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    ),
)
