# =============================================================================
# ARCHIVO: agents/agent_saludo.py
# Descripción: Agente que interpreta saludos y responde en función del horario.
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any
from datetime import datetime
import pytz

class AgentSaludo(BaseAgent):
    def __init__(self):
        super().__init__("Saludo")

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "").strip()
        chat_id = data.get("chat_id")
        
        # Verificar si el texto contiene un saludo
        if any(saludo in texto_usuario.lower() for saludo in ["hola", "buenas", "buen día", "buenas tardes"]):
            respuesta = self.generar_saludo()
            return {
                "respuesta": respuesta,
                "exito": True
            }
        
        return {
            "respuesta": "❗ No he detectado un saludo, por favor intenta nuevamente.",
            "exito": False
        }

    def generar_saludo(self) -> str:
        # Configuración de zona horaria de Ciudad de México
        mexico_city_tz = pytz.timezone('America/Mexico_City')
        hora_actual = datetime.now(mexico_city_tz).hour
        
        if 6 <= hora_actual < 12:
            return "¡Hola! Buen día, ¿en qué puedo ayudarte? Soy el asistente encargado de mejorar la administración de bases de datos Oracle."
        elif 12 <= hora_actual < 18:
            return "¡Hola! Buenas tardes, ¿en qué puedo ayudarte? Soy el asistente encargado de mejorar la administración de bases de datos Oracle."
        else:
            return "¡Hola! Buenas noches, ¿en qué puedo ayudarte? Soy el asistente encargado de mejorar la administración de bases de datos Oracle."

