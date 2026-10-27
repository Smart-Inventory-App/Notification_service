import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAND_BLUE = "#1B3A8F"

# Aclaración al final de todo de los mails que no son de cuenta (alertas): por qué llegan y cómo dejar de recibirlos
NOTIFICATIONS_NOTE = (
    "Recibís este mail porque tenés las notificaciones activadas. Si querés dejar de recibir estos mails, "
    "ingresa a la aplicación y desactiva las notificaciones."
)

# Qué significa cada aviso y qué conviene hacer. `kind` lo manda quien pide la notificación (app_backend);
# sin `kind` el mail lleva solo el título y el mensaje. `prediction` (solo en los avisos que estiman o calculan algo):
# cómo lo estima el sistema, dicho en simple y al final del mail.
KINDS = {
    "expiry": {
        "days_label": "Vence en",
        "label": "Vencimiento",
        "color": "#E8A317",
        "meaning": "Un producto de tu inventario está cerca de su fecha de vencimiento. Pasada esa fecha ya no conviene consumirlo.",
        "actions": [
            "Usalo primero, antes que los productos que vencen más tarde.",
            "Si no vas a llegar a consumirlo, pensá en compartirlo o en usarlo en alguna preparación.",
            "Si ya lo consumiste, actualizá el stock en la app para que las alertas reflejen la realidad.",
        ],
    },
    "low_coverage": {
        "days_label": "Se agotaría en",
        "label": "Stock por agotarse",
        "color": "#E5484D",
        "meaning": "Calculamos cuánto te va a durar el producto según tu ritmo de consumo y se va a terminar pronto.",
        "actions": [
            "Agregalo a tu próxima compra para no quedarte sin stock.",
            "Si ya lo repusiste, registrá la entrada en la app y la alerta se actualiza sola.",
            "Podés ajustar con cuántos días de anticipación querés estos avisos desde Perfil.",
        ],
        "prediction": (
            "Miramos cuánto sacás de este producto y cada cuánto, y lo comparamos con las unidades que te quedan. "
            "Con ese ritmo estimamos en cuántos días se te termina. Es una estimación: si cambia lo que consumís, "
            "el aviso también cambia."
        ),
    },
    "overstock": {
        "days_label": "Stock para",
        "label": "Exceso de stock",
        "color": "#237FA1",
        "meaning": "Después de tu última carga, la cantidad que tenés supera lo que vas a consumir en un tiempo razonable.",
        "actions": [
            "Evitá comprar más de este producto por ahora.",
            "Revisá su fecha de vencimiento para asegurarte de llegar a consumirlo.",
        ],
        "prediction": (
            "Miramos cuánto sacás de este producto y cada cuánto, y calculamos para cuántos días te alcanza lo que "
            "tenés. Si son muchos más de los que solés usar, te avisamos que quizás compraste de más. Es una "
            "estimación: si cambia lo que consumís, el aviso también cambia."
        ),
    },
    "understock": {
        "days_label": "Stock para",
        "label": "Stock insuficiente",
        "color": "#E8A317",
        "meaning": "Aun con la compra que acabás de registrar, el producto no te va a alcanzar para el período que suele cubrir.",
        "actions": [
            "Considerá comprar más unidades en tu próxima salida.",
            "Si la cantidad que cargaste no era la correcta, corregila desde el inventario.",
        ],
        "prediction": (
            "Miramos cuánto sacás de este producto y cada cuánto, y calculamos para cuántos días te alcanza lo que "
            "tenés después de esta compra. Si son menos de los que suele cubrir, te avisamos que quizás compraste de "
            "menos. Es una estimación: si cambia lo que consumís, el aviso también cambia."
        ),
    },
    "slow_pace": {
        "days_label": "Vence en",
        "label": "Riesgo de vencimiento",
        "color": "#E8A317",
        "meaning": "Al ritmo en que lo consumís, el producto no se va a terminar antes de vencerse y parte del stock se perdería.",
        "actions": [
            "Priorizá consumir este producto en los próximos días.",
            "Evitá comprar más hasta que se normalice el stock.",
            "Si podés, compartilo o usalo en alguna preparación antes de que venza.",
        ],
        "prediction": (
            "Miramos cuánto sacás de este producto y cada cuánto, y vemos si lo vas a terminar antes de que venza. "
            "Si no, estimamos cuántas unidades quedarían sin usar. Es una estimación: si cambia lo que consumís, "
            "el aviso también cambia."
        ),
    },
}


