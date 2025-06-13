# =============================================================================
# ARCHIVO: agents/agent_sql_generator.py
# Descripción: Generador SQL mejorado pero simple (sin analyzer complejo)
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
        
        # Templates SQL específicos para casos comunes
        self.sql_templates = {
            "tablespace_uso": """
SELECT 
    ts.TABLESPACE_NAME,
    ts.STATUS,
    ts.CONTENTS,
    ROUND(NVL(df.BYTES,0)/1024/1024, 2) AS SIZE_MB,
    ROUND(NVL(df.BYTES - NVL(fs.BYTES,0),0)/1024/1024, 2) AS USED_MB,
    ROUND(NVL(fs.BYTES,0)/1024/1024, 2) AS FREE_MB,
    CASE 
        WHEN df.BYTES > 0 THEN ROUND((NVL(df.BYTES - NVL(fs.BYTES,0),0) / df.BYTES) * 100, 2)
        ELSE 0
    END AS PCT_USED
FROM DBA_TABLESPACES ts
LEFT JOIN (SELECT TABLESPACE_NAME, SUM(BYTES) BYTES FROM DBA_DATA_FILES GROUP BY TABLESPACE_NAME) df
    ON ts.TABLESPACE_NAME = df.TABLESPACE_NAME
LEFT JOIN (SELECT TABLESPACE_NAME, SUM(BYTES) BYTES FROM DBA_FREE_SPACE GROUP BY TABLESPACE_NAME) fs
    ON ts.TABLESPACE_NAME = fs.TABLESPACE_NAME
WHERE ts.STATUS = 'ONLINE'
ORDER BY PCT_USED DESC""",
            
            "sesiones_activas": """
SELECT 
    s.USERNAME,
    s.STATUS,
    s.SID,
    s.SERIAL#,
    s.MACHINE,
    s.PROGRAM,
    TO_CHAR(s.LOGON_TIME, 'DD-MON-YYYY HH24:MI:SS') AS LOGON_TIME
FROM GV$SESSION s
WHERE s.USERNAME IS NOT NULL
  AND s.STATUS = 'ACTIVE'
ORDER BY s.LOGON_TIME DESC""",
            
            "estado_base": """
SELECT 
    INST_ID,
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
ORDER BY THREAD#"""
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generar SQL con templates inteligentes"""
        texto_usuario = data.get("texto", "")
        
        self.log_info(f"Generando SQL para: {texto_usuario}")
        
        try:
            # Paso 1: Verificar si coincide con algún template
            template_sql = self._check_templates(texto_usuario)
            
            if template_sql:
                # Usar template específico
                self.log_info("Usando template específico")
                return {
                    "tipo": "template",
                    "sql": template_sql,
                    "procesado_por": self.name,
                    "exito": True,
                    "confidence": 0.9
                }
            
            # Paso 2: Generar con OpenAI mejorado
            sql_generada = await self._generate_with_improved_openai(texto_usuario)
            sql_limpia = self._limpiar_sql(sql_generada)
            
            # Validar seguridad
            if not self._validar_sql_seguro(sql_limpia):
                raise ValueError("SQL generada no es segura")
            
            self.log_info("SQL generada exitosamente")
            
            return {
                "tipo": "generada",
                "sql": sql_limpia,
                "procesado_por": self.name,
                "exito": True,
                "confidence": 0.7
            }
            
        except Exception as e:
            self.log_error(f"Error generando SQL: {str(e)}")
            # Fallback a SQL básico
            sql_fallback = self._generar_sql_fallback(texto_usuario)
            
            return {
                "tipo": "fallback",
                "sql": sql_fallback,
                "procesado_por": self.name,
                "exito": True,
                "confidence": 0.5,
                "nota": f"Usando SQL básico (Error: {str(e)})"
            }
    
    def _check_templates(self, texto: str) -> str:
        """Verificar si la consulta coincide con algún template"""
        texto_lower = texto.lower()
        
        # Detectar consultas de estado de base
        if any(word in texto_lower for word in ["estado", "estatus"]) and \
           any(word in texto_lower for word in ["base", "bd", "instancia", "sistema"]):
            return self.sql_templates["estado_base"]
        
        # Detectar consultas de tablespace
        if any(word in texto_lower for word in ["tablespace", "tbs", "espacio"]) and \
           any(word in texto_lower for word in ["uso", "utiliz", "ocupado", "libre"]):
            return self.sql_templates["tablespace_uso"]
        
        # Detectar sesiones activas
        if any(word in texto_lower for word in ["sesiones", "session"]) and \
           any(word in texto_lower for word in ["activas", "active"]):
            return self.sql_templates["sesiones_activas"]
        
        return None
    
    async def _generate_with_improved_openai(self, texto: str) -> str:
        """Generar SQL con OpenAI usando prompt mejorado"""
        
        # Contexto específico basado en palabras clave
        contexto = self._obtener_contexto_especifico(texto)
        
        prompt = f"""Eres un DBA experto en Oracle. Genera ÚNICAMENTE la consulta SQL para esta solicitud:

{contexto}

SOLICITUD: {texto}

REGLAS:
- SQL válido para Oracle únicamente
- Usar vistas del sistema apropiadas (GV$SESSION, DBA_TABLESPACES, etc.)
- Incluir filtros relevantes
- Usar aliases descriptivos
- Limitar resultados a 50 filas máximo
- Para fechas usar SYSDATE
- Para sesiones filtrar USERNAME IS NOT NULL

SQL:"""

        respuesta = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un DBA Oracle experto. Genera únicamente código SQL válido sin explicaciones."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=400,
            n=1
        )
        
        return respuesta.choices[0].message.content.strip()
    
    def _obtener_contexto_especifico(self, texto: str) -> str:
        """Obtener contexto específico para OpenAI"""
        texto_lower = texto.lower()
        
        if "tablespace" in texto_lower:
            return """
CONTEXTO TABLESPACE:
- Usar DBA_TABLESPACES para información básica
- JOIN con DBA_DATA_FILES para tamaño total
- JOIN con DBA_FREE_SPACE para espacio libre
- Calcular porcentaje usado: (USADO / TOTAL) * 100
- Ordenar por porcentaje usado descendente
"""
        
        elif "usuarios" in texto_lower or "sesiones" in texto_lower:
            if "conectados" in texto_lower or "activ" in texto_lower:
                return """
CONTEXTO SESIONES:
- Usar GV$SESSION para información de sesiones
- Filtrar USERNAME IS NOT NULL (excluir background)
- Si pide "activas": agregar STATUS = 'ACTIVE'
- Si pide "hoy": agregar TRUNC(LOGON_TIME) = TRUNC(SYSDATE)
- Mostrar USERNAME, STATUS, MACHINE, PROGRAM, LOGON_TIME
"""
        
        elif "procesos" in texto_lower:
            return """
CONTEXTO PROCESOS:
- Usar GV$PROCESS o GV$RESOURCE_LIMIT
- Para recursos: mostrar CURRENT_UTILIZATION, MAX_UTILIZATION
- Para procesos: mostrar PID, SPID, USERNAME, PROGRAM
"""
        
        elif "estado" in texto_lower:
            return """
CONTEXTO ESTADO:
- Usar GV$INSTANCE para estado de instancias
- Mostrar INSTANCE_NAME, STATUS, HOST_NAME, STARTUP_TIME
- Usar TO_CHAR para formatear fechas
"""
        
        return "Generar consulta SQL apropiada para Oracle."
    
    def _generar_sql_fallback(self, texto: str) -> str:
        """Generar SQL básico como respaldo"""
        texto_lower = texto.lower()
        
        if "estado" in texto_lower and ("base" in texto_lower or "instancia" in texto_lower):
            return """SELECT INST_ID,
                            INSTANCE_NUMBER,
                            INSTANCE_NAME,
                            HOST_NAME,
                            VERSION,
                            TO_CHAR(STARTUP_TIME, 'DD-MON-YYYY HH24:MI:SS') AS INICIADA,
                            STATUS,
                            DATABASE_STATUS
                     FROM GV$INSTANCE
                     ORDER BY THREAD#"""
        
        elif "tablespace" in texto_lower:
            return "SELECT TABLESPACE_NAME, STATUS, CONTENTS FROM DBA_TABLESPACES WHERE ROWNUM <= 20"
        
        elif "usuarios" in texto_lower or "sesiones" in texto_lower:
            if "hoy" in texto_lower:
                return """SELECT USERNAME, STATUS, MACHINE, 
                                TO_CHAR(LOGON_TIME, 'DD-MON-YYYY HH24:MI:SS') AS LOGON_TIME
                         FROM GV$SESSION 
                         WHERE USERNAME IS NOT NULL 
                           AND TRUNC(LOGON_TIME) = TRUNC(SYSDATE)
                           AND ROWNUM <= 20"""
            else:
                return """SELECT USERNAME, STATUS, MACHINE, 
                                TO_CHAR(LOGON_TIME, 'DD-MON-YYYY HH24:MI:SS') AS LOGON_TIME
                         FROM GV$SESSION 
                         WHERE USERNAME IS NOT NULL AND ROWNUM <= 20"""
        
        else:
            return "SELECT SYSDATE AS FECHA_ACTUAL FROM DUAL"
    
    def _limpiar_sql(self, sql: str) -> str:
        """Limpiar SQL de formato"""
        sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
        sql = sql.replace("```", "")
        sql = sql.strip()
        
        if sql.endswith(";"):
            sql = sql[:-1].strip()
        
        return sql
    
    def _validar_sql_seguro(self, sql: str) -> bool:
        """Validar que SQL sea seguro"""
        sql_upper = sql.upper().strip()
        
        if not sql_upper.startswith("SELECT"):
            return False
        
        palabras_prohibidas = [
            "DELETE", "UPDATE", "INSERT", "DROP", "ALTER", 
            "CREATE", "TRUNCATE", "GRANT", "REVOKE"
        ]
        
        for palabra in palabras_prohibidas:
            if palabra in sql_upper:
                return False
        
        return True
