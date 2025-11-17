#!/usr/bin/env python3
"""
Script para testar a conexão com o PostgreSQL
Usado para verificar se o serviço está funcionando corretamente
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

def test_postgres_connection():
    """Testa a conexão com o PostgreSQL e verifica as tabelas"""
    
    # Configurações do banco
    config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'chat_memory'),
        'user': os.getenv('POSTGRES_USER', 'chat_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'chat_password')
    }
    
    print("🔍 Testando conexão com PostgreSQL...")
    print(f"📊 Configurações: {json.dumps(config, indent=2)}")
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("✅ Conexão estabelecida com sucesso!")
        
        # Verificar se as tabelas existem
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('chat_messages', 'chat_sessions')
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"📋 Tabelas encontradas: {[table['table_name'] for table in tables]}")
        
        # Verificar estrutura da tabela chat_messages
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'chat_messages'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("\n📝 Estrutura da tabela chat_messages:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        # Testar inserção de uma mensagem de teste
        test_session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_message = {
            'session_id': test_session_id,
            'message': 'Esta é uma mensagem de teste para verificar a funcionalidade do PostgreSQL como memória do chat.',
            'metadata': json.dumps({'test': True, 'timestamp': datetime.now().isoformat()})
        }
        
        cursor.execute("""
            INSERT INTO chat_messages (session_id, message, metadata)
            VALUES (%(session_id)s, %(message)s, %(metadata)s)
            RETURNING id, created_at
        """, test_message)
        
        result = cursor.fetchone()
        print(f"\n✅ Mensagem de teste inserida com sucesso!")
        print(f"   ID: {result['id']}")
        print(f"   Timestamp: {result['created_at']}")
        
        # Verificar se a mensagem foi inserida
        cursor.execute("""
            SELECT id, session_id, message, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (test_session_id,))
        
        retrieved_message = cursor.fetchone()
        if retrieved_message:
            print(f"\n📖 Mensagem recuperada:")
            print(f"   ID: {retrieved_message['id']}")
            print(f"   Sessão: {retrieved_message['session_id']}")
            print(f"   Mensagem: {retrieved_message['message'][:50]}...")
            print(f"   Criada em: {retrieved_message['created_at']}")
        
        # Limpar mensagem de teste
        cursor.execute("DELETE FROM chat_messages WHERE session_id = %s", (test_session_id,))
        print(f"\n🧹 Mensagem de teste removida")
        
        # Verificar estatísticas
        cursor.execute("SELECT COUNT(*) as total_messages FROM chat_messages")
        total_messages = cursor.fetchone()['total_messages']
        print(f"\n📊 Total de mensagens no banco: {total_messages}")
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) as total_sessions FROM chat_messages")
        total_sessions = cursor.fetchone()['total_sessions']
        print(f"📊 Total de sessões únicas: {total_sessions}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n🎉 Todos os testes passaram com sucesso!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Erro na conexão com PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_postgres_connection()
    sys.exit(0 if success else 1) 