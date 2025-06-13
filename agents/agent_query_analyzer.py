# =============================================================================
# ARCHIVO: agents/agent_query_analyzer.py
# Descripción: Agente inteligente para análisis profundo de consultas usando OpenAI
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config.settings import Config
import json
import re

class AgentQueryAnalyzer(BaseAgent):
    def __init__(self):
        super().__init__("QueryAnalyzer")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Base de conocimiento Oracle
        self.oracle_knowledge = {
            "tablespaces": {
                "vistas": ["DBA_TABLESPACES", "DBA_DATA_FILES", "DBA_FREE_SPACE", "V$TABLESPACE"],
                "campos_clave": ["TABLESPACE_NAME", "STATUS", "CONTENTS", "BYTES", "MAXBYTES", "AUTOEXTENSIBLE"],
                "conceptos": ["uso", "espacio libre", "autoextend", "datafiles", "fragmentación"]
            },
            "sesiones": {
                "vistas": ["GV$SESSION", "V$SESSION", "GV$PROCESS"],
                "campos_clave": ["USERNAME", "STATUS", "SID", "SERIAL#", "MACHINE", "PROGRAM", "LOGON_TIME"],
                "conceptos": ["activas", "inactivas", "bloqueadas", "conectadas", "usuarios"]
            },
            "rendimiento": {
                "vistas": ["GV$RESOURCE_LIMIT", "V$SYSSTAT", "GV$SYSTEM_EVENT", "V$SQL"],
                "campos_clave": ["CURRENT_UTILIZATION", "MAX_UTILIZATION", "LIMIT_VALUE", "EVENT", "TOTAL_WAITS"],
                "conceptos": ["utilización", "esperas", "estadísticas", "eventos", "recursos"]
            },
            "bloqueos": {
                "vistas": ["GV$LOCK", "V$LOCKED_OBJECT", "DBA_OBJECTS", "GV$SESSION"],
                "campos_clave": ["SID", "TYPE", "LMODE", "REQUEST", "OBJECT_NAME", "OWNER"],
                "conceptos": ["locks", "bloqueos", "waiting", "holding", "deadlocks"]
            },
            "instancia": {
                "vistas": ["GV$INSTANCE", "V$DATABASE", "V$VERSION"],
                "campos_clave": ["INSTANCE_NAME", "STATUS", "HOST_NAME", "VERSION", "STARTUP_TIME"],
                "conceptos": ["estado", "uptime", "versión", "parámetros", "alertas"]
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar consulta de usuario para entender la intención real"""
        texto_usuario = data.get("texto", "")
        db_config = data.get("db_config", {})
        
        self.log_info(f"Analizando consulta: '{texto_usuario}'")
        
        try:
            # Paso 1: Análisis de intención con OpenAI
            analisis_intencion = await self._analyze_user_intent(texto_usuario)
            
            # Paso 2: Mapear a conceptos Oracle
            mapeo_oracle = self._map_to_oracle_concepts(analisis_intencion, texto_usuario)
            
            # Paso 3: Determinar vistas y campos necesarios
            estructura_sql = self._determine_sql_structure(mapeo_oracle, analisis_intencion)
            
            # Paso 4: Validar contexto y completar información
            contexto_final = await self._enrich_context(estructura_sql, texto_usuario, db_config)
            
            resultado = {
                "intencion_original": texto_usuario,
                "intencion_analizada": analisis_intencion,
                "categoria_oracle": mapeo_oracle,
                "estructura_sql": estructura_sql,
                "contexto_enriquecido": contexto_final,
                "confidence": self._calculate_confidence(analisis_intencion, mapeo_oracle),
                "procesado_por": self.name,
                "exito": True
            }
            
            self.log_info(f"Análisis completado - Categoría: {mapeo_oracle['categoria']}, Confianza: {resultado['confidence']}")
            
            return resultado
            
        except Exception as e:
            self.log_error(f"Error en análisis: {str(e)}")
            return {
                "intencion_original": texto_usuario,
                "error": str(e),
                "procesado_por": self.name,
                "exito": False
            }
    
    async def _analyze_user_intent(self, texto_usuario: str) -> Dict[str, Any]:
        """Usar OpenAI para analizar la intención del usuario"""
        
        prompt = f"""Analiza esta consulta de un DBA sobre Oracle y devuelve un JSON con la información estructurada:

CONSULTA: "{texto_usuario}"

Analiza y devuelve ÚNICAMENTE un JSON con esta estructura:
{{
    "objetivo_principal": "¿qué quiere saber/hacer el usuario?",
    "entidades_involucradas": ["tablespace", "sesión", "usuario", etc.],
    "acciones_solicitadas": ["consultar", "listar", "verificar", "monitorear", etc.],
    "filtros_temporales": ["hoy", "activo", "reciente", etc.],
    "metricas_esperadas": ["uso", "espacio", "cantidad", "estado", etc.],
    "nivel_detalle": "básico|intermedio|avanzado",
    "urgencia": "baja|media|alta"
}}

JSON:"""

        try:
            respuesta = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un experto DBA Oracle. Analiza consultas y devuelve ÚNICAMENTE JSON válido sin explicaciones adicionales."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=300,
                n=1
            )
            
            json_text = respuesta.choices[0].message.content.strip()
            
            # Limpiar y parsear JSON
            json_text = self._clean_json_response(json_text)
            return json.loads(json_text)
            
        except Exception as e:
            self.log_error(f"Error con OpenAI o JSON: {str(e)}")
            # Fallback a análisis simple
            return self._fallback_intent_analysis(texto_usuario)
    
    def _clean_json_response(self, json_text: str) -> str:
        """Limpiar respuesta JSON de OpenAI"""
        # Remover markdown si existe
        json_text = re.sub(r'```json\s*', '', json_text)
        json_text = re.sub(r'```\s*$', '', json_text)
        
        # Buscar JSON válido en la respuesta
        json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return json_text
    
    def _fallback_intent_analysis(self, texto: str) -> Dict[str, Any]:
        """Análisis de intención básico como fallback"""
        texto_lower = texto.lower()
        
        # Detectar entidades principales
        entidades = []
        if any(word in texto_lower for word in ["tablespace", "tbs", "espacio"]):
            entidades.append("tablespace")
        if any(word in texto_lower for word in ["sesion", "session", "usuario", "conectado"]):
            entidades.append("sesion")
        if any(word in texto_lower for word in ["proceso", "process"]):
            entidades.append("proceso")
        if any(word in texto_lower for word in ["bloqueo", "lock", "bloqueado"]):
            entidades.append("bloqueo")
        
        # Detectar acciones
        acciones = []
        if any(word in texto_lower for word in ["uso", "utilizar", "ocupado"]):
            acciones.append("consultar_uso")
        if any(word in texto_lower for word in ["estado", "status"]):
            acciones.append("verificar_estado")
        if any(word in texto_lower for word in ["listar", "mostrar", "ver"]):
            acciones.append("listar")
        
        return {
            "objetivo_principal": f"Consultar {', '.join(entidades) if entidades else 'información general'}",
            "entidades_involucradas": entidades,
            "acciones_solicitadas": acciones,
            "filtros_temporales": ["actual"] if "hoy" in texto_lower or "actual" in texto_lower else [],
            "metricas_esperadas": ["uso", "estado"],
            "nivel_detalle": "intermedio",
            "urgencia": "media"
        }
    
    def _map_to_oracle_concepts(self, analisis: Dict[str, Any], texto_original: str) -> Dict[str, Any]:
        """Mapear análisis de intención a conceptos específicos de Oracle"""
        entidades = analisis.get("entidades_involucradas", [])
        acciones = analisis.get("acciones_solicitadas", [])
        
        # Determinar categoría principal
        categoria = "general"
        for entidad in entidades:
            if entidad in ["tablespace", "espacio"]:
                categoria = "tablespaces"
                break
            elif entidad in ["sesion", "usuario", "conectado"]:
                categoria = "sesiones"
                break
            elif entidad in ["proceso"]:
                categoria = "rendimiento"
                break
            elif entidad in ["bloqueo", "lock"]:
                categoria = "bloqueos"
                break
            elif entidad in ["instancia", "base"]:
                categoria = "instancia"
                break
        
        # Obtener conocimiento específico
        conocimiento = self.oracle_knowledge.get(categoria, {})
        
        return {
            "categoria": categoria,
            "vistas_recomendadas": conocimiento.get("vistas", []),
            "campos_clave": conocimiento.get("campos_clave", []),
            "conceptos_relacionados": conocimiento.get("conceptos", []),
            "entidades_detectadas": entidades,
            "acciones_detectadas": acciones
        }
    
    def _determine_sql_structure(self, mapeo_oracle: Dict[str, Any], analisis: Dict[str, Any]) -> Dict[str, Any]:
        """Determinar estructura SQL necesaria"""
        categoria = mapeo_oracle["categoria"]
        vistas = mapeo_oracle["vistas_recomendadas"]
        campos = mapeo_oracle["campos_clave"]
        
        estructura = {
            "vista_principal": vistas[0] if vistas else "DUAL",
            "campos_necesarios": campos[:5],  # Limitar campos
            "joins_necesarios": [],
            "filtros_sugeridos": [],
            "ordenamiento": None,
            "agrupacion": None
        }
        
        # Estructuras específicas por categoría
        if categoria == "tablespaces":
            estructura.update({
                "vista_principal": "DBA_TABLESPACES",
                "campos_necesarios": ["TABLESPACE_NAME", "STATUS", "CONTENTS"],
                "joins_necesarios": ["DBA_DATA_FILES", "DBA_FREE_SPACE"],
                "filtros_sugeridos": ["STATUS = 'ONLINE'"],
                "ordenamiento": "TABLESPACE_NAME"
            })
            
            # Si menciona "uso", agregar cálculos de espacio
            if any("uso" in str(item).lower() for item in analisis.get("metricas_esperadas", [])):
                estructura["campos_necesarios"].extend(["BYTES", "MAXBYTES"])
                estructura["requires_space_calculation"] = True
        
        elif categoria == "sesiones":
            estructura.update({
                "vista_principal": "GV$SESSION",
                "campos_necesarios": ["USERNAME", "STATUS", "SID", "MACHINE", "PROGRAM"],
                "filtros_sugeridos": ["USERNAME IS NOT NULL"],
                "ordenamiento": "LOGON_TIME DESC"
            })
            
            # Filtros temporales
            if "hoy" in analisis.get("filtros_temporales", []):
                estructura["filtros_sugeridos"].append("TRUNC(LOGON_TIME) = TRUNC(SYSDATE)")
            
            # Si menciona "activas"
            if "activo" in str(analisis).lower():
                estructura["filtros_sugeridos"].append("STATUS = 'ACTIVE'")
        
        return estructura
    
    async def _enrich_context(self, estructura: Dict[str, Any], texto_original: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecer contexto con información adicional usando OpenAI"""
        
        prompt = f"""Como DBA experto en Oracle, revisa esta estructura SQL propuesta para la consulta del usuario:

CONSULTA ORIGINAL: "{texto_original}"

ESTRUCTURA PROPUESTA:
- Vista principal: {estructura['vista_principal']}
- Campos: {estructura['campos_necesarios']}
- Filtros: {estructura['filtros_sugeridos']}

¿Hay algo que mejorar o que falta? Responde en JSON:
{{
    "estructura_correcta": true/false,
    "mejoras_sugeridas": ["mejora1", "mejora2"],
    "campos_adicionales": ["campo1", "campo2"],
    "filtros_adicionales": ["filtro1"],
    "comentario": "explicación breve"
}}

JSON:"""

        try:
            respuesta = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un DBA Oracle experto. Devuelve ÚNICAMENTE JSON válido."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200,
                n=1
            )
            
            json_text = self._clean_json_response(respuesta.choices[0].message.content.strip())
            enriquecimiento = json.loads(json_text)
            
            return {
                "estructura_original": estructura,
                "validacion_ia": enriquecimiento,
                "recomendaciones_aplicadas": True
            }
            
        except Exception as e:
            self.log_error(f"Error enriqueciendo contexto: {str(e)}")
            return {
                "estructura_original": estructura,
                "validacion_ia": {"estructura_correcta": True, "comentario": "Validación no disponible"},
                "recomendaciones_aplicadas": False
            }
    
    def _calculate_confidence(self, analisis: Dict[str, Any], mapeo: Dict[str, Any]) -> float:
        """Calcular nivel de confianza del análisis"""
        confidence = 0.5  # Base
        
        # Incrementar por entidades detectadas
        entidades = len(analisis.get("entidades_involucradas", []))
        confidence += min(entidades * 0.15, 0.3)
        
        # Incrementar por acciones claras
        acciones = len(analisis.get("acciones_solicitadas", []))
        confidence += min(acciones * 0.1, 0.2)
        
        # Incrementar si hay categoría específica
        if mapeo["categoria"] != "general":
            confidence += 0.2
        
        return min(confidence, 1.0)
