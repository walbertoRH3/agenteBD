# =============================================================================
# ARCHIVO: app.py
# Descripción: Aplicación principal Flask con soporte de inventario BD
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
        
        # Verificar si es comando de ayuda
        if texto.lower().strip() in ['/help', '/ayuda', 'ayuda', 'help']:
            respuesta = generar_mensaje_ayuda()
        else:
            try:
                # Procesar con el sistema multiagente
                resultado = asyncio.run(agent_master.process({
                    "texto": texto,
                    "chat_id": chat_id
                }))
                
                respuesta = resultado["respuesta"]
                
            except Exception as e:
                traceback.print_exc()
                respuesta = f"❌ Error del sistema:\n{str(e)}"
        
        # Enviar respuesta a Telegram de forma segura
        enviar_mensaje_seguro(chat_id, respuesta)
    
    return "ok"

def generar_mensaje_ayuda():
    """Generar mensaje de ayuda del sistema"""
    return """🤖 Bot Consultor SQL Multibase v2.0

📝 Cómo usar:
1. Especifica la base de datos en tu consulta (OBLIGATORIO)
2. Escribe tu consulta en lenguaje natural
3. Recibe resultados con análisis experto

🎯 Ejemplos correctos:
• BRM estado de la base
• SAP usuarios conectados hoy
• consultas procesos activos
• facturas sesiones bloqueadas

❌ Ejemplos incorrectos:
• estado de la base (falta nombre BD)
• usuarios conectados (falta nombre BD)

📊 Bases disponibles:
• BRM: brm, BRM, consultas
• SAP: sap, SAP, facturas

⚠️ Sistema de intentos:
• 1er intento sin BD: Te pediré especificar la base
• 2do intento sin BD: Consulta será rechazada
• BD encontrada: Procesamiento normal

🔧 Comandos:
• /help o /ayuda - Mostrar esta ayuda

💡 Tip: Si no funciona al segundo intento, inicia una nueva consulta con formato: [NOMBRE_BD] [consulta]
"""

@app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "ok", 
        "system": "multiagent-sql-bot",
        "version": "2.0",
        "features": ["inventory", "multi-database", "predefined-queries", "ai-generation"]
    }

if __name__ == "__main__":
    print("🚀 Iniciando sistema multiagente con inventario BD...")
    print("📋 Agentes disponibles: Master, DBInventory, ConsultasPredefinidas, SQLGenerator, Analisis")
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
    
    app.run(host="0.0.0.0", port=5000, debug=True)
