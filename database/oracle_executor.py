# =============================================================================
# ARCHIVO: database/oracle_executor.py
# Descripción: Ejecutor mejorado para Oracle
# =============================================================================

import oracledb
import traceback
from typing import List, Dict, Any
from config.settings import Config
import logging

logger = logging.getLogger(__name__)

class OracleExecutor:
    def __init__(self):
        self.config = Config
    
    async def ejecutar_sql(self, sql: str) -> List[Dict[str, Any]]:
        logger.info(f"📥 Ejecutando SQL: {sql[:100]}...")
        
        conn = None
        cursor = None
        
        try:
            # Conexión a Oracle
            conn = oracledb.connect(
                user=self.config.ORACLE_USER,
                password=self.config.ORACLE_PASSWORD,
                dsn=self.config.ORACLE_DSN,
                mode=oracledb.AUTH_MODE_SYSDBA
            )
            cursor = conn.cursor()
            
            # Ejecutar SQL
            cursor.execute(sql)
            
            # Si no hay descripción, no es una consulta SELECT
            if cursor.description is None:
                conn.commit()
                logger.info("✅ Consulta ejecutada sin resultados (no SELECT).")
                return []
            
            # Obtener resultados de una SELECT
            columnas = [desc[0] for desc in cursor.description]
            filas = cursor.fetchall()
            
            resultado = []
            for fila in filas:
                item = {col: str(val) if val is not None else None 
                       for col, val in zip(columnas, fila)}
                resultado.append(item)
            
            logger.info(f"✅ Consulta ejecutada. {len(resultado)} filas obtenidas.")
            return resultado
            
        except oracledb.DatabaseError as e:
            error, = e.args
            logger.error(f"❌ Error ORACLE: {error.message}")
            raise Exception(f"ORA Error: {error.message}")
            
        except Exception as e:
            logger.error(f"❌ Error general: {str(e)}")
            traceback.print_exc()
            raise Exception(f"Error general al ejecutar SQL: {str(e)}")
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

