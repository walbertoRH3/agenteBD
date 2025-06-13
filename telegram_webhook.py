#!/usr/bin/env python3
"""
Script para gestionar el webhook de Telegram
"""

import requests
import sys

TOKEN = "8043933777:AAEwVph3Zey3Sb_S671HN5PTa_HAqDPXD_E"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def get_webhook_info():
    """Obtener información del webhook actual"""
    response = requests.get(f"{BASE_URL}/getWebhookInfo")
    if response.status_code == 200:
        info = response.json()
        if info["ok"]:
            result = info["result"]
            print(f"✅ Webhook Info:")
            print(f"   URL: {result.get('url', 'No configurado')}")
            print(f"   Certificado personalizado: {result.get('has_custom_certificate', False)}")
            print(f"   Updates pendientes: {result.get('pending_update_count', 0)}")
            print(f"   Último error: {result.get('last_error_message', 'Ninguno')}")
            return result
        else:
            print(f"❌ Error: {info['description']}")
    else:
        print(f"❌ Error HTTP {response.status_code}")
    return None

def set_webhook(url):
    """Configurar webhook"""
    response = requests.post(f"{BASE_URL}/setWebhook", json={"url": url})
    if response.status_code == 200:
        info = response.json()
        if info["ok"]:
            print(f"✅ Webhook configurado: {url}")
            return True
        else:
            print(f"❌ Error configurando webhook: {info['description']}")
    else:
        print(f"❌ Error HTTP {response.status_code}")
    return False

def delete_webhook():
    """Eliminar webhook"""
    response = requests.post(f"{BASE_URL}/deleteWebhook")
    if response.status_code == 200:
        info = response.json()
        if info["ok"]:
            print("✅ Webhook eliminado")
            return True
        else:
            print(f"❌ Error eliminando webhook: {info['description']}")
    else:
        print(f"❌ Error HTTP {response.status_code}")
    return False

def test_bot():
    """Probar conexión del bot"""
    response = requests.get(f"{BASE_URL}/getMe")
    if response.status_code == 200:
        info = response.json()
        if info["ok"]:
            bot_info = info["result"]
            print(f"✅ Bot conectado: @{bot_info['username']} ({bot_info['first_name']})")
            return True
        else:
            print(f"❌ Error: {info['description']}")
    else:
        print(f"❌ Error HTTP {response.status_code}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python webhook_manager.py info          # Ver info del webhook")
        print("  python webhook_manager.py set <URL>     # Configurar webhook")
        print("  python webhook_manager.py delete        # Eliminar webhook")
        print("  python webhook_manager.py test          # Probar bot")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "info":
        get_webhook_info()
    elif command == "set" and len(sys.argv) > 2:
        url = sys.argv[2]
        set_webhook(url)
        print("\nVerificando...")
        get_webhook_info()
    elif command == "delete":
        delete_webhook()
        print("\nVerificando...")
        get_webhook_info()
    elif command == "test":
        test_bot()
    else:
        print("❌ Comando inválido")
        sys.exit(1)