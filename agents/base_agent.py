# =============================================================================
# ARCHIVO: agents/base_agent.py
# Descripción: Clase base para todos los agentes
# =============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Agent.{name}")
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa los datos de entrada y retorna el resultado"""
        pass
    
    def log_info(self, message: str):
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        self.logger.error(f"[{self.name}] {message}")
