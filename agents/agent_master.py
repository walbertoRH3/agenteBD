# =============================================================================
# ARCHIVO: agents/agent_master.py
# Descripción: Agente coordinador principal con soporte de inventario BD
# =============================================================================

from .base_agent import BaseAgent
from .agent_consultas_predefinidas import AgentConsultasPredefinidas
from .agent_sql_generator import AgentSQLGenerator
from .agent_analisis import AgentAnalisis
from .agent_db_inventory import AgentDBInventory
from database.oracle_executor import OracleExecutor
from typing import Dict, Any
import re

class AgentMaster(BaseAgent):
    def __init__(self):
        super().__init__("Master")
        
        # Inicializar agentes especializados
        self.agent_consultas = AgentConsultasPredefinidas()
        self.agent_sql_generator = AgentSQLGenerator()
        self.agent_analisis = AgentAnalisis()
        self.agent_db_inventory = AgentDBInventory()
        self.oracle_executor = OracleExecutor()
        
        # Estado para manejar conversaciones multi-turno
        self.conversaciones_pendientes = {}
    
    def _escape_markdown(self, text: str) -> str:
        """Escapar caracteres especiales de Markdown para Telegram"""
        if not text:
            return text
            
        # Caracteres que necesitan ser escapados en Telegram Markdown
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def _format_for_telegram(self, text: str) -> str:
        """Formatear texto para envío seguro a Telegram"""
        # Primero escapar caracteres especiales
        text = self._escape_markdown(text)
        
        # Luego aplicar formato específico (usando caracteres ya escapados)
        # Reemplazar nuestros marcadores de formato
        text = text.replace('\\*\\*', '*')  # Para bold
        text = text.replace('🎯', '🎯')     # Emojis están bien
        text = text.replace('🖥️', '🖥️')
        text = text.replace('📊', '📊')
        text = text.replace('🔸', '🔸')
        text = text.replace('📋', '📋')
        text = text.replace('🧠', '🧠')
        text = text.replace('⚠️', '⚠️')
        text = text.replace('✅', '✅')
        text = text.replace('❌', '❌')
        text = text.replace('❗', '❗')
        text = text.replace('🔍', '🔍')
        text = text.replace('💡', '💡')
        text = text.replace('👉', '👉')
        text = text.replace('🔧', '🔧')
        
        return text
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "").strip()
        chat_id = data.get("chat_id")
        
        self.log_info(f"Procesando solicitud del chat {chat_id}")
        
        if not texto_usuario:
            return {
                "respuesta": "Por favor, escribe una consulta.",
                "exito": False
            }
        
        try:
            # Verificar si hay una conversación pendiente para este chat
            conversacion_pendiente = self.conversaciones_pendientes.get(chat_id, {})
            intento = conversacion_pendiente.get('intento', 1)
            consulta_original = conversacion_pendiente.get('consulta_original', '')
            
            # Si es segundo intento, combinar consulta original con nueva respuesta
            if intento > 1 and consulta_original:
                texto_combinado = f"{consulta_original} {texto_usuario}"
                self.log_info(f"Segundo intento - combinando: '{consulta_original}' + '{texto_usuario}'")
            else:
                texto_combinado = texto_usuario
                # Guardar consulta original para posibles intentos futuros
                if intento == 1:
                    self.conversaciones_pendientes[chat_id] = {
                        'consulta_original': texto_usuario,
                        'intento': 1
                    }
            
            # Paso 1: Identificar y validar base de datos
            resultado_bd = await self.agent_db_inventory.process({
                "texto": texto_combinado,
                "chat_id": chat_id,
                "intento": intento
            })
            
            if not resultado_bd.get("bd_encontrada", False):
                # BD no encontrada
                error_tipo = resultado_bd.get("error")
                
                if error_tipo == "bd_requerida":
                    # Primer intento fallido, guardar estado
                    self.conversaciones_pendientes[chat_id] = {
                        'intento': resultado_bd.get('intento', 2),
                        'estado': 'esperando_bd',
                        'consulta_original': texto_usuario
                    }
                elif error_tipo == "bd_no_encontrada":
                    # Segundo intento fallido, limpiar conversación
                    self.conversaciones_pendientes.pop(chat_id, None)
                
                return {
                    "respuesta": resultado_bd.get("mensaje"),
                    "exito": False
                }
            
            # BD encontrada, limpiar conversación pendiente
            self.conversaciones_pendientes.pop(chat_id, None)
            
            # Obtener información de conexión
            connection_info = resultado_bd.get("connection_info")
            # Usar texto combinado para la consulta SQL
            texto_consulta = resultado_bd.get("texto_sin_bd", texto_combinado)
            db_config = resultado_bd.get("db_config")
            
            self.log_info(f"BD seleccionada: {db_config['id']} - {db_config.get('description', '')}")
            self.log_info(f"Consulta a procesar: '{texto_consulta}'")
            
            # Paso 2: Verificar si es consulta predefinida
            resultado_consulta = await self.agent_consultas.process({"texto": texto_consulta})
            
            # Paso 3: Generar SQL (predefinida o personalizada)
            if resultado_consulta["tipo"] == "predefinida":
                sql_a_ejecutar = resultado_consulta["sql"]
                self.log_info(f"Usando consulta predefinida: {resultado_consulta['nombre_consulta']}")
            else:
                # Generar SQL personalizada
                resultado_sql = await self.agent_sql_generator.process({"texto": texto_consulta})
                if not resultado_sql.get("exito", False):
                    return {
                        "respuesta": f"Error generando SQL: {resultado_sql.get('error', 'Error desconocido')}",
                        "exito": False
                    }
                sql_a_ejecutar = resultado_sql["sql"]
                self.log_info("Usando SQL generada por IA")
            
            # Paso 4: Ejecutar SQL en la BD específica
            self.log_info(f"Ejecutando SQL en BD: {db_config['id']}")
            resultados = await self.oracle_executor.ejecutar_sql(sql_a_ejecutar, connection_info)
            
            # Paso 5: Analizar resultados
            resultado_analisis = await self.agent_analisis.process({
                "resultados": resultados,
                "sql": sql_a_ejecutar,
                "texto_original": texto_consulta
            })
            
            # Paso 6: Formatear respuesta final
            respuesta_final = self._formatear_respuesta_final(
                resultados, 
                resultado_analisis.get("analisis", "Análisis no disponible"),
                db_config
            )
            
            self.log_info("Procesamiento completado exitosamente")
            
            return {
                "respuesta": respuesta_final,
                "exito": True,
                "sql_ejecutada": sql_a_ejecutar,
                "num_resultados": len(resultados),
                "base_datos": db_config['id']
            }
            
        except Exception as e:
            self.log_error(f"Error en procesamiento: {str(e)}")
            # Limpiar conversación pendiente en caso de error
            self.conversaciones_pendientes.pop(chat_id, None)
            
            # Mensaje de error más amigable
            error_msg = str(e)
            if "ORA" in error_msg:
                respuesta_error = f"Error de Base de Datos:\n{error_msg}\n\nVerifica que la consulta sea válida para Oracle."
            elif "connection" in error_msg.lower():
                respuesta_error = f"Error de Conexión:\n{error_msg}\n\nRevisa la conectividad con la base de datos."
            else:
                respuesta_error = f"Error del Sistema:\n{error_msg}"
                
            return {
                "respuesta": respuesta_error,
                "exito": False
            }
    
    def _formatear_respuesta_final(self, resultados: list, analisis: str, db_config: Dict[str, Any]) -> str:
        MAX_VALUE_LEN = 100
        MAX_LENGTH = 3500  # Reducido para evitar problemas con Telegram
        
        # Encabezado con información de BD (sin formato markdown problemático)
        respuesta = f"🎯 Base de datos: {db_config['id']} ({db_config.get('description', 'Sin descripción')})\n"
        respuesta += f"🖥️ Host: {db_config.get('connection', {}).get('host')}\n\n"
        
        if not resultados:
            respuesta += "✅ Consulta ejecutada correctamente, sin resultados."
        else:
            respuesta += "📊 Resultados:\n\n"
            
            # Mostrar máximo 5 filas
            for i, fila in enumerate(resultados[:5], 1):
                respuesta += f"--- Registro {i} ---\n"
                for k, v in fila.items():
                    v = "NULL" if v is None else str(v)
                    if len(v) > MAX_VALUE_LEN:
                        v = v[:MAX_VALUE_LEN] + "..."
                    respuesta += f"🔸 {k.upper()}: {v}\n"
                respuesta += "\n"
            
            if len(resultados) > 5:
                respuesta += f"📋 Se muestran 5 de {len(resultados)} registros totales\n\n"
        
        # Añadir análisis
        respuesta += f"\n🧠 Análisis experto:\n{analisis}"
        
        # Truncar si excede límite de Telegram
        if len(respuesta) > MAX_LENGTH:
            respuesta = respuesta[:MAX_LENGTH] + "\n\n⚠️ Resultado truncado por longitud."
        
        return respuesta
