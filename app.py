# =============================================================================
# ARCHIVO: app.py
# Descripción: Aplicación principal Flask mejorada
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

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        texto = data["message"]["text"]
        
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
        
        # Enviar respuesta a Telegram
        try:
            bot.send_message(chat_id=chat_id, text=respuesta)
        except Exception as e:
            print(f"❌ Error enviando mensaje: {str(e)}")
    
    return "ok"

@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok", "system": "multiagent-sql-bot"}

if __name__ == "__main__":
    print("🚀 Iniciando sistema multiagente...")
    print("📋 Agentes disponibles: Master, ConsultasPredefinidas, SQLGenerator, Analisis")
    app.run(host="0.0.0.0", port=5000, debug=True)
