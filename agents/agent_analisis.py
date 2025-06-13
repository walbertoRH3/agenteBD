# =============================================================================
# ARCHIVO: agents/agent_analisis.py
# Descripción: Agente analizador de resultados
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any, List
from openai import OpenAI
from config.settings import Config

class AgentAnalisis(BaseAgent):
    def __init__(self):
        super().__init__("Analisis")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        resultados = data.get("resultados", [])
        sql_ejecutada = data.get("sql", "")
        texto_usuario = data.get("texto_original", "")
        
        self.log_info("Iniciando análisis de resultados")
        
        try:
            analisis = await self._generar_analisis(texto_usuario, sql_ejecutada, resultados)
            
            return {
                "analisis": analisis,
                "procesado_por": self.name,
                "exito": True
            }
            
        except Exception as e:
            self.log_error(f"Error en análisis: {str(e)}")
            return {
                "analisis": "No se pudo generar el análisis automático.",
                "procesado_por": self.name,
                "exito": False
            }
    
    async def _generar_analisis(self, texto_usuario: str, sql: str, resultados: List[Dict]) -> str:
        # Formatear resultados (máximo 5 filas)
        resumen_resultados = self._formatear_resultados(resultados)
        
        prompt = f"""
Eres un DBA experto en Oracle. Analiza únicamente los RESULTADOS siguientes. No comentes la consulta SQL, ni la pregunta del usuario.

RESULTADOS:
{resumen_resultados}

Proporciona un análisis breve, técnico y claro (máximo 3-4 líneas). Indica si los datos muestran un problema o si todo está dentro de lo esperado.
"""
        
        respuesta = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un DBA experto en Oracle. Tus análisis deben ser técnicos, concisos y enfocados solo en los resultados SQL. Máximo 3-4 líneas."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=300,
            n=1
        )
        
        return respuesta.choices[0].message.content.strip()
    
    def _formatear_resultados(self, resultados: List[Dict], max_filas: int = 5) -> str:
        if not resultados:
            return "La consulta no devolvió resultados."
        
        resumen = ""
        filas_mostrar = resultados[:max_filas]
        
        for fila in filas_mostrar:
            fila_texto = ", ".join(f"{k}={v}" for k, v in fila.items())
            resumen += fila_texto + "\n"
        
        if len(resultados) > max_filas:
            resumen += f"... (se muestran {max_filas} de {len(resultados)} filas)\n"
        
        return resumen


