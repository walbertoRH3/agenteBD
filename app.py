# =============================================================================
# ARCHIVO: app.py
# Descripción: Aplicación principal Flask con soporte de inventario BD - CORREGIDO
# =============================================================================

from flask import Flask, request
import telegram
import traceback
import asyncio
from config.settings import Config
from agents.agent_master import AgentMaster

# Validar configuración al inicio
Config.validate()

app = Flask(__name__)
bot = telegram.Bot(token=Config.TELEGRAM_TOKEN)
agent_master = AgentMaster()

def enviar_mensaje_seguro(chat_id, texto):
    """Enviar mensaje a Telegram de forma segura"""
    try:
        # Primero intentar con parse_mode=None (sin formato)
        bot.send_message(
            chat_id=chat_id, 
            text=texto,
            parse_mode=None
        )
        return True
    except Exception as e:
        print(f"❌ Error enviando mensaje: {str(e)}")
        
        # Si falla, intentar con texto más simple
        try:
            texto_simple = texto.replace('*', '').replace('_', '').replace('`', '')
            bot.send_message(
                chat_id=chat_id, 
                text=texto_simple,
                parse_mode=None
            )
            return True
        except Exception as e2:
            print(f"❌ Error enviando mensaje simplificado: {str(e2)}")
            
            # Último intento con mensaje de error genérico
            try:
                bot.send_message(
                    chat_id=chat_id, 
                    text="❌ Error procesando la respuesta. Intenta de nuevo.",
                    parse_mode=None
                )
                return True
            except Exception as e3:
                print(f"❌ Error enviando mensaje de error: {str(e3)}")
                return False

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        texto = data["message"]["text"]
        
        print(f"📥 Mensaje recibido de {chat_id}: {texto}")
        
        try:
            # Procesar con el sistema multiagente
            resultado = asyncio.run(agent_master.process({
                "texto": texto,
                "chat_id": chat_id
            }))
            
            respuesta = resultado["respuesta"]
            print(f"📤 Enviando respuesta: {respuesta[:100]}...")
            
        except Exception as e:
            print(f"❌ Error procesando mensaje: {str(e)}")
            traceback.print_exc()
            respuesta = f"❌ Error del sistema: {str(e)}"
        
        # Enviar respuesta a Telegram de forma segura
        enviar_mensaje_seguro(chat_id, respuesta)
    
    return "ok"

@app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "ok", 
        "system": "multiagent-sql-bot",
        "version": "2.0-fixed",
        "features": ["inventory", "multi-database", "predefined-queries", "ai-generation", "greetings"]
    }

@app.route("/test", methods=["GET"])
def test_system():
    """Endpoint para probar el sistema"""
    try:
        from agents.agent_db_inventory import AgentDBInventory
        inventory = AgentDBInventory()
        
        return {
            "status": "ok",
            "databases_loaded": len(inventory.databases),
            "databases": [
                {
                    "id": db["id"],
                    "aliases": db.get("aliases", []),
                    "host": db.get("connection", {}).get("host")
                }
                for db in inventory.databases
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 Iniciando sistema multiagente CORREGIDO...")
    print("📋 Agentes disponibles: Master, Saludo, DBInventory, ConsultasPredefinidas, SQLGenerator, Analisis")
    print("🗃️ Bases de datos configuradas:")
    
    # Mostrar inventario al inicio
    try:
        from agents.agent_db_inventory import AgentDBInventory
        inventory = AgentDBInventory()
        for db in inventory.databases:
            aliases = ", ".join(db.get('aliases', []))
            print(f"   • {db['id']}: {aliases} ({db.get('connection', {}).get('host')})")
    except Exception as e:
        print(f"   ❌ Error cargando inventario: {str(e)}")
    
    print("\n✅ Sistema listo para recibir consultas")
    print("🔧 Endpoints disponibles:")
    print("   • /webhook - Webhook de Telegram")
    print("   • /health - Estado del sistema")
    print("   • /test - Prueba de inventario")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
