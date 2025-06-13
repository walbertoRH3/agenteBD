# =============================================================================
# ARCHIVO: app.py
# Descripción: Aplicación principal Flask con soporte de inventario BD
# =============================================================================

import os
import sys
from flask import Flask, request, jsonify
import asyncio
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verificar imports críticos
try:
    from config.settings import Config
    logger.info("✅ Config importado correctamente")
except ImportError as e:
    logger.error(f"❌ Error importando Config: {e}")
    print("❌ No se pudo importar config.settings.Config")
    print("💡 Verifica que existe el archivo config/settings.py")
    sys.exit(1)

try:
    from agents.agent_master import AgentMaster
    logger.info("✅ AgentMaster importado correctamente")
except ImportError as e:
    logger.error(f"❌ Error importando AgentMaster: {e}")
    print("❌ No se pudo importar agents.agent_master.AgentMaster")
    print("💡 Verifica que existe el archivo agents/agent_master.py")
    sys.exit(1)

# Importación de Telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError
    logger.info("✅ Telegram Bot importado correctamente")
except ImportError as e:
    logger.error(f"❌ Error importando Bot: {e}")
    print("❌ No se pudo importar telegram.Bot")
    print("💡 Ejecuta: pip install python-telegram-bot==20.6")
    sys.exit(1)

# Crear app Flask
app = Flask(__name__)

# Variables globales
bot = None
agent_master = None
executor = ThreadPoolExecutor(max_workers=4)

# Event loop global para async operations
_loop = None
_loop_thread = None
_loop_lock = threading.Lock()

def inicializar_configuracion():
    """Inicializar y validar configuración"""
    try:
        Config.validate()
        logger.info("✅ Configuración validada")
        return True
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        print(f"❌ Error en configuración: {e}")
        return False

def inicializar_bot():
    """Inicializar bot de Telegram"""
    global bot
    try:
        if not hasattr(Config, 'TELEGRAM_TOKEN') or not Config.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN no configurado")
        
        # Crear bot con configuración de conexión mejorada
        from telegram.request import HTTPXRequest
        request_instance = HTTPXRequest(
            connection_pool_size=8,
            pool_timeout=20.0,
            read_timeout=10.0,
            write_timeout=10.0,
            connect_timeout=5.0
        )
        
        bot = Bot(token=Config.TELEGRAM_TOKEN, request=request_instance)
        logger.info("✅ Bot de Telegram inicializado")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando bot: {e}")
        print(f"❌ Error creando bot: {e}")
        return False

def inicializar_agente():
    """Inicializar sistema de agentes"""
    global agent_master
    try:
        agent_master = AgentMaster()
        logger.info("✅ Sistema de agentes inicializado")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando agentes: {e}")
        print(f"❌ Error creando agentes: {e}")
        return False

def get_or_create_event_loop():
    """Obtener o crear el event loop global"""
    global _loop, _loop_thread
    
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            def run_loop():
                global _loop
                _loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_loop)
                try:
                    _loop.run_forever()
                except Exception as e:
                    logger.error(f"❌ Error en event loop: {e}")
                finally:
                    _loop.close()
            
            _loop_thread = threading.Thread(target=run_loop, daemon=True)
            _loop_thread.start()
            
            # Esperar a que el loop esté disponible
            timeout = 5  # 5 segundos máximo
            start_time = time.time()
            while (_loop is None or not _loop.is_running()) and (time.time() - start_time) < timeout:
                time.sleep(0.01)
        
        return _loop

def run_async_in_thread(coro):
    """Ejecutar corrutina usando el event loop global"""
    try:
        loop = get_or_create_event_loop()
        if loop is None or loop.is_closed():
            logger.error("❌ Event loop no disponible")
            return None
            
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30)
    except Exception as e:
        logger.error(f"❌ Error ejecutando async: {e}")
        return None

async def enviar_mensaje_telegram(chat_id, texto):
    """Enviar mensaje a Telegram"""
    if not bot:
        logger.error("❌ Bot no inicializado")
        return False
        
    try:
        if not texto or not texto.strip():
            texto = "❌ Respuesta vacía"
        
        if len(texto) > 4096:
            texto = texto[:4090] + "..."
        
        await bot.send_message(
            chat_id=chat_id,
            text=texto,
            parse_mode=None
        )
        logger.info(f"✅ Mensaje enviado a {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")
        try:
            # Intento simplificado
            texto_simple = str(texto)[:4000].replace('*', '').replace('_', '')
            await bot.send_message(
                chat_id=chat_id,
                text=texto_simple or "Error procesando respuesta",
                parse_mode=None
            )
            return True
        except Exception as e2:
            logger.error(f"❌ Error crítico: {e2}")
            return False

