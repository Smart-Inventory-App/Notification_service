"""Contenido de los mails de alertas: descriptivos, con el logo y sin romper los pedidos que no traen datos extra."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core import email as email_mod
from app.core.config import settings
from app.core.email import KINDS, build_email, send_email
from app.main import app

client = TestClient(app)


def enviar(**kwargs):
    """Manda un mail con un SMTP falso y devuelve el mensaje armado."""
    with patch("smtplib.SMTP") as smtp:
        server = MagicMock()
        smtp.return_value.__enter__.return_value = server
        send_email("dest@test.com", "Titulo", "Cuerpo del aviso", **kwargs)
    return server.send_message.call_args.args[0]


def partes(msg):
    return {p.get_content_type(): p.get_payload(decode=True).decode() for p in msg.get_payload()}


# ── mails sin datos extra (como antes) ───────────────────────────────────────

def test_sin_kind_el_mail_lleva_titulo_y_mensaje_y_nada_mas():
    texto, html = build_email("Titulo", "Cuerpo del aviso")
    assert "Titulo" in texto and "Cuerpo del aviso" in texto
    assert "Qué significa" not in texto
    assert "Qué significa" not in html
    assert "Cuerpo del aviso" in html


def test_asunto_con_la_marca_y_remitente():
    msg = enviar()
    assert msg["Subject"] == "Titulo - Smart Inventory"
    assert msg["To"] == "dest@test.com"
    assert msg["From"] == (settings.SMTP_FROM or settings.SMTP_USER)


def test_el_mail_trae_texto_plano_y_html():
    contenido = partes(enviar())
    assert set(contenido) == {"text/plain", "text/html"}


AVISO = (
    "Recibís este mail porque tenés las notificaciones activadas. Si querés dejar de recibir estos mails, "
    "ingresa a la aplicación y desactiva las notificaciones."
)


def test_el_pie_explica_por_que_llega_y_como_desactivarlo():
    texto, html = build_email("T", "B")
    assert AVISO in texto
    assert AVISO in html


@pytest.mark.parametrize("kind", list(KINDS) + [None, "otra-cosa"])
def test_todos_los_mails_de_alerta_llevan_el_aviso_de_las_notificaciones(kind):
    texto, html = build_email("T", "B", kind=kind, product_name="Leche", days=3, units=2)
    assert AVISO in texto
    assert AVISO in html
    assert "Podés cambiarlo desde Perfil" not in texto


PREDICEN = ["low_coverage", "overstock", "understock", "slow_pace"]


@pytest.mark.parametrize("kind", PREDICEN)
def test_los_avisos_que_estiman_algo_explican_como_lo_calculan(kind):
    texto, html = build_email("T", "B", kind=kind, product_name="Leche", days=3, units=2)
    prediccion = KINDS[kind]["prediction"]
    assert "Cómo lo calculamos" in texto and "Cómo lo calculamos" in html
    assert prediccion in texto and prediccion in html
    assert texto.index("Cómo lo calculamos") > texto.index("Qué podés hacer")
    assert html.index("Cómo lo calculamos") > html.index("Qué podés hacer")


@pytest.mark.parametrize("kind", list(KINDS) + [None, "otra-cosa"])
def test_el_aviso_de_las_notificaciones_es_lo_ultimo_del_mail_y_en_letra_chica(kind):
    texto, html = build_email("T", "B", kind=kind, product_name="Leche", days=3, units=2)
    assert texto.rstrip().endswith(AVISO)
    # en el HTML, el último párrafo es la aclaración, con letra más chica que el resto
    ultimo = html[html.rindex("<p "):]
    assert AVISO in ultimo
    assert "font-size: 11px" in ultimo
    assert html.rindex("font-size: 11px") > html.rindex("Cómo lo calculamos") if "Cómo lo calculamos" in html else True


def test_la_aclaracion_es_mas_chica_que_el_resto_del_texto_secundario():
    _, html = build_email("T", "B", kind="low_coverage", product_name="Leche", days=3)
    assert html.count("font-size: 11px") == 1
    assert "Podés cambiarlo desde Perfil" not in html
    assert "vía mail" not in html


@pytest.mark.parametrize("kind", PREDICEN)
def test_la_explicacion_es_breve_y_sin_tecnicismos(kind):
    prediccion = KINDS[kind]["prediction"]
    assert len(prediccion) < 400
    for tecnico in ("modelo", "algoritmo", "machine", "regresión", "predicción", "ML"):
        assert tecnico.lower() not in prediccion.lower()


@pytest.mark.parametrize("kind", [None, "expiry", "otra-cosa"])
def test_los_avisos_que_no_estiman_nada_no_llevan_la_explicacion(kind):
    texto, html = build_email("T", "B", kind=kind, product_name="Leche", days=3)
    assert "Cómo lo calculamos" not in texto
    assert "Cómo lo calculamos" not in html


# ── mails descriptivos por tipo ──────────────────────────────────────────────

@pytest.mark.parametrize("kind", list(KINDS))
def test_cada_tipo_explica_que_significa_y_que_hacer(kind):
    texto, html = build_email("T", "B", kind=kind, product_name="Leche", days=3, units=2)
    info = KINDS[kind]
    assert "Qué significa" in texto and "Qué podés hacer" in texto
    assert info["meaning"] in texto
    assert info["label"] in html
    for accion in info["actions"]:
        assert accion in texto
        assert accion in html
    assert "Producto: Leche" in texto


def test_los_datos_del_aviso_se_muestran_en_lista():
    texto, html = build_email("T", "B", kind="expiry", product_name="Yogur", days=1)
    assert "Producto: Yogur" in texto
    assert "Vence en: 1 día" in texto
    assert "<li>Producto: Yogur</li>" in html


def test_los_dias_se_pluralizan():
    assert "3 días" in build_email("T", "B", kind="expiry", days=3)[0]
    assert "1 día" in build_email("T", "B", kind="expiry", days=1)[0]
    # nunca «0 días»: el mismo día se dice «hoy»
    assert "0 días" not in build_email("T", "B", kind="expiry", days=0)[0]
    assert "Vence en: hoy" in build_email("T", "B", kind="expiry", days=0)[0]


def test_slow_pace_muestra_las_unidades_en_riesgo():
    texto, _ = build_email("T", "B", kind="slow_pace", product_name="Pan", days=4, units=5)
    assert "Unidades en riesgo: 5" in texto
    assert "Vence en: 4 días" in texto


def test_sin_datos_no_hay_lista_de_datos_pero_si_explicacion():
    texto, html = build_email("T", "B", kind="low_coverage")
    assert "Producto:" not in texto
    assert "Qué significa" in html
    assert "<ul style=\"padding-left:20px;line-height:1.5;\"></ul>" not in html


def test_un_kind_desconocido_se_trata_como_mail_simple():
    texto, _ = build_email("T", "B", kind="otra-cosa", product_name="X")
    assert "Qué significa" not in texto


def test_el_nombre_del_producto_no_puede_inyectar_html():
    _, html = build_email("T", "B", kind="expiry", product_name="<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_el_titulo_y_el_cuerpo_se_escapan_en_el_html():
    _, html = build_email("<b>T</b>", "<i>B</i>")
    assert "<b>T</b>" not in html and "&lt;b&gt;T&lt;/b&gt;" in html


def test_el_mail_enviado_lleva_el_contenido_descriptivo():
    contenido = partes(enviar(kind="expiry", product_name="Queso", days=2))
    assert "Qué podés hacer" in contenido["text/plain"]
    assert "Queso" in contenido["text/html"]


# ── logo ─────────────────────────────────────────────────────────────────────

def test_el_mail_lleva_el_logo_si_hay_url_configurada(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_LOGO_URL", "https://cdn.example.com/logo.png")
    assert 'src="https://cdn.example.com/logo.png"' in partes(enviar())["text/html"]
    assert 'src="https://cdn.example.com/logo.png"' in partes(enviar(kind="expiry"))["text/html"]


def test_sin_url_de_logo_no_hay_imagen(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_LOGO_URL", "")
    assert "<img" not in partes(enviar())["text/html"]


def test_la_url_del_logo_no_puede_romper_el_html(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_LOGO_URL", 'https://x.com/a.png" onerror="alert(1)')
    assert 'onerror="alert' not in partes(enviar())["text/html"]


# ── SMTP sin configurar ──────────────────────────────────────────────────────

def test_sin_smtp_no_envia_y_deja_aviso_en_el_log(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    with patch("smtplib.SMTP") as smtp, caplog.at_level("WARNING", logger="app.core.email"):
        assert send_email("dest@test.com", "T", "B") is None
    smtp.assert_not_called()
    assert "SMTP no configurado" in caplog.text
    assert "dest@test.com" in caplog.text


# ── endpoint ─────────────────────────────────────────────────────────────────

def test_el_endpoint_pasa_los_datos_extra_al_mail():
    payload = {
        "token": "t", "title": "Producto próximo a vencerse", "body": "Leche vence en 2 días.", "email": "dest@test.com",
        "kind": "expiry", "product_name": "Leche", "days": 2,
    }
    with patch("app.routes.notification.send_push"), patch("app.routes.notification.send_email") as mail:
        assert client.post("/notification/send_notification", json=payload).status_code == 200
    mail.assert_called_once_with(
        "dest@test.com", "Producto próximo a vencerse", "Leche vence en 2 días.",
        kind="expiry", product_name="Leche", days=2, units=None, limit_days=None, daily_rate=None,
    )


def test_el_endpoint_pasa_la_regla_y_el_consumo_al_mail():
    payload = {
        "token": "t", "title": "T", "body": "B", "email": "dest@test.com",
        "kind": "understock", "product_name": "Fideos", "days": 3, "limit_days": 7, "daily_rate": 1.5,
    }
    with patch("app.routes.notification.send_push"), patch("app.routes.notification.send_email") as mail:
        assert client.post("/notification/send_notification", json=payload).status_code == 200
    assert mail.call_args.kwargs["limit_days"] == 7
    assert mail.call_args.kwargs["daily_rate"] == 1.5


def test_un_tipo_desconocido_no_impide_el_push_ni_el_mail():
    payload = {"token": "t", "title": "T", "body": "B", "email": "dest@test.com", "kind": "inventado"}
    with patch("app.routes.notification.send_push") as push, patch("app.routes.notification.send_email") as mail:
        assert client.post("/notification/send_notification", json=payload).status_code == 200
    push.assert_called_once()
    mail.assert_called_once()


def test_los_dias_con_decimales_se_redondean_en_vez_de_rechazar_el_pedido():
    payload = {"token": "t", "title": "T", "body": "B", "email": "dest@test.com", "kind": "low_coverage",
               "days": 2.6, "units": 3.0}
    with patch("app.routes.notification.send_push"), patch("app.routes.notification.send_email") as mail:
        assert client.post("/notification/send_notification", json=payload).status_code == 200
    assert mail.call_args.kwargs["days"] == 3
    assert mail.call_args.kwargs["units"] == 3


# ── los números reales del aviso ─────────────────────────────────────────────

def test_el_aviso_de_stock_explica_con_la_regla_y_el_consumo_del_usuario():
    texto, html = build_email("T", "B", kind="low_coverage", product_name="Leche", days=3, limit_days=7, daily_rate=2.5)
    assert "Tu mínimo configurado: 7 días" in texto
    assert "Consumo estimado: 2.5 unidades por día" in texto
    assert "Tu mínimo configurado es de 7 días" in texto and "alcanza para 3 días" in texto
    assert "por debajo de ese mínimo" in texto
    assert "Tu mínimo configurado: 7 días" in html


def test_compraste_de_menos_dice_con_cuanto_se_compara_lo_que_alcanza():
    texto, _ = build_email("T", "B", kind="understock", product_name="Fideos", days=3, limit_days=7, daily_rate=1.0)
    assert "alcanza para 3 días" in texto
    assert "tu mínimo configurado es de 7 días" in texto


def test_compraste_de_mas_dice_con_cuanto_se_compara_lo_que_alcanza():
    texto, _ = build_email("T", "B", kind="overstock", product_name="Arroz", days=90, limit_days=7, daily_rate=0.1)
    assert "alcanza para 90 días" in texto
    assert "mucho más que tu mínimo de 7 días" in texto


def test_un_stock_que_alcanza_para_menos_de_un_dia_no_dice_cero_dias():
    texto, _ = build_email("T", "B", kind="low_coverage", product_name="Cafe", days=0, limit_days=7, daily_rate=5)
    assert "0 días" not in texto
    assert "menos de 1 día" in texto
    assert "unas 5 unidades por día" in texto


def test_el_aviso_de_vencimiento_dice_la_anticipacion_configurada():
    texto, _ = build_email("T", "B", kind="expiry", product_name="Yogur", days=2, limit_days=7)
    assert "Tu aviso de anticipación: 7 días" in texto
    assert "Configuraste que te avisemos cuando falten 7 días o menos" in texto


def test_un_producto_vencido_dice_hace_cuantos_dias():
    texto, _ = build_email("T", "B", kind="expiry", product_name="Yogur", days=-3)
    assert "Venció hace: 3 días" in texto


def test_sin_la_regla_el_mail_es_el_de_siempre():
    texto, _ = build_email("T", "B", kind="understock", product_name="Fideos", days=3)
    assert "Tu mínimo configurado" not in texto
    assert "Consumo estimado" not in texto


def test_el_consumo_se_escribe_legible():
    assert "Consumo estimado: 12 unidades por día" in build_email("T", "B", kind="low_coverage", days=2, daily_rate=12.4)[0]
    assert "Consumo estimado: 0.3 unidades por día" in build_email("T", "B", kind="low_coverage", days=2, daily_rate=0.34)[0]
    assert "Consumo estimado" not in build_email("T", "B", kind="low_coverage", days=2, daily_rate=0)[0]


def test_el_ritmo_lento_muestra_la_anticipacion_con_su_nombre():
    texto, _ = build_email("T", "B", kind="slow_pace", product_name="Pan", days=4, units=5, limit_days=7)
    assert "Tu aviso de anticipación: 7 días" in texto
