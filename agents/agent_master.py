# =============================================================================
# ARCHIVO: agents/agent_master.py
# Descripción: Agente coordinador principal
# =============================================================================

from .base_agent import BaseAgent
from .agent_consultas_predefinidas import AgentConsultasPredefinidas
from .agent_sql_generator import AgentSQLGenerator
from .agent_analisis import AgentAnalisis
from .agent_saludo import AgentSaludo  # Importar el nuevo agente de saludo
from database.oracle_executor import OracleExecutor
from typing import Dict, Any
import asyncio

class AgentMaster(BaseAgent):
    def __init__(self):
        super().__init__("Master")

        # Inicializar agentes especializados
        self.agent_saludo = AgentSaludo()  # Instanciar el agente de saludo
        self.agent_consultas = AgentConsultasPredefinidas()
        self.agent_sql_generator = AgentSQLGenerator()
        self.agent_analisis = AgentAnalisis()
        self.oracle_executor = OracleExecutor()

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "").strip()
        chat_id = data.get("chat_id")

        self.log_info(f"Procesando solicitud del chat {chat_id}")

        if not texto_usuario:
            return {
                "respuesta": "❗ Por favor, escribe una consulta.",
                "exito": False
            }

        try:
            # Paso 1: Verificar si es un saludo (prioritario)
            resultado_saludo = await self.agent_saludo.process({"texto": texto_usuario, "chat_id": chat_id})
            if resultado_saludo["exito"]:  # Si es un saludo, responder y salir
                return resultado_saludo

            # Paso 2: Verificar si es consulta predefinida
            resultado_consulta = await self.agent_consultas.process({"texto": texto_usuario})

            # Paso 3: Generar SQL (predefinida o personalizada)
            if resultado_consulta["tipo"] == "predefinida":
                sql_a_ejecutar = resultado_consulta["sql"]
                self.log_info(f"Usando consulta predefinida: {resultado_consulta['nombre_consulta']}")
            else:
                # Generar SQL personalizada
                resultado_sql = await self.agent_sql_generator.process({"texto": texto_usuario})
                if not resultado_sql.get("exito", False):
                    return {
                        "respuesta": f"❌ Error generando SQL: {resultado_sql.get('error', 'Error desconocido')}",
                        "exito": False
                    }
                sql_a_ejecutar = resultado_sql["sql"]
                self.log_info("Usando SQL generada por IA")

            # Paso 4: Ejecutar SQL
            self.log_info(f"Ejecutando SQL: {sql_a_ejecutar[:50]}...")
            resultados = await self.oracle_executor.ejecutar_sql(sql_a_ejecutar)

            # Paso 5: Analizar resultados
            resultado_analisis = await self.agent_analisis.process({
                "resultados": resultados,
                "sql": sql_a_ejecutar,
                "texto_original": texto_usuario
            })

            # Paso 6: Formatear respuesta final
            respuesta_final = self._formatear_respuesta_final(
                resultados,
                resultado_analisis.get("analisis", "Análisis no disponible")
            )

            self.log_info("Procesamiento completado exitosamente")

            return {
                "respuesta": respuesta_final,
                "exito": True,
                "sql_ejecutada": sql_a_ejecutar,
                "num_resultados": len(resultados)
            }

        except Exception as e:
            self.log_error(f"Error en procesamiento: {str(e)}")
            return {
                "respuesta": f"❌ Error detectado:\n{str(e)}",
                "exito": False
            }

    def _formatear_respuesta_final(self, resultados: list, analisis: str) -> str:
        MAX_VALUE_LEN = 100
        MAX_LENGTH = 4000

        if not resultados:
            respuesta = "✅ Consulta ejecutada correctamente, sin resultados."
        else:
            respuesta = "📊 Resultados:\n"

            # Mostrar máximo 5 filas
            for fila in resultados[:5]:
                for k, v in fila.items():
                    v = "NULL" if v is None else str(v)
                    if len(v) > MAX_VALUE_LEN:
                        v = v[:MAX_VALUE_LEN] + "..."
                    respuesta += f"🔸 {k.upper()}: {v}\n"
                respuesta += "\n"

        # Añadir análisis
        respuesta += "\n\n🧠 Análisis experto:\n" + analisis

        # Truncar si excede límite de Telegram
        if len(respuesta) > MAX_LENGTH:
            respuesta = respuesta[:MAX_LENGTH] + "\n\n⚠️ Resultado truncado por longitud."

        return respuesta