def enviar_mensaje_seguro(chat_id, texto):
    """Wrapper para enviar mensajes"""
    if not bot:
        logger.error("❌ Bot no disponible")
        return False
    
    try:
        return run_async_in_thread(enviar_mensaje_telegram(chat_id, texto))
    except Exception as e:
        logger.error(f"❌ Error en envío seguro: {e}")
        return False

def procesar_con_agente(texto, chat_id):
    """Procesar mensaje con agentes"""
    if not agent_master:
        return "❌ Sistema de agentes no disponible"
    
    try:
        if asyncio.iscoroutinefunction(agent_master.process):
            resultado = run_async_in_thread(agent_master.process({
                "texto": texto,
                "chat_id": chat_id
            }))
        else:
            resultado = agent_master.process({
                "texto": texto,
                "chat_id": chat_id
            })
        
        if isinstance(resultado, dict):
            return resultado.get("respuesta", "✅ Procesado")
        else:
            return str(resultado) if resultado else "❌ Sin respuesta"
            
    except Exception as e:
        logger.error(f"❌ Error procesando con agente: {e}")
        return f"❌ Error del sistema: {str(e)}"

@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook para Telegram"""
    try:
        data = request.get_json()
        
        if not data or "message" not in data:
            return jsonify({"status": "no message"}), 400
            
        message = data["message"]
        
        if "text" not in message or "chat" not in message:
            return jsonify({"status": "incomplete"}), 400
            
        chat_id = message["chat"]["id"]
        texto = message["text"].strip()
        
        logger.info(f"📨 Mensaje de {chat_id}: {texto[:50]}...")
        
        # Comandos de ayuda
        if texto.lower() in ['/help', '/ayuda', 'ayuda', 'help', '/start']:
            respuesta = generar_mensaje_ayuda()
        else:
            respuesta = procesar_con_agente(texto, chat_id)
        
        # Enviar respuesta
        if respuesta:
            exito = enviar_mensaje_seguro(chat_id, respuesta)
            if exito:
                logger.info(f"✅ Respuesta enviada a {chat_id}")
            else:
                logger.error(f"❌ Falló envío a {chat_id}")
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

def generar_mensaje_ayuda():
    """Mensaje de ayuda"""
    return """🤖 Bot Consultor SQL Multibase v2.0

📝 Uso:
1. Especifica la BD en tu consulta
2. Escribe en lenguaje natural
3. Recibe resultados y análisis

🎯 Ejemplos:
• BRM estado de la base
• SAP usuarios conectados
• consultas procesos activos

📊 Bases disponibles:
• BRM: brm, BRM, consultas
• SAP: sap, SAP, facturas

🔧 Comandos:
• /help - Esta ayuda

💡 Siempre incluye el nombre de la BD"""

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    status = {
        "status": "ok",
        "system": "multiagent-sql-bot",
        "version": "2.0",
        "components": {
            "flask": "running",
            "bot": "ok" if bot else "error",
            "agents": "ok" if agent_master else "error",
            "executor": f"{executor._max_workers} workers"
        }
    }
    
    return jsonify(status)

@app.route("/test", methods=["GET"])
def test_endpoint():
    """Test básico"""
    return jsonify({
        "status": "ok",
        "message": "Servidor Flask funcionando",
        "port": 5000
    })

@app.route("/", methods=["GET"])
def root():
    """Página raíz"""
    return jsonify({
        "service": "Bot Consultor SQL Multibase",
        "version": "2.0",
        "endpoints": ["/health", "/test", "/webhook"],
        "status": "running"
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500

def verificar_puerto_disponible(port=5000):
    """Verificar si el puerto está disponible"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            return True
    except OSError:
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando Bot Consultor SQL Multibase v2.0")
    
    # Verificar puerto
    if not verificar_puerto_disponible(5000):
        print("❌ Puerto 5000 ocupado")
        print("💡 Ejecuta: lsof -ti:5000 | xargs kill -9")
        return False
    
    # Inicializar componentes
    if not inicializar_configuracion():
        return False
    
    if not inicializar_bot():
        print("⚠️  Continuando sin bot (modo desarrollo)")
    
    if not inicializar_agente():
        print("⚠️  Continuando sin agentes (modo desarrollo)")
    
    print("✅ Sistema inicializado")
    print("🌐 Servidor disponible en:")
    print("   • Local: http://localhost:5000")
    print("   • Red: http://0.0.0.0:5000")
    print("📡 Endpoints disponibles:")
    print("   • GET  /health - Estado del sistema")
    print("   • GET  /test - Test básico")
    print("   • POST /webhook - Webhook de Telegram")
    
    return True

if __name__ == "__main__":
    try:
        if main():
            app.run(
                host="0.0.0.0", 
                port=5000, 
                debug=False,  # Cambiar a False para producción
                threaded=True,
                use_reloader=False  # Evitar problemas con threading
            )
    except KeyboardInterrupt:
        print("\n👋 Cerrando aplicación...")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        traceback.print_exc()
    finally:
        executor.shutdown(wait=True)
        print("✅ Recursos liberados")