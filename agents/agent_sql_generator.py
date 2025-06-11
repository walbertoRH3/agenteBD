# =============================================================================
# ARCHIVO: agents/agent_sql_generator.py
# Descripción: Agente generador de SQL usando OpenAI
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any
from openai import OpenAI
from config.settings import Config
import re

class AgentSQLGenerator(BaseAgent):
    def __init__(self):
        super().__init__("SQLGenerator")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "")
        
        self.log_info(f"Generando SQL para: {texto_usuario}")
        
        try:
            contexto_extra = self._obtener_contexto_adicional(texto_usuario)
            
            prompt = f"""
Eres un experto en Oracle SQL. Genera SOLO la consulta SQL en Oracle basada en esta pregunta del usuario:
{contexto_extra}
Pregunta: {texto_usuario}
SQL:
"""
            
            respuesta = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "Eres un generador experto de consultas Oracle SQL."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=150,
                n=1
            )
            
            sql_generada = respuesta.choices[0].message.content.strip()
            sql_limpia = self._limpiar_sql(sql_generada)
            
            self.log_info("SQL generada exitosamente")
            
            return {
                "tipo": "generada",
                "sql": sql_limpia,
                "procesado_por": self.name,
                "exito": True
            }
            
        except Exception as e:
            self.log_error(f"Error generando SQL: {str(e)}")
            return {
                "tipo": "error",
                "error": str(e),
                "procesado_por": self.name,
                "exito": False
            }
    
    def _obtener_contexto_adicional(self, texto: str) -> str:
        texto_lower = texto.lower()
        if "usuarios" in texto_lower and "iniciado sesion" in texto_lower and "hoy" in texto_lower:
            return """
-- Ejemplo para usuarios que iniciaron sesión hoy:
-- Usar V$SESSION, columnas USERNAME y LOGON_TIME (fecha/hora inicio sesión)
"""
        return ""
    
    def _limpiar_sql(self, sql: str) -> str:
        # Limpiar formato Markdown
        sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
        sql = sql.replace("```", "")
        sql = sql.strip()
        
        # Quitar punto y coma final
        if sql.endswith(";"):
            sql = sql[:-1].strip()
        
        return sql
