# =============================================================================
# ARCHIVO: agents/agent_db_inventory.py
# Descripción: Agente para gestión de inventario de bases de datos
# =============================================================================

from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
import json
import os
import unicodedata
import re

class AgentDBInventory(BaseAgent):
    def __init__(self, inventory_file: str = "config/db_inventory.json"):
        super().__init__("DBInventory")
        self.inventory_file = inventory_file
        self.databases = self._load_inventory()
        
    def _load_inventory(self) -> List[Dict[str, Any]]:
        """Cargar inventario de bases de datos desde archivo JSON"""
        try:
            if not os.path.exists(self.inventory_file):
                self.log_error(f"Archivo de inventario no encontrado: {self.inventory_file}")
                return []
                
            with open(self.inventory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('databases', [])
                
        except Exception as e:
            self.log_error(f"Error cargando inventario: {str(e)}")
            return []
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para comparación"""
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower().strip()
    
    def _extract_db_names_from_text(self, text: str) -> List[str]:
        """Extraer posibles nombres de BD del texto del usuario"""
        words = text.split()
        potential_names = []
        
        # Buscar palabras que podrían ser nombres de BD
        for word in words:
            clean_word = re.sub(r'[^a-zA-Z0-9]', '', word)
            if len(clean_word) >= 2:  # Mínimo 2 caracteres
                potential_names.append(clean_word)
        
        return potential_names
    
    def find_database(self, db_identifier: str) -> Optional[Dict[str, Any]]:
        """Buscar base de datos por nombre o alias"""
        normalized_identifier = self._normalize_text(db_identifier)
        
        for db in self.databases:
            # Buscar en aliases
            for alias in db.get('aliases', []):
                if self._normalize_text(alias) == normalized_identifier:
                    self.log_info(f"BD encontrada: {db['id']} (alias: {alias})")
                    return db
            
            # Buscar en ID
            if self._normalize_text(db['id']) == normalized_identifier:
                self.log_info(f"BD encontrada: {db['id']} (por ID)")
                return db
        
        return None
    
    def get_database_connection_info(self, db_config: Dict[str, Any]) -> Dict[str, str]:
        """Obtener información de conexión para Oracle"""
        conn_info = db_config.get('connection', {})
        
        return {
            'user': conn_info.get('user'),
            'password': conn_info.get('password'),
            'host': conn_info.get('host'),
            'service_name': conn_info.get('service_name'),
            'role': conn_info.get('role', 'normal'),
            'dsn': f"{conn_info.get('host')}/{conn_info.get('service_name')}"
        }
    
    def list_available_databases(self) -> str:
        """Listar bases de datos disponibles"""
        if not self.databases:
            return "No hay bases de datos configuradas en el inventario."
        
        lista = "📋 Bases de datos disponibles:\n\n"
        
        for db in self.databases:
            aliases_str = ", ".join(f"'{alias}'" for alias in db.get('aliases', []))
            lista += f"🔸 {db['id']}\n"
            lista += f"   📝 Descripción: {db.get('description', 'Sin descripción')}\n"
            lista += f"   🏷️ Nombres válidos: {aliases_str}\n"
            lista += f"   🖥️ Host: {db.get('connection', {}).get('host')}\n\n"
        
        return lista
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar solicitud para identificar y validar BD"""
        texto_usuario = data.get("texto", "")
        chat_id = data.get("chat_id")
        intento = data.get("intento", 1)
        
        self.log_info(f"Procesando identificación de BD (intento {intento})")
        
        # Extraer posibles nombres de BD del texto
        posibles_nombres = self._extract_db_names_from_text(texto_usuario)
        
        # Buscar coincidencias
        db_encontrada = None
        nombre_usado = None
        
        for nombre in posibles_nombres:
            db_encontrada = self.find_database(nombre)
            if db_encontrada:
                nombre_usado = nombre
                break
        
        if db_encontrada:
            # BD encontrada
            conn_info = self.get_database_connection_info(db_encontrada)
            
            return {
                "bd_encontrada": True,
                "db_config": db_encontrada,
                "connection_info": conn_info,
                "nombre_usado": nombre_usado,
                "texto_sin_bd": self._remove_db_name_from_text(texto_usuario, nombre_usado),
                "procesado_por": self.name,
                "exito": True
            }
        
        else:
            # BD no encontrada
            if intento >= 2:
                # Segundo intento fallido
                mensaje_error = f"❌ Base de datos no encontrada después de 2 intentos.\n\n"
                mensaje_error += f"🔍 Nombres detectados en tu respuesta: {', '.join(posibles_nombres) if posibles_nombres else 'ninguno'}\n\n"
                mensaje_error += f"❗ Posibles causas:\n"
                mensaje_error += f"• El nombre no está en el inventario\n"
                mensaje_error += f"• Hay un error de escritura\n"
                mensaje_error += f"• No especificaste claramente el nombre\n\n"
                mensaje_error += f"💡 Sugerencia: Inicia una nueva consulta con el formato:\n"
                mensaje_error += f"[NOMBRE_BD] [tu consulta]\n\n"
                mensaje_error += f"{self.list_available_databases()}"
                
                return {
                    "bd_encontrada": False,
                    "error": "bd_no_encontrada",
                    "mensaje": mensaje_error,
                    "procesado_por": self.name,
                    "exito": False
                }
            else:
                # Primer intento fallido, solicitar nombre
                mensaje_solicitud = f"❗ Necesito el nombre de la base de datos para continuar.\n\n"
                mensaje_solicitud += f"👉 Responde solo con el nombre de la BD seguido de tu consulta.\n"
                mensaje_solicitud += f"Ejemplo: BRM, la base de datos es SAP   \n\n"
                
                return {
                    "bd_encontrada": False,
                    "error": "bd_requerida",
                    "mensaje": mensaje_solicitud,
                    "intento": intento + 1,
                    "procesado_por": self.name,
                    "exito": False,
                    "requiere_respuesta": True
                }
    
    def _remove_db_name_from_text(self, texto: str, db_name: str) -> str:
        """Remover el nombre de BD del texto para procesar la consulta real"""
        # Remover el nombre de BD encontrado del texto
        pattern = re.compile(r'\b' + re.escape(db_name) + r'\b', re.IGNORECASE)
        texto_limpio = pattern.sub('', texto).strip()
        
        # Limpiar espacios múltiples y palabras conectoras comunes
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
        texto_limpio = re.sub(r'\b(en|de|del|la|el|para|con|sobre)\s+', ' ', texto_limpio, flags=re.IGNORECASE)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        
        # Si el texto queda muy corto, devolver texto original sin el nombre de BD
        if len(texto_limpio) < 3:
            words = texto.split()
            filtered_words = [w for w in words if w.lower() != db_name.lower()]
            texto_limpio = ' '.join(filtered_words)
        
        return texto_limpio
