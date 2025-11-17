#!/usr/bin/env python3
"""Script de teste para o sistema de sessões."""

import sys
import os
import requests
import json
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_session_system():
    """Testa o sistema de sessões."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testando Sistema de Sessões")
    print("=" * 50)
    
    # Teste 1: Criar sessão
    print("\n1. Criando nova sessão...")
    try:
        response = requests.post(
            f"{base_url}/api/sessions",
            json={"name": "Sessão de Teste"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"✅ Sessão criada: {session_id}")
        else:
            print(f"❌ Erro ao criar sessão: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return False
    
    # Teste 2: Listar sessões
    print("\n2. Listando sessões...")
    try:
        response = requests.get(f"{base_url}/api/sessions")
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get('sessions', [])
            print(f"✅ Encontradas {len(sessions)} sessões")
            
            for session in sessions:
                print(f"   - {session.get('name', 'Sem nome')} ({session.get('message_count', 0)} mensagens)")
        else:
            print(f"❌ Erro ao listar sessões: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 3: Enviar mensagem via chat
    print(f"\n3. Enviando mensagem para sessão {session_id}...")
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "message": "Olá, esta é uma mensagem de teste!",
                "session_id": session_id,
                "collection_name": None,
                "similarity_threshold": 0.0
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Resposta recebida: {result.get('response', '')[:100]}...")
            print(f"   Processado por: {result.get('processed_by', 'unknown')}")
        else:
            print(f"❌ Erro no chat: {response.status_code}")
            print(f"   Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 4: Obter sessão específica
    print(f"\n4. Obtendo detalhes da sessão {session_id}...")
    try:
        response = requests.get(f"{base_url}/api/sessions/{session_id}")
        
        if response.status_code == 200:
            result = response.json()
            session = result.get('session', {})
            messages = session.get('messages', [])
            print(f"✅ Sessão obtida: {session.get('name', 'Sem nome')}")
            print(f"   Mensagens: {len(messages)}")
            
            for i, msg in enumerate(messages[:3]):  # Mostrar apenas as primeiras 3
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]
                print(f"   {i+1}. [{role}] {content}...")
        else:
            print(f"❌ Erro ao obter sessão: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 5: Obter mensagens da sessão
    print(f"\n5. Obtendo mensagens da sessão {session_id}...")
    try:
        response = requests.get(f"{base_url}/api/sessions/{session_id}/messages")
        
        if response.status_code == 200:
            result = response.json()
            messages = result.get('messages', [])
            print(f"✅ {len(messages)} mensagens obtidas")
        else:
            print(f"❌ Erro ao obter mensagens: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 6: Atualizar nome da sessão
    print(f"\n6. Atualizando nome da sessão {session_id}...")
    try:
        new_name = f"Sessão Atualizada - {datetime.now().strftime('%H:%M:%S')}"
        response = requests.put(
            f"{base_url}/api/sessions/{session_id}/name",
            json={"name": new_name},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Nome atualizado para: {new_name}")
        else:
            print(f"❌ Erro ao atualizar nome: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 7: Enviar mais uma mensagem
    print(f"\n7. Enviando segunda mensagem...")
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "message": "Esta é a segunda mensagem de teste!",
                "session_id": session_id,
                "collection_name": None,
                "similarity_threshold": 0.0
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Segunda resposta recebida")
        else:
            print(f"❌ Erro no chat: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 8: Verificar se as mensagens foram salvas
    print(f"\n8. Verificando mensagens salvas...")
    try:
        response = requests.get(f"{base_url}/api/sessions/{session_id}")
        
        if response.status_code == 200:
            result = response.json()
            session = result.get('session', {})
            messages = session.get('messages', [])
            print(f"✅ Total de mensagens na sessão: {len(messages)}")
            
            if len(messages) >= 4:  # 2 do usuário + 2 do assistente
                print("✅ Sistema de persistência funcionando corretamente!")
            else:
                print("⚠️ Sistema de persistência pode ter problemas")
        else:
            print(f"❌ Erro ao verificar sessão: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Teste do sistema de sessões concluído!")
    
    return True

if __name__ == "__main__":
    test_session_system() 