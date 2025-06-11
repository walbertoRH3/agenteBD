# =============================================================================
# ARCHIVO: database/oracle_executor.py
# Descripción: Ejecutor mejorado para Oracle con soporte multi-BD
# =============================================================================

import oracledb
import traceback
from typing import List, Dict, Any, Optional
from config.settings import Config
import logging

logger = logging.getLogger(__name__)

class OracleExecutor:
    def __init__(self):
        self.config = Config
    
    async def ejecutar_sql(self, sql: str, connection_info: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Ejecutar SQL en Oracle usando información de conexión específica o por defecto
        
        Args:
            sql: Consulta SQL a ejecutar
            connection_info: Información de conexión específica (opcional)
        """
        
        # Usar conexión específica o la por defecto
        if connection_info:
            user = connection_info.get('user')
            password = connection_info.get('password')
            dsn = connection_info.get('dsn')
            role = connection_info.get('role', 'normal')
            logger.info(f"📥 Ejecutando SQL en BD específica: {dsn}")
        else:
            # Conexión por defecto (para compatibilidad)
            user = self.config.ORACLE_USER
            password = self.config.ORACLE_PASSWORD
            dsn = self.config.ORACLE_DSN
            role = 'sysdba'
            logger.info(f"📥 Ejecutando SQL en BD por defecto: {dsn}")
            
        logger.info(f"🔍 SQL: {sql[:100]}...")
        
        conn = None
        cursor = None
        
        try:
            # Determinar modo de autenticación
            if role.lower() == 'sysdba':
                auth_mode = oracledb.AUTH_MODE_SYSDBA
            elif role.lower() == 'sysoper':
                auth_mode = oracledb.AUTH_MODE_SYSOPER
            else:
                auth_mode = oracledb.AUTH_MODE_DEFAULT
            
            # Conexión a Oracle
            conn = oracledb.connect(
                user=user,
                password=password,
                dsn=dsn,
                mode=auth_mode
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
            
            logger.info(f"✅ Consulta ejecutada exitosamente. {len(resultado)} filas obtenidas.")
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
