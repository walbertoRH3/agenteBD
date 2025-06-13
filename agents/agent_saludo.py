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
        
        self.log_info(f"Procesando saludo: {texto_usuario}")
        
        # Verificar si el texto contiene un saludo
        if self._es_saludo(texto_usuario):
            respuesta = self._generar_saludo()
            return {
                "respuesta": respuesta,
                "exito": True
            }
        
        return {
            "respuesta": "❗ No he detectado un saludo, por favor intenta nuevamente.",
            "exito": False
        }
    
    def _es_saludo(self, texto: str) -> bool:
        """Verificar si el texto es un saludo"""
        texto_lower = texto.lower().strip()
        saludos = [
            "hola", "buenos", "buenas", "buen día", "buenas tardes", 
            "buenas noches", "hey", "hi", "hello", "saludos"
        ]
        return any(saludo in texto_lower for saludo in saludos)

    def _generar_saludo(self) -> str:
        """Generar saludo personalizado según la hora"""
        try:
            # Configuración de zona horaria de Ciudad de México
            mexico_city_tz = pytz.timezone('America/Mexico_City')
            hora_actual = datetime.now(mexico_city_tz).hour
            
            if 6 <= hora_actual < 12:
                saludo_hora = "¡Buenos días!"
            elif 12 <= hora_actual < 18:
                saludo_hora = "¡Buenas tardes!"
            else:
                saludo_hora = "¡Buenas noches!"
            
            return f"""{saludo_hora} 👋

🤖 Soy tu asistente especializado en administración de bases de datos Oracle.

📊 **¿En qué puedo ayudarte hoy?**
• Consultar estado de bases de datos
• Revisar sesiones de usuarios
• Analizar rendimiento del sistema
• Verificar procesos activos

💡 **Recuerda:** Siempre especifica el nombre de la base de datos en tu consulta.

Ejemplos:
• "BRM estado de la base"
• "SAP usuarios conectados hoy" 

¿Qué consulta necesitas realizar?"""
            
        except Exception as e:
            self.log_error(f"Error generando saludo: {str(e)}")
            return "¡Hola! 👋 Soy tu asistente de bases de datos Oracle. ¿En qué puedo ayudarte?"
