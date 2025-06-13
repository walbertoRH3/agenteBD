# =============================================================================
# ARCHIVO: agents/agent_master.py
# Descripción: Agente coordinador con análisis inteligente de consultas
# =============================================================================

from .base_agent import BaseAgent
from .agent_consultas_predefinidas import AgentConsultasPredefinidas
from .agent_sql_generator import AgentSQLGenerator
from .agent_analisis import AgentAnalisis
from .agent_db_inventory import AgentDBInventory
from .agent_saludo import AgentSaludo
from database.oracle_executor import OracleExecutor
from typing import Dict, Any
import re

class AgentMaster(BaseAgent):
    def __init__(self):
        super().__init__("Master")
        
        # Inicializar agentes especializados
        self.agent_saludo = AgentSaludo()
        self.agent_consultas = AgentConsultasPredefinidas()
        self.agent_sql_generator = AgentSQLGenerator()  # Ahora incluye analizador inteligente
        self.agent_analisis = AgentAnalisis()
        self.agent_db_inventory = AgentDBInventory()
        self.oracle_executor = OracleExecutor()
        
        # Estado para manejar conversaciones multi-turno
        self.conversaciones_pendientes = {}
    
    def _is_greeting(self, texto: str) -> bool:
        """Verificar si el texto es un saludo"""
        texto_lower = texto.lower().strip()
        saludos = ["hola", "buenos", "buenas", "buen día", "buenas tardes", "buenas noches", "hey", "hi"]
        return any(saludo in texto_lower for saludo in saludos)
    
    def _is_help_request(self, texto: str) -> bool:
        """Verificar si es solicitud de ayuda"""
        texto_lower = texto.lower().strip()
        help_words = ["/help", "/ayuda", "ayuda", "help", "como usar", "que puedo", "comandos"]
        return any(word in texto_lower for word in help_words)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        texto_usuario = data.get("texto", "").strip()
        chat_id = data.get("chat_id")
        
        self.log_info(f"Procesando solicitud del chat {chat_id}: '{texto_usuario[:50]}...'")
        
        if not texto_usuario:
            return {
                "respuesta": "Por favor, escribe una consulta.",
                "exito": False
            }
        
        try:
            # 1. Verificar si es un saludo
            if self._is_greeting(texto_usuario):
                resultado_saludo = await self.agent_saludo.process(data)
                return resultado_saludo
            
            # 2. Verificar si es solicitud de ayuda
            if self._is_help_request(texto_usuario):
                return {
                    "respuesta": self._generar_mensaje_ayuda(),
                    "exito": True
                }
            
            # 3. Procesar consulta de base de datos con análisis inteligente
            return await self._process_intelligent_database_query(data)
            
        except Exception as e:
            self.log_error(f"Error en procesamiento: {str(e)}")
            # Limpiar conversación pendiente en caso de error
            self.conversaciones_pendientes.pop(chat_id, None)
            
            return {
                "respuesta": f"❌ Error del sistema: {str(e)}",
                "exito": False
            }
    
    async def _process_intelligent_database_query(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar consulta de base de datos con análisis inteligente"""
        texto_usuario = data.get("texto", "").strip()
        chat_id = data.get("chat_id")
        
        # Manejar conversación multi-turno
        conversacion_pendiente = self.conversaciones_pendientes.get(chat_id, {})
        intento = conversacion_pendiente.get('intento', 1)
        consulta_original = conversacion_pendiente.get('consulta_original', '')
        
        # Combinar texto si es segundo intento
        if intento > 1 and consulta_original:
            texto_combinado = f"{consulta_original} {texto_usuario}"
            self.log_info(f"Segundo intento - combinando consultas")
        else:
            texto_combinado = texto_usuario
            if intento == 1:
                self.conversaciones_pendientes[chat_id] = {
                    'consulta_original': texto_usuario,
                    'intento': 1
                }
        
        # PASO 1: Identificar y validar base de datos
        self.log_info("🔍 Paso 1: Identificando base de datos...")
        resultado_bd = await self.agent_db_inventory.process({
            "texto": texto_combinado,
            "chat_id": chat_id,
            "intento": intento
        })
        
        if not resultado_bd.get("bd_encontrada", False):
            # Manejar caso sin BD encontrada
            error_tipo = resultado_bd.get("error")
            
            if error_tipo == "bd_requerida":
                self.conversaciones_pendientes[chat_id] = {
                    'intento': resultado_bd.get('intento', 2),
                    'estado': 'esperando_bd',
                    'consulta_original': texto_usuario
                }
            elif error_tipo == "bd_no_encontrada":
                self.conversaciones_pendientes.pop(chat_id, None)
            
            return {
                "respuesta": resultado_bd.get("mensaje"),
                "exito": False
            }
        
        # BD encontrada, continuar con procesamiento inteligente
        self.conversaciones_pendientes.pop(chat_id, None)
        
        connection_info = resultado_bd.get("connection_info")
        texto_consulta = resultado_bd.get("texto_sin_bd", texto_combinado)
        db_config = resultado_bd.get("db_config")
        
        self.log_info(f"✅ BD seleccionada: {db_config['id']}")
        self.log_info(f"📝 Consulta a procesar: '{texto_consulta}'")
        
        # PASO 2: Verificar consultas predefinidas primero (más rápido)
        self.log_info("🔍 Paso 2: Verificando consultas predefinidas...")
        resultado_consulta = await self.agent_consultas.process({"texto": texto_consulta})
        
        sql_a_ejecutar = None
        sql_metadata = {}
        
        if resultado_consulta["tipo"] == "predefinida":
            # Usar consulta predefinida
            sql_a_ejecutar = resultado_consulta["sql"]
            sql_metadata = {
                "tipo": "predefinida",
                "nombre": resultado_consulta.get("nombre_consulta"),
                "confidence": 1.0
            }
            self.log_info(f"✅ Usando consulta predefinida: {sql_metadata['nombre']}")
        
        else:
            # PASO 3: Generar SQL inteligente
            self.log_info("🧠 Paso 3: Generando SQL con análisis inteligente...")
            resultado_sql = await self.agent_sql_generator.process({
                "texto": texto_consulta,
                "db_config": db_config
            })
            
            if not resultado_sql.get("exito", False):
                return {
                    "respuesta": f"❌ Error generando SQL: {resultado_sql.get('error', 'Error desconocido')}",
                    "exito": False
                }
            
            sql_a_ejecutar = resultado_sql["sql"]
            sql_metadata = {
                "tipo": resultado_sql.get("tipo", "generada"),
                "confidence": resultado_sql.get("confidence", 0.5),
                "analisis": resultado_sql.get("analisis_usado", {})
            }
            
            confidence_level = "Alta" if sql_metadata["confidence"] > 0.8 else "Media" if sql_metadata["confidence"] > 0.5 else "Baja"
            self.log_info(f"✅ SQL generada con confianza: {confidence_level} ({sql_metadata['confidence']:.2f})")
        
        # PASO 4: Ejecutar SQL
        self.log_info(f"⚡ Paso 4: Ejecutando SQL en BD {db_config['id']}...")
        try:
            resultados = await self.oracle_executor.ejecutar_sql(sql_a_ejecutar, connection_info)
            self.log_info(f"✅ Ejecución exitosa: {len(resultados)} resultados obtenidos")
        except Exception as e:
            self.log_error(f"❌ Error ejecutando SQL: {str(e)}")
            return {
                "respuesta": f"❌ Error ejecutando consulta: {str(e)}\n\n🔧 SQL generada:\n```\n{sql_a_ejecutar}\n```",
                "exito": False
            }
        
        # PASO 5: Analizar resultados
        self.log_info("🧠 Paso 5: Analizando resultados...")
        resultado_analisis = await self.agent_analisis.process({
            "resultados": resultados,
            "sql": sql_a_ejecutar,
            "texto_original": texto_consulta
        })
        
        # PASO 6: Formatear respuesta final con información adicional
        respuesta_final = self._formatear_respuesta_inteligente(
            resultados, 
            resultado_analisis.get("analisis", "Análisis no disponible"),
            db_config,
            sql_metadata,
            texto_consulta
        )
        
        self.log_info("✅ Procesamiento completado exitosamente")
        
        return {
            "respuesta": respuesta_final,
            "exito": True,
            "sql_ejecutada": sql_a_ejecutar,
            "num_resultados": len(resultados),
            "base_datos": db_config['id'],
            "metadata": sql_metadata
        }
    
    def _formatear_respuesta_inteligente(self, resultados: list, analisis: str, db_config: Dict[str, Any], 
                                       sql_metadata: Dict[str, Any], consulta_original: str) -> str:
        """Formatear respuesta con información inteligente adicional"""
        MAX_VALUE_LEN = 100
        MAX_LENGTH = 3500
        
        # Encabezado mejorado
        respuesta = f"🎯 **Base de datos:** {db_config['id']} ({db_config.get('description', 'Sin descripción')})\n"
        respuesta += f"🖥️ **Host:** {db_config.get('connection', {}).get('host')}\n"
        
        # Información de análisis inteligente
        if sql_metadata.get("tipo") == "predefinida":
            respuesta += f"🔧 **Tipo:** Consulta predefinida ({sql_metadata.get('nombre', 'N/A')})\n"
        else:
            confidence = sql_metadata.get("confidence", 0.5)
            confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
            respuesta += f"🤖 **Tipo:** SQL generada con IA {confidence_emoji} (Confianza: {confidence:.0%})\n"
        
        respuesta += "\n"
        
        # Resultados
        if not resultados:
            respuesta += "✅ Consulta ejecutada correctamente, sin resultados.\n"
        else:
            respuesta += f"📊 **Resultados** ({len(resultados)} registros):\n\n"
            
            # Mostrar máximo 5 filas con formato mejorado
            for i, fila in enumerate(resultados[:5], 1):
                respuesta += f"**--- Registro {i} ---**\n"
                for k, v in fila.items():
                    v = "NULL" if v is None else str(v)
                    if len(v) > MAX_VALUE_LEN:
                        v = v[:MAX_VALUE_LEN] + "..."
                    
                    # Formateo especial para campos comunes
                    if "PCT" in k.upper() or "PERCENT" in k.upper():
                        respuesta += f"📈 **{k}:** {v}%\n"
                    elif "SIZE" in k.upper() or "BYTES" in k.upper():
                        respuesta += f"💾 **{k}:** {v}\n"
                    elif "STATUS" in k.upper():
                        status_emoji = "✅" if "ACTIVE" in str(v).upper() or "ONLINE" in str(v).upper() else "⚠️"
                        respuesta += f"{status_emoji} **{k}:** {v}\n"
                    else:
                        respuesta += f"🔸 **{k}:** {v}\n"
                respuesta += "\n"
            
            if len(resultados) > 5:
                respuesta += f"📋 *Se muestran 5 de {len(resultados)} registros totales*\n\n"
        
        # Análisis experto
        respuesta += f"🧠 **Análisis experto:**\n{analisis}\n"
        
        # Información adicional si la confianza es baja
        if sql_metadata.get("confidence", 1.0) < 0.6:
            respuesta += f"\n💡 **Sugerencia:** Si los resultados no son los esperados, intenta ser más específico en tu consulta."
        
        # Truncar si excede límite
        if len(respuesta) > MAX_LENGTH:
            respuesta = respuesta[:MAX_LENGTH] + "\n\n⚠️ *Resultado truncado por longitud.*"
        
        return respuesta
    
    def _generar_mensaje_ayuda(self) -> str:
        """Generar mensaje de ayuda del sistema"""
        return """🤖 **Bot Consultor SQL Multibase v2.1 - Inteligente**

📝 **Cómo usar:**
1. Especifica la base de datos en tu consulta (OBLIGATORIO)
2. Escribe tu consulta en lenguaje natural
3. Recibe resultados con análisis experto

🧠 **Ejemplos inteligentes:**
• **BRM uso de tablespace** → Analiza espacio usado por tablespaces
• **SAP sesiones activas hoy** → Sesiones activas del día actual  
• **consultas usuarios conectados** → Usuarios actualmente conectados
• **facturas procesos bloqueados** → Procesos con bloqueos

❌ **Evita:**
• Consultas sin especificar base de datos
• Términos muy genéricos sin contexto

📊 **Bases disponibles:**
• **BRM:** brm, BRM, consultas
• **SAP:** sap, SAP, facturas

🧠 **Análisis inteligente:**
• Detecta automáticamente el tipo de consulta
• Usa templates optimizados cuando es posible
• Genera SQL específico con alta precisión
• Proporciona análisis contextual de resultados

⚠️ **Sistema de intentos:**
• 1er intento sin BD: Te pediré especificar la base
• 2do intento sin BD: Consulta será rechazada
• BD encontrada: Procesamiento inteligente activado

🔧 **Comandos:**
• **/help** o **/ayuda** - Mostrar esta ayuda
• **hola** - Saludo personalizado

💡 **Tip:** El sistema ahora entiende mejor tus consultas. Prueba con: "BRM tablespaces con más uso" o "SAP sesiones de usuario específico"
"""
