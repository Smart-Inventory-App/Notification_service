from typing import Optional

from pydantic import BaseModel, field_validator


class NotificationBase(BaseModel):
    title: str
    body: str
    token: str
    email: str
    # Datos opcionales para que el mail explique el aviso (qué significa y qué hacer). Sin ellos, o con un tipo que este
    # servicio no conoce, el mail lleva solo el título y el mensaje: un dato de más nunca debe impedir el push.
    kind: Optional[str] = None
    product_name: Optional[str] = None
    days: Optional[int] = None
    units: Optional[int] = None

    @field_validator("days", "units", mode="before")
    @classmethod
    def _whole_number(cls, value):
        # Los días que calcula el modelo de predicción pueden venir con decimales
        if isinstance(value, float):
            return round(value)
        return value