def _logo_html() -> str:
    """Logo de la app arriba del mail. Sin EMAIL_LOGO_URL no se muestra nada (el mail sigue siendo válido)."""
    if not settings.EMAIL_LOGO_URL:
        return ""
    return (
        f'<img src="{escape(settings.EMAIL_LOGO_URL, quote=True)}" alt="Smart Inventory" width="220" '
        'style="display:block;margin:0 0 20px;">'
    )


def _plural(amount: int, singular: str, plural: str) -> str:
    return f"{amount} {singular if amount == 1 else plural}"


def _facts(info, product_name, days, units) -> list[str]:
    """Datos del aviso en lista, para que se vean de un vistazo (solo los que llegaron)."""
    facts = []
    if product_name:
        facts.append(f"Producto: {product_name}")
    if days is not None:
        facts.append(f"{info['days_label']}: {_plural(days, 'día', 'días')}")
    if units is not None:
        facts.append(f"Unidades en riesgo: {units}")
    return facts


def build_email(title: str, body: str, kind=None, product_name=None, days=None, units=None) -> tuple[str, str]:
    """Texto plano y HTML del mail de una alerta."""
    info = KINDS.get(kind)
    footer = NOTIFICATIONS_NOTE
    prediction = info.get("prediction") if info else None

    text_parts = [title, "", body]
    if info:
        facts = _facts(info, product_name, days, units)
        if facts:
            text_parts += ["", *facts]
        text_parts += ["", "Qué significa:", info["meaning"], "", "Qué podés hacer:"]
        text_parts += [f"- {action}" for action in info["actions"]]
    # Cómo se estima lo que avisa el mail (solo en los que estiman algo) y, abajo de todo, la aclaración de las notificaciones
    if prediction:
        text_parts += ["", "Cómo lo calculamos:", prediction]
    text_parts += ["", footer]
    text = "\n".join(text_parts)

    badge = ""
    detail = ""
    if info:
        badge = (
            f'<span style="display:inline-block;background:{info["color"]};color:#fff;font-size:12px;font-weight:bold;'
            f'padding:3px 10px;border-radius:12px;margin-bottom:10px;">{escape(info["label"])}</span>'
        )
        facts = _facts(info, product_name, days, units)
        facts_html = "".join(f'<li>{escape(fact)}</li>' for fact in facts)
        actions_html = "".join(f'<li style="margin-bottom:6px;">{escape(action)}</li>' for action in info["actions"])
        detail = f"""
  {f'<ul style="padding-left:20px;line-height:1.5;">{facts_html}</ul>' if facts else ''}
  <p style="margin-top:20px;"><strong>Qué significa</strong><br>{escape(info["meaning"])}</p>
  <p style="margin-top:20px;"><strong>Qué podés hacer</strong></p>
  <ul style="padding-left:20px;line-height:1.5;">{actions_html}</ul>"""

    prediction_html = (
        f'\n  <p style="color: #666; font-size: 13px; margin-top: 28px;"><strong>Cómo lo calculamos</strong><br>'
        f'{escape(prediction)}</p>'
        if prediction
        else ""
    )

    html = f"""
<html>
<body style="font-family: sans-serif; padding: 24px; color: #1a1a1a;">
  {_logo_html()}
  {badge}
  <h2 style="color: {BRAND_BLUE}; margin: 0 0 12px;">{escape(title)}</h2>
  <p style="font-size:16px;">{escape(body)}</p>{detail}
  {prediction_html}
  <p style="color: #888; font-size: 11px; margin-top: 28px;">{escape(footer)}</p>
</body>
</html>
"""
    return text, html


def send_email(to_email: str, subject: str, body: str, kind=None, product_name=None, days=None, units=None) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        # Sin SMTP no sale ningún mail: se avisa en el log para que no parezca que se envió
        logger.warning("SMTP no configurado (SMTP_HOST / SMTP_USER): no se envió el mail a %s", to_email)
        return

    text, html = build_email(subject, body, kind, product_name, days, units)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{subject} - Smart Inventory"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
