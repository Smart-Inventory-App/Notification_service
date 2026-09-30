# Notification Service — Smart Inventory Platform

[![codecov](https://codecov.io/gh/Smart-Inventory-App/Notification_service/branch/main/graph/badge.svg?token=vix01ZuRav)](https://codecov.io/gh/Smart-Inventory-App/Notification_service)

Microservicio que entrega las alertas del inventario al usuario: una **notificación push** (Firebase Cloud Messaging) y mediante un SMTP configurado un **email** con el mismo mensaje. No guarda nada ni decide cuándo alertar: quien decide es `app_backend`, que llama a este servicio cuando un producto entra en una condición crítica.

## Stack

- Python 3.11 + FastAPI
- `firebase_admin` para el push (FCM)
- `smtplib` (STARTTLS) para el email

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/notification/send_notification` | Envía el push y el email |
| `GET` | `/health` | Healthcheck: `{"status": "ok"}` |

### `POST /notification/send_notification`

```json
{
  "title": "Stock bajo",
  "body": "Te quedan 2 unidades de Leche entera",
  "token": "<token FCM del dispositivo>",
  "email": "usuario@ejemplo.com"
}
```

Responde `200` con `{"message": "Notification sent successfully"}`. Los cuatro campos son obligatorios.

## Comportamiento

- **Primero el push, después el email.** Si Firebase rechaza el envío (token vencido o inválido, credenciales mal), el endpoint responde **500** y el email **no se manda**.
- **El email es opcional.** Sin `SMTP_HOST` y `SMTP_USER` no se envía nada y no es un error: el push igual sale.
- **No hay reintentos ni cola.** Es un envío directo. `app_backend` lo trata como *best effort*: llama con un timeout de 10 s y ignora el fallo, así que una alerta puede perderse si este servicio no responde.
- **Firebase se inicializa una sola vez**, en el primer envío, a partir de `FIREBASE_CREDENTIALS`.

## Configuración

| Variable | Obligatoria | Descripción |
|----------|:-----------:|-------------|
| `JWT_SECRET` | ✅ | Requerida por la configuración |
| `FIREBASE_CREDENTIALS` | ✅ | **JSON completo** de la cuenta de servicio de Firebase, en una sola línea |
| `JWT_ALGORITHM` | | Por defecto `HS256` |
| `SMTP_HOST`, `SMTP_PORT` | | Por defecto puerto `587` |
| `SMTP_USER`, `SMTP_PASSWORD` | | Credenciales SMTP |
| `SMTP_FROM` | | Remitente; si falta se usa `SMTP_USER` |

Sin `JWT_SECRET` o sin `FIREBASE_CREDENTIALS` el servicio **no arranca**. `FIREBASE_CREDENTIALS` es un secreto: se define en el `.env` local o en el panel del cloud, nunca en el repositorio.

## Correr el Servicio

```bash
# Local
pip install -r requirements.txt
uvicorn app.main:app --port 8010

# Docker (requiere la red tpp-net)
docker compose up --build
```

Con Docker el servicio queda en el puerto `8010`. `app_backend` lo encuentra con `NOTIFICATION_SERVICE_URL` (por defecto `http://localhost:8010/notification`, ya con el prefijo de la ruta).

En Railway el puerto lo inyecta la plataforma (`PORT`) y el healthcheck es `/health`.

## Tests

```bash
pip install pytest pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

El CI exige **90 %** de coverage y sube el reporte a Codecov. Los tests reemplazan Firebase y SMTP, así que no necesitan credenciales.
