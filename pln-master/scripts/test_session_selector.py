#!/usr/bin/env python3
"""Script de teste para o seletor de sessões no chat."""

import sys
import os
import requests
import json
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_session_selector():
    """Testa o seletor de sessões no chat."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testando Seletor de Sessões no Chat")
    print("=" * 50)
    
    # Teste 1: Criar múltiplas sessões
    print("\n1. Criando múltiplas sessões para teste...")
    session_ids = []
    
    for i in range(3):
        try:
            response = requests.post(
                f"{base_url}/api/sessions",
                json={"name": f"Sessão de Teste {i+1}"},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('session_id')
                session_ids.append(session_id)
                print(f"✅ Sessão {i+1} criada: {session_id}")
            else:
                print(f"❌ Erro ao criar sessão {i+1}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    if not session_ids:
        print("❌ Nenhuma sessão foi criada. Abortando teste.")
        return False
    
    # Teste 2: Enviar mensagens para as sessões
    print(f"\n2. Enviando mensagens para as sessões...")
    
    for i, session_id in enumerate(session_ids):
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json={
                    "message": f"Mensagem de teste {i+1} para sessão {i+1}",
                    "session_id": session_id,
                    "collection_name": None,
                    "similarity_threshold": 0.0
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Mensagem enviada para sessão {i+1}")
            else:
                print(f"❌ Erro ao enviar mensagem para sessão {i+1}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    # Teste 3: Verificar se as sessões aparecem na lista
    print(f"\n3. Verificando lista de sessões...")
    try:
        response = requests.get(f"{base_url}/api/sessions")
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get('sessions', [])
            print(f"✅ Encontradas {len(sessions)} sessões na lista")
            
            # Verificar se nossas sessões estão na lista
            test_sessions = [s for s in sessions if s.get('name', '').startswith('Sessão de Teste')]
            print(f"✅ {len(test_sessions)} sessões de teste encontradas")
            
            for session in test_sessions:
                print(f"   - {session.get('name')} ({session.get('message_count', 0)} mensagens)")
        else:
            print(f"❌ Erro ao listar sessões: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # Teste 4: Testar carregamento de sessão específica
    print(f"\n4. Testando carregamento de sessão específica...")
    if session_ids:
        try:
            session_id = session_ids[0]
            response = requests.get(f"{base_url}/api/sessions/{session_id}")
            
            if response.status_code == 200:
                result = response.json()
                session = result.get('session', {})
                messages = session.get('messages', [])
                print(f"✅ Sessão carregada: {session.get('name')}")
                print(f"   Mensagens: {len(messages)}")
                
                for i, msg in enumerate(messages[:2]):  # Mostrar apenas as primeiras 2
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:50]
                    print(f"   {i+1}. [{role}] {content}...")
            else:
                print(f"❌ Erro ao carregar sessão: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    # Teste 5: Testar atualização de nome de sessão
    print(f"\n5. Testando atualização de nome de sessão...")
    if session_ids:
        try:
            session_id = session_ids[0]
            new_name = f"Sessão Atualizada - {datetime.now().strftime('%H:%M:%S')}"
            
            response = requests.put(
                f"{base_url}/api/sessions/{session_id}/name",
                json={"name": new_name},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Nome atualizado para: {new_name}")
                
                # Verificar se o nome foi atualizado
                response = requests.get(f"{base_url}/api/sessions/{session_id}")
                if response.status_code == 200:
                    result = response.json()
                    session = result.get('session', {})
                    if session.get('name') == new_name:
                        print("✅ Nome atualizado com sucesso!")
                    else:
                        print("⚠️ Nome não foi atualizado corretamente")
            else:
                print(f"❌ Erro ao atualizar nome: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    # Teste 6: Testar envio de mensagem com session_id
    print(f"\n6. Testando envio de mensagem com session_id...")
    if session_ids:
        try:
            session_id = session_ids[0]
            
            response = requests.post(
                f"{base_url}/api/chat",
                json={
                    "message": "Mensagem de teste com session_id específico",
                    "session_id": session_id,
                    "collection_name": None,
                    "similarity_threshold": 0.0
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                returned_session_id = result.get('session_id')
                
                if returned_session_id == session_id:
                    print("✅ session_id enviado e retornado corretamente")
                else:
                    print(f"⚠️ session_id não corresponde: enviado={session_id}, retornado={returned_session_id}")
            else:
                print(f"❌ Erro ao enviar mensagem: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Teste do seletor de sessões concluído!")
    print("\n📋 Para testar no frontend:")
    print("1. Acesse: http://localhost:5000")
    print("2. Vá para aba 'Chat Multi-Agente'")
    print("3. Use o seletor de sessões para escolher uma sessão")
    print("4. Envie mensagens e verifique se o session_id é enviado")
    
    return True

if __name__ == "__main__":
    test_session_selector() 