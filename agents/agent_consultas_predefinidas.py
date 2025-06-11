# =============================================================================
# ARCHIVO: agents/agent_consultas_predefinidas.py
# Descripción: Agente para consultas frecuentes
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any
import unicodedata
import re

class AgentConsultasPredefinidas(BaseAgent):
    def __init__(self):
        super().__init__("ConsultasPredefinidas")
        self.consultas_predefinidas = {
            "estado_bd": {
                "patrones": [
                    "estado de la base",
                    "estado de la base de datos", 
                    "estado general",
                    "estado del sistema",
                    "revisar base de datos"
                ],
                "sql": """
SELECT INST_ID,
       INSTANCE_NUMBER,
       INSTANCE_NAME,
       HOST_NAME,
       VERSION,
       TO_CHAR(STARTUP_TIME, 'DD-MON-YYYY HH24:MI:SS') AS INICIADA,
       STATUS,
       PARALLEL,
       THREAD#,
       ARCHIVER,
       DATABASE_STATUS
FROM GV$INSTANCE
ORDER BY THREAD#""",
                "tipo": "predefinida"
            },
            "procesos_sesiones": {
                "patrones": [
                    "estatus de procesos",
                    "estatus de sesiones",
                    "umbrales procesos",
                    "umbrales de procesos",
                    "umbrales sesiones",
                    "limite de sesiones",
                    "limite de procesos"
                ],
                "sql": """
SELECT INST_ID,
       resource_name,
       current_utilization,
       max_utilization,
       limit_value
FROM GV$RESOURCE_LIMIT
WHERE resource_name IN ('sessions', 'processes', 'transactions')
ORDER BY resource_name, INST_ID""",
                "tipo": "predefinida"
            }
        }
    
    def normalizar_texto(self, texto: str) -> str:
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r"[¿?¡!]", "", texto).lower().strip()
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "")
        texto_normalizado = self.normalizar_texto(texto_usuario)
        
        self.log_info(f"Analizando consulta: {texto_normalizado}")
        
        # Verificar si coincide con alguna consulta predefinida
        for nombre_consulta, config in self.consultas_predefinidas.items():
            for patron in config["patrones"]:
                if patron in texto_normalizado:
                    self.log_info(f"Consulta predefinida encontrada: {nombre_consulta}")
                    return {
                        "tipo": "predefinida",
                        "sql": config["sql"].strip(),
                        "nombre_consulta": nombre_consulta,
                        "procesado_por": self.name
                    }
        
        # No es una consulta predefinida
        return {
            "tipo": "personalizada",
            "texto": texto_usuario,
            "procesado_por": self.name
        }

