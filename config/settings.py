# =============================================================================
# ARCHIVO: config/settings.py
# Descripción: Configuración centralizada
# =============================================================================

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ORACLE_USER = os.getenv("ORACLE_USER")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
    ORACLE_DSN = os.getenv("ORACLE_DSN")
    
    # Validar que todas las variables estén configuradas
    @classmethod
    def validate(cls):
        required_vars = [
            cls.TELEGRAM_TOKEN,
            cls.OPENAI_API_KEY,
            cls.ORACLE_USER,
            cls.ORACLE_PASSWORD,
            cls.ORACLE_DSN
        ]
        
        if not all(required_vars):
            raise ValueError("❌ Faltan variables de entorno. Revisa tu archivo .env")
        
        print("✅ Configuración validada correctamente")
