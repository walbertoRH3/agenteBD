# =============================================================================
# ARCHIVO: test_db_inventory.py
# Descripción: Pruebas del sistema de inventario
# =============================================================================

import asyncio
import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_db_inventory import AgentDBInventory
from agents.agent_master import AgentMaster

async def test_inventory():
    """Probar funcionalidad del inventario"""
    print("🧪 INICIANDO PRUEBAS DEL INVENTARIO\n")
    
    # Crear agente de inventario
    agent = AgentDBInventory()
    
    print(f"📁 Bases de datos cargadas: {len(agent.databases)}")
    for db in agent.databases:
        print(f"   • {db['id']}: {', '.join(db['aliases'])}")
    
    print("\n" + "="*50)
    
    # Casos de prueba
    casos_prueba = [
        "estado de la base BRM",
        "consultas en sap",
        "usuarios conectados",  # Sin BD
        "facturas del sistema",  # Alias
        "revisar base xyz",  # BD inexistente
    ]
    
    for caso in casos_prueba:
        print(f"\n🔍 PROBANDO: '{caso}'")
        resultado = await agent.process({
            "texto": caso,
            "chat_id": "test_123",
            "intento": 1
        })
        
        if resultado.get("bd_encontrada"):
            print(f"   ✅ BD encontrada: {resultado['db_config']['id']}")
            print(f"   📝 Consulta limpia: '{resultado['texto_sin_bd']}'")
        else:
            print(f"   ❌ BD no encontrada: {resultado.get('error')}")
            print(f"   💬 Mensaje: {resultado.get('mensaje', 'Sin mensaje')[:100]}...")

async def test_conversation_flow():
    """Probar flujo completo de conversación"""
    print("\n\n🎭 PROBANDO FLUJO DE CONVERSACIÓN\n")
    
    master = AgentMaster()
    chat_id = "test_conversation"
    
    # Simulación de conversación
    print("👤 Usuario: 'usuarios conectados'")
    resultado1 = await master.process({
        "texto": "usuarios conectados",
        "chat_id": chat_id
    })
    
    print(f"🤖 Bot: {resultado1['respuesta'][:200]}...")
    print(f"✅ Éxito: {resultado1['exito']}")
    
    if not resultado1['exito']:
        print("\n👤 Usuario: 'BRM usuarios conectados'")
        resultado2 = await master.process({
            "texto": "BRM usuarios conectados",
            "chat_id": chat_id
        })
        
        print(f"🤖 Bot: {resultado2['respuesta'][:200]}...")
        print(f"✅ Éxito: {resultado2['exito']}")

if __name__ == "__main__":
    print("🚀 EJECUTANDO PRUEBAS DEL SISTEMA\n")
    
    try:
        asyncio.run(test_inventory())
        asyncio.run(test_conversation_flow())
        print("\n✅ PRUEBAS COMPLETADAS")
    except Exception as e:
        print(f"\n❌ ERROR EN PRUEBAS: {str(e)}")
        import traceback
        traceback.print_exc()
