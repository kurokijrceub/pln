"""Aplicação Flask principal do RAG-Demo."""

import os
import json
import sys
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from src.config import get_config
from src.document_processor import DocumentProcessor
from src.qa_generator import qa_generator
from langchain_core.documents import Document
from src.vector_store import QdrantVectorStore
from src.storage import StorageManager
from src.chat_rag_service import ChatManager
from src.debug_utils import charset_debugger
from src.entity_study_service import (
    DEFAULT_MAX_CHUNKS,
    DEFAULT_TOP_N,
    CONTEXT_NEIGHBORS,
    clamp_neighbor_top,
    run_entity_study,
    run_gliner_entity_study,
)
from src.gliner_bert_client import (
    GlinerBertUnavailable,
    health as gliner_health,
    list_models as gliner_list_models,
    reload_model as gliner_reload_model,
    start_train as gliner_start_train,
    train_status as gliner_train_status,
)


def sanitize_content(content: str) -> str:
    """Sanitiza conteúdo de arquivos para prevenir problemas de charset."""
    if not isinstance(content, str):
        content = str(content)
    
    try:
        # 1. Remover caracteres de controle (exceto quebras de linha)
        content = ''.join(char for char in content if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')
        
        # 2. Normalizar Unicode
        content = unicodedata.normalize('NFKC', content)
        
        # 3. Remover surrogates UTF-16 problemáticos
        content = content.encode('utf-8', 'ignore').decode('utf-8')
        
        # 4. Remover caracteres não-printáveis
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # 5. Normalizar espaços e quebras de linha
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 6. Limpar linhas
        content = '\n'.join(line.strip() for line in content.split('\n'))
        
        # 7. Verificação final
        content.encode('utf-8')
        
        return content.strip()
        
    except Exception as e:
        print(f"⚠️ Erro na sanitização de conteúdo: {e}", file=sys.stderr)
        # Fallback mais agressivo
        try:
            content = content.encode('ascii', 'ignore').decode('ascii')
            return content.strip()
        except:
            print("❌ Falha completa na sanitização, retornando conteúdo vazio", file=sys.stderr)
            return "Conteúdo não pôde ser processado devido a problemas de codificação"


# Configuração
config = get_config()

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar serviços
document_processor = DocumentProcessor()
storage_manager = StorageManager()
chat_manager = ChatManager()

# Verificar qual tipo de storage está sendo usado
print(f"🗄️ Tipo de storage: {'MinIO' if storage_manager.use_minio else 'Local'}", file=sys.stderr)
print(f"🗄️ Classe de storage: {type(storage_manager.storage).__name__}", file=sys.stderr)

# Inicializar banco de vetores (Qdrant)
import time
max_retries = 5
retry_delay = 5

for attempt in range(max_retries):
    try:
        print(f"🔄 Tentativa {attempt + 1}/{max_retries} de conectar ao Qdrant...")
        vector_store = QdrantVectorStore()
        use_qdrant = True
        print("✅ Conectado ao Qdrant com sucesso!")
        break
    except Exception as e:
        print(f"❌ Erro ao conectar ao Qdrant (tentativa {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            print(f"⏳ Aguardando {retry_delay} segundos antes da próxima tentativa...")
            time.sleep(retry_delay)
        else:
            print("❌ Qdrant é obrigatório para este projeto")
            raise e

# Criar diretórios necessários
Path("uploads").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)


@socketio.on('chat_message')
def handle_chat_message(data):
    """Handler para mensagens de chat via WebSocket com suporte a sessões."""
    try:
        message = data.get('message')
        session_id = data.get('session_id')
        collection_name = data.get('collection_name')
        similarity_threshold = data.get('similarity_threshold', 0.0)
        
        if not message:
            emit('chat_response', {'error': 'Mensagem é obrigatória'})
            return
        
        # Validar threshold de similaridade
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0.0 or similarity_threshold > 1.0:
            similarity_threshold = 0.0
        
        # Para busca por similaridade, criar sessão temporária se não fornecida
        if not session_id:
            session_id = chat_manager.create_session("Busca por Similaridade")
        
        # Processar mensagem usando o ChatManager
        result = chat_manager.chat(
            session_id=session_id,
            message=message,
            collection_names=collection_name,
            similarity_threshold=similarity_threshold,
            skip_n8n=True,
        )
        
        # Enviar resposta via WebSocket
        emit('chat_response', {
            'success': True,
            'response': result['response'],
            'sources': result.get('sources', []),
            'session_id': result.get('session_id'),
            'collections_used': result.get('collections_used', []),
            'processed_by': result.get('processed_by', 'unknown'),
            'similarity_threshold': similarity_threshold
        })
        
    except Exception as e:
        print(f"❌ Erro no handle_chat_message: {e}")
        emit('chat_response', {'error': str(e)})


def _run_document_search(query: str, collection_name, mode: str,
                         similarity_threshold: float, top_k: int):
    """Executa busca densa, léxica ou híbrida em uma ou todas as collections."""
    collection_names = collection_name
    if isinstance(collection_names, str):
        collection_names = [collection_names] if collection_names.strip() else []
    elif collection_names is None:
        collection_names = []

    results = chat_manager.chat_service.multi_agent_service.query_knowledge_sources(
        query=query,
        source_names=collection_names,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        mode=mode,
    )
    for item in results:
        if "id" in item:
            item["id"] = str(item["id"])
    return results


@app.route('/api/search', methods=['POST'])
def search_documents():
    """Busca de documentos: dense (semântica), lexical ou hybrid (RRF)."""
    try:
        data = request.get_json() or {}
        query = (data.get('query') or data.get('message') or '').strip()
        mode = (data.get('mode') or 'dense').strip().lower()
        collection_name = data.get('collection_name') or data.get('collection_names')
        similarity_threshold = data.get('similarity_threshold', 0.0)
        top_k = int(data.get('top_k', 10))

        if not query:
            return jsonify({'success': False, 'error': 'Consulta é obrigatória'}), 400

        if mode not in ('dense', 'lexical', 'hybrid', 'sparse', 'bm25', 'hibrida', 'híbrida'):
            return jsonify({'success': False, 'error': f'Modo de busca inválido: {mode}'}), 400

        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0 or similarity_threshold > 1:
            similarity_threshold = 0.0

        top_k = max(1, min(top_k, 50))
        sources = _run_document_search(
            query=query,
            collection_name=collection_name,
            mode=mode,
            similarity_threshold=similarity_threshold,
            top_k=top_k,
        )

        mode_label = {
            'dense': 'semântica (densa)',
            'lexical': 'léxica (esparsa)',
            'sparse': 'léxica (esparsa)',
            'bm25': 'léxica (esparsa)',
            'hybrid': 'híbrida (RRF)',
            'hibrida': 'híbrida (RRF)',
            'híbrida': 'híbrida (RRF)',
        }.get(mode, mode)

        return jsonify({
            'success': True,
            'mode': mode,
            'query': query,
            'sources': sources,
            'similarity_threshold': similarity_threshold,
            'response': f'Encontrados {len(sources)} trechos na busca {mode_label}.',
        })
    except Exception as e:
        print(f"❌ Erro em /api/search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def emit_entity_study_progress(step: str, progress: int, message: str):
    """Progresso do estudo TF-IDF + NER via Socket.IO."""
    socketio.emit('entity_study_progress', {
        'step': step,
        'progress': progress,
        'message': message,
    })


def _golden_set_download(result: dict):
    """Resposta HTTP com o rascunho do golden set para download."""
    collection = result.get('collection_name', 'collection')
    filename = f"golden_set_draft_{collection}.json"
    return app.response_class(
        response=json.dumps(result.get('golden_set_draft', []), ensure_ascii=False, indent=2),
        status=200,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _run_entity_study_request():
    """Executa o estudo de entidades a partir do JSON da requisição."""
    data = request.get_json() or {}
    collection_name = (data.get('collection_name') or '').strip()
    if not collection_name:
        return None, (jsonify({
            'success': False,
            'error': 'collection_name é obrigatório',
        }), 400)

    max_chunks = int(data.get('max_chunks', config.ENTITY_STUDY_MAX_CHUNKS or DEFAULT_MAX_CHUNKS))
    top_n = int(data.get('top_n', DEFAULT_TOP_N))
    neighbor_top = clamp_neighbor_top(data.get('neighbor_top', CONTEXT_NEIGHBORS))
    max_chunks = max(1, min(max_chunks, DEFAULT_MAX_CHUNKS))
    top_n = max(1, min(top_n, 200))

    emit_entity_study_progress('reading', 15, f'Lendo chunks de {collection_name}...')
    result = run_entity_study(
        vector_store,
        collection_name,
        max_chunks=max_chunks,
        top_n=top_n,
        neighbor_top=neighbor_top,
    )
    emit_entity_study_progress(
        'completed',
        100,
        f'{result["chunks_analyzed"]} chunks analisados; '
        f'{len(result["golden_set_draft"])} candidatos ao golden set.',
    )
    return result, None


@app.route('/api/entity-study', methods=['POST'])
def entity_study():
    """Extrai entidades (TF-IDF + NER) e gera rascunho de golden set."""
    try:
        result, error_response = _run_entity_study_request()
        if error_response:
            return error_response
        download = (request.get_json() or {}).get('format') in ('json', 'download')
        if download:
            return _golden_set_download(result)
        return jsonify({'success': True, **result})
    except NotImplementedError as e:
        return jsonify({'success': False, 'error': str(e)}), 501
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"❌ Erro em /api/entity-study: {e}")
        emit_entity_study_progress('error', 0, str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entity-study/export', methods=['POST'])
def entity_study_export():
    """Baixa o rascunho do golden set em JSON."""
    try:
        result, error_response = _run_entity_study_request()
        if error_response:
            return error_response
        return _golden_set_download(result)
    except NotImplementedError as e:
        return jsonify({'success': False, 'error': str(e)}), 501
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"❌ Erro em /api/entity-study/export: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/gliner-bert/status', methods=['GET'])
def gliner_bert_status():
    """Indica se o container Torch GLiNER/BERTimbau está utilizável."""
    payload = gliner_health()
    available = bool(payload.get("available"))
    train_available = bool(payload.get("train_available", available))
    return jsonify({
        "success": True,
        "available": available,
        "train_available": train_available,
        **payload,
    }), 200


@app.route('/api/gliner-study', methods=['POST'])
def gliner_study():
    """Estudo TF-IDF + NER remoto (GLiNER/BERTimbau)."""
    try:
        if not config.GLINER_BERT:
            return jsonify({
                "success": False,
                "available": False,
                "error": "GLINER_BERT=false. Ative a flag no .env e suba o profile gliner.",
            }), 503
        data = request.get_json() or {}
        collection_name = (data.get("collection_name") or "").strip()
        if not collection_name:
            return jsonify({"success": False, "error": "collection_name é obrigatório"}), 400
        max_chunks = int(data.get("max_chunks", config.GLINER_STUDY_MAX_CHUNKS))
        top_n = int(data.get("top_n", DEFAULT_TOP_N))
        neighbor_top = clamp_neighbor_top(data.get("neighbor_top", CONTEXT_NEIGHBORS))
        max_chunks = max(1, min(max_chunks, DEFAULT_MAX_CHUNKS))
        top_n = max(1, min(top_n, 200))
        emit_entity_study_progress("reading", 15, f"Lendo chunks de {collection_name}...")
        emit_entity_study_progress("ner", 40, "Enviando textos ao serviço GLiNER/BERTimbau...")
        result = run_gliner_entity_study(
            vector_store,
            collection_name,
            max_chunks=max_chunks,
            top_n=top_n,
            neighbor_top=neighbor_top,
            labels=config.GLINER_LABELS,
        )
        emit_entity_study_progress(
            "completed",
            100,
            f'{result["chunks_analyzed"]} chunks; '
            f'{len(result["golden_set_draft"])} candidatos (GLiNER/BERTimbau).',
        )
        download = data.get("format") in ("json", "download")
        if download:
            return _golden_set_download(result)
        return jsonify({"success": True, **result})
    except GlinerBertUnavailable as error:
        emit_entity_study_progress("error", 0, str(error))
        return jsonify({"success": False, "available": False, "error": str(error)}), 503
    except Exception as error:
        print(f"❌ Erro em /api/gliner-study: {error}")
        emit_entity_study_progress("error", 0, str(error))
        return jsonify({"success": False, "error": str(error)}), 500


@app.route('/api/gliner-train', methods=['POST'])
def gliner_train():
    """Encaminha JSON BIO ao serviço Torch para treino assíncrono."""
    try:
        if not config.GLINER_BERT:
            return jsonify({
                "success": False,
                "cuda_available": False,
                "error": "GLINER_BERT=false. Ative a flag no .env e suba o profile gliner.",
            }), 503
        if request.files.get("file"):
            raw = request.files["file"].read()
            if len(raw) > config.MAX_CONTENT_LENGTH:
                return jsonify({"success": False, "error": "Arquivo JSON grande demais."}), 413
            payload = json.loads(raw.decode("utf-8"))
            extra_steps = request.form.get("max_steps")
            extra_name = request.form.get("output_name")
            if not isinstance(payload, dict):
                payload = {"sentences": payload}
            if extra_steps:
                payload["max_steps"] = int(extra_steps)
            if extra_name:
                payload["output_name"] = extra_name
        else:
            payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"success": False, "error": "Envie JSON BIO no body ou um arquivo .json"}), 400
        result = gliner_start_train(payload)
        return jsonify({"success": True, **result})
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "JSON BIO inválido"}), 400
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except GlinerBertUnavailable as error:
        code = getattr(error, "status_code", 503) or 503
        return jsonify({"success": False, "error": str(error)}), code
    except Exception as error:
        print(f"❌ Erro em /api/gliner-train: {error}")
        return jsonify({"success": False, "error": str(error)}), 500


@app.route('/api/gliner-train/status', methods=['GET'])
def gliner_train_status_route():
    """Proxy de GET /train/status."""
    if not config.GLINER_BERT:
        return jsonify({
            "success": True,
            "state": "idle",
            "cuda_available": False,
            "message": "GLINER_BERT=false",
        }), 503
    payload = gliner_train_status()
    return jsonify({"success": True, **payload})


@app.route('/api/gliner-models', methods=['GET'])
def gliner_models_route():
    """Lista o Hub e os checkpoints em volumes/gliner-checkpoints."""
    if not config.GLINER_BERT:
        return jsonify({
            "success": True,
            "available": False,
            "current_id": "hub",
            "checkpoints": [],
            "error": "GLINER_BERT=false. Ative a flag no .env e suba o profile gliner.",
        }), 200
    try:
        payload = gliner_list_models()
        return jsonify({"success": True, **payload})
    except GlinerBertUnavailable as error:
        return jsonify({
            "success": False,
            "available": False,
            "current_id": "hub",
            "checkpoints": [],
            "error": str(error),
        }), 503


@app.route('/api/gliner-reload', methods=['POST'])
def gliner_reload_route():
    """Carrega um checkpoint em disco (ou volta ao Hub) sem reiniciar o container."""
    try:
        if not config.GLINER_BERT:
            return jsonify({
                "success": False,
                "error": "GLINER_BERT=false. Ative a flag no .env e suba o profile gliner.",
            }), 503
        data = request.get_json(silent=True) or {}
        model_id = (data.get("id") or data.get("checkpoint") or "hub").strip() or "hub"
        trained_only = data.get("trained_only")
        result = gliner_reload_model(model_id, trained_only=trained_only)
        return jsonify({"success": True, **result})
    except GlinerBertUnavailable as error:
        code = getattr(error, "status_code", 503) or 503
        return jsonify({"success": False, "error": str(error)}), code
    except Exception as error:
        print(f"❌ Erro em /api/gliner-reload: {error}")
        return jsonify({"success": False, "error": str(error)}), 500


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo é permitido."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')

@app.route('/api/test')
def test():
    """Endpoint de teste."""
    print("=== TESTE ENDPOINT ===", file=sys.stderr)
    return jsonify({'message': 'Teste OK'})


@app.route('/api/n8n/status', methods=['GET'])
def n8n_status():
    """Endpoint para verificar o status do N8N."""
    try:
        n8n_webhook_url = os.getenv('N8N_WEBHOOK_URL')
        if not n8n_webhook_url:
            return jsonify({
                'status': 'error',
                'message': 'N8N_WEBHOOK_URL não configurada no .env'
            }), 500
        
        import requests
        
        # Extrair URL base do N8N removendo sufixos de webhook
        if '/webhook-test/' in n8n_webhook_url:
            n8n_base_url = n8n_webhook_url.split('/webhook-test/')[0]
        elif '/webhook/' in n8n_webhook_url:
            n8n_base_url = n8n_webhook_url.split('/webhook/')[0]
        else:
            # Fallback: protocolo + host + porta
            parts = n8n_webhook_url.split('/')
            n8n_base_url = f"{parts[0]}//{parts[2]}"
        
        # Verificar conectividade básica
        try:
            health_check = requests.get(f"{n8n_base_url}/healthz", timeout=5)
            n8n_accessible = health_check.status_code == 200
        except requests.exceptions.RequestException:
            n8n_accessible = False
        
        # Verificar webhook específico
        webhook_status = 'unknown'
        webhook_details = None
        
        if n8n_accessible:
            try:
                webhook_response = requests.get(n8n_webhook_url, timeout=5)
                if webhook_response.status_code == 404:
                    webhook_status = 'not_registered'
                    try:
                        webhook_details = webhook_response.json()
                    except:
                        webhook_details = webhook_response.text
                elif webhook_response.status_code == 200:
                    webhook_status = 'active'
                else:
                    webhook_status = f'error_{webhook_response.status_code}'
                    webhook_details = webhook_response.text
            except requests.exceptions.RequestException as e:
                webhook_status = 'connection_error'
                webhook_details = str(e)
        
        return jsonify({
            'status': 'ok',
            'n8n_accessible': n8n_accessible,
            'n8n_base_url': n8n_base_url,
            'webhook_url': n8n_webhook_url,
            'webhook_status': webhook_status,
            'webhook_details': webhook_details,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/storage-info')
def storage_info():
    """Endpoint para informações do storage e documentos disponíveis."""
    print("=== TESTE STORAGE ENDPOINT ===", file=sys.stderr)
    try:
        storage_type = 'MinIO' if storage_manager.use_minio else 'Local'
        print(f"🗄️ Usando storage: {storage_type}", file=sys.stderr)
        
        # Listar documentos usando o método unificado
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents)}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'storage_type': storage_type,
            'storage_class': type(storage_manager.storage).__name__,
            'documents_count': len(documents),
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no storage: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['GET'])
def list_collections():
    """Lista collections disponíveis."""
    try:
        collections = vector_store.list_collections()
        
        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['POST'])
def create_collection():
    """Cria uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        collection_name = data.get('name')
        embedding_model = data.get('embedding_model')
        description = data.get('description', '')
        
        if not collection_name or not embedding_model:
            return jsonify({'error': 'Nome da collection e modelo de embedding são obrigatórios'}), 400
        
        # Criar collection
        created_name = vector_store.create_collection(
            collection_name=collection_name,
            embedding_model=embedding_model,
            description=description
        )
        
        return jsonify({
            'success': True,
            'message': f'Collection "{created_name}" criada com sucesso',
            'collection_name': created_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name: str):
    """Deleta uma collection."""
    try:
        success = vector_store.delete_collection(collection_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" deletada com sucesso'
            })
        else:
            return jsonify({'error': f'Collection "{collection_name}" não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/embedding-models', methods=['GET'])
def list_embedding_models():
    """Lista modelos de embedding disponíveis."""
    try:
        models = []
        for key, model_config in config.EMBEDDING_MODELS.items():
            models.append({
                'id': key,
                'name': model_config['name'],
                'model': model_config['model'],
                'dimension': model_config['dimension'],
                'provider': model_config['provider']
            })
        
        return jsonify({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/compatibility', methods=['GET'])
def check_collection_compatibility(collection_name: str):
    """Verifica compatibilidade de dimensões entre collection e modelos."""
    try:
        results = {}
        
        # Verificar compatibilidade com todos os modelos
        for model_key in config.EMBEDDING_MODELS.keys():
            compatibility = vector_store._check_dimension_compatibility(collection_name, model_key)
            results[model_key] = compatibility
        
        # Determinar status geral
        any_compatible = any(result["compatible"] for result in results.values())
        
        return jsonify({
            'success': True,
            'collection_name': collection_name,
            'compatible_models': results,
            'any_compatible': any_compatible,
            'recommendation': (
                "Collection compatível com pelo menos um modelo" if any_compatible else 
                "Collection precisa ser recriada - nenhum modelo compatível"
            )
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/update-dimensions', methods=['POST'])
def update_collection_dimensions(collection_name: str):
    """Força atualização das dimensões de uma collection para as atuais do config."""
    try:
        result = vector_store.update_collection_dimensions(collection_name)
        
        if result["success"]:
            return jsonify({
                'success': True,
                'message': f'Dimensões da collection "{collection_name}" atualizadas com sucesso',
                'details': result
            })
        else:
            return jsonify({'error': result.get("error", "Erro desconhecido")}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/migrate-all-dimensions', methods=['POST'])
def migrate_all_collection_dimensions():
    """Migra todas as collections para usar as dimensões atuais do config."""
    try:
        collections = vector_store.list_collections()
        results = []
        
        for collection in collections:
            if collection.get("exists_in_qdrant"):
                collection_name = collection["name"]
                result = vector_store.update_collection_dimensions(collection_name)
                results.append({
                    "collection": collection_name,
                    "result": result
                })
        
        success_count = sum(1 for r in results if r["result"].get("success"))
        total_count = len(results)
        
        return jsonify({
            'success': True,
            'message': f'Migração concluída: {success_count}/{total_count} collections atualizadas',
            'results': results,
            'summary': {
                'total': total_count,
                'success': success_count,
                'failed': total_count - success_count
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/charset-test', methods=['POST'])
def test_charset():
    """Endpoint para testar e diagnosticar problemas de charset."""
    try:
        data = request.get_json()
        test_text = data.get('text', '')
        
        if not test_text:
            return jsonify({'error': 'Texto de teste é obrigatório'}), 400
        
        # Diagnóstico detalhado
        diagnosis = {
            'original_length': len(test_text),
            'original_encoding_test': None,
            'sanitized_text': None,
            'sanitized_length': 0,
            'encoding_issues': [],
            'character_analysis': {}
        }
        
        # Testar encoding original
        try:
            test_text.encode('utf-8')
            diagnosis['original_encoding_test'] = 'UTF-8 válido'
        except UnicodeEncodeError as e:
            diagnosis['original_encoding_test'] = f'Erro UTF-8: {str(e)}'
            diagnosis['encoding_issues'].append(str(e))
        
        # Sanitizar e testar
        sanitized = sanitize_content(test_text)
        diagnosis['sanitized_text'] = sanitized
        diagnosis['sanitized_length'] = len(sanitized)
        
        # Análise de caracteres problemáticos
        problematic_chars = []
        for i, char in enumerate(test_text):
            try:
                char.encode('utf-8')
            except UnicodeEncodeError:
                problematic_chars.append({
                    'position': i,
                    'character': repr(char),
                    'unicode_category': unicodedata.category(char) if char else 'None'
                })
        
        diagnosis['character_analysis'] = {
            'total_problematic': len(problematic_chars),
            'problematic_chars': problematic_chars[:10]  # Primeiros 10
        }
        
        return jsonify({
            'success': True,
            'diagnosis': diagnosis,
            'recommendation': (
                'Texto já está válido' if len(problematic_chars) == 0 else 
                'Texto possui caracteres problemáticos que foram sanitizados'
            )
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/status', methods=['GET'])
def storage_status():
    """Verifica o status do sistema de armazenamento."""
    try:
        storage_type = "MinIO" if storage_manager.use_minio else "Local"
        storage_class = type(storage_manager.storage).__name__
        
        # Testar conectividade básica
        try:
            # Tentar listar documentos para testar se está funcionando
            files = storage_manager.get_document_list()
            connected = True
            error = None
        except Exception as e:
            connected = False
            error = str(e)
        
        return jsonify({
            'storage_type': storage_type,
            'storage_class': storage_class,
            'connected': connected,
            'error': error,
            'status': 'connected' if connected else 'disconnected'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files', methods=['GET'])
def list_storage_files():
    """Lista arquivos armazenados."""
    try:
        collection_name = request.args.get('collection')
        prefix = request.args.get('prefix', '')
        
        files = storage_manager.get_document_list(topic=collection_name)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_files': len(files),
            'collection': collection_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files/<path:object_name>', methods=['DELETE'])
def delete_storage_file(object_name):
    """Deleta um arquivo do storage."""
    try:
        storage_manager.delete_document(object_name)
        return jsonify({
            'success': True,
            'message': f'Arquivo "{object_name}" deletado com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def emit_progress(step: str, progress: int, message: str):
    """Emite progresso via SocketIO - SIMPLES."""
    try:
        socketio.emit('upload_progress', {
            'step': step,
            'progress': progress,
            'message': message
        })
        print(f"📡 {step} - {progress}% - {message}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Erro emit: {e}", file=sys.stderr)

def emit_qa_progress(step: str, progress: int, message: str):
    """Emite progresso de Q&A via SocketIO."""
    try:
        socketio.emit('qa_progress', {
            'step': step,
            'progress': progress,
            'message': message
        })
        print(f"📊 Q&A {step} - {progress}% - {message}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Erro emit Q&A: {e}", file=sys.stderr)

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload e processamento de documentos com DEBUG ROBUSTO."""
    print("=== INÍCIO DO UPLOAD ===", file=sys.stderr)
    charset_debugger.log_debug("APP_UPLOAD_START", "Iniciando processo de upload com debug robusto")
    
    try:
        emit_progress('validation', 5, 'Validando arquivo enviado...')
        charset_debugger.log_debug("APP_UPLOAD_VALIDATION", "Iniciando validação do arquivo")
        
        # Validações básicas
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        collection_name = request.form.get('collection_name')
        
        if not file.filename or not collection_name:
            return jsonify({'error': 'Arquivo ou collection não fornecidos'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        emit_progress('saving', 10, f'Salvando arquivo {file.filename}...')
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        emit_progress('saved', 20, 'Arquivo salvo com sucesso')
        
        # Upload para storage
        emit_progress('uploading', 30, 'Enviando arquivo para armazenamento...')
        try:
            upload_result = storage_manager.upload_document(file_path, topic=collection_name)
            emit_progress('uploaded', 40, 'Arquivo armazenado com sucesso')
        except Exception as e:
            os.remove(file_path)
            return jsonify({'error': f'Erro no upload: {str(e)}'}), 500
        
        # Processar documento
        emit_progress('processing', 50, 'Processando documento...')
        try:
            result = document_processor.process_document(file_path)
            emit_progress('processed', 70, 'Documento processado com sucesso')
        except Exception as e:
            os.remove(file_path)
            return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500
        
        # ESTRATÉGIA ZERO-CHARSET: Adicionar minio_path aos chunks
        emit_progress('preparing', 75, 'Preparando metadados para armazenamento...')
        for chunk in result['chunks']:
            chunk.metadata['minio_path'] = upload_result['original_path']
            chunk.metadata['minio_object'] = upload_result['object_name']
        
        # Inserir no banco de vetores COM DEBUG ROBUSTO
        emit_progress('vectorizing', 80, 'Gerando embeddings e inserindo no banco de vetores...')
        charset_debugger.log_debug("APP_VECTORIZING_START", f"Iniciando vetorização de {len(result['chunks'])} chunks")
        
        try:
            # Debug dos chunks antes da inserção
            for i, chunk in enumerate(result['chunks']):
                safety_check = charset_debugger.check_text_safety(chunk.page_content, f"app_chunk_{i+1}")
                charset_debugger.log_debug("APP_CHUNK_SAFETY", f"Chunk {i+1} verificação", safety_check)
                
                # Debug dos metadados
                for key, value in chunk.metadata.items():
                    metadata_safety = charset_debugger.check_text_safety(str(value), f"app_metadata_{key}_{i+1}")
                    charset_debugger.log_debug("APP_METADATA_SAFETY", f"Metadata {key} do chunk {i+1}", metadata_safety)
            
            charset_debugger.log_debug("APP_VECTOR_STORE_CALL", f"Chamando vector_store.insert_documents para collection: {collection_name}")
            success = vector_store.insert_documents(
                collection_name=collection_name,
                documents=result['chunks']
            )
            charset_debugger.log_debug("APP_VECTOR_STORE_SUCCESS", "vector_store.insert_documents concluído com sucesso")
            emit_progress('vectorized', 95, 'Embeddings e metadados completos armazenados com sucesso!')
            
        except Exception as e:
            charset_debugger.log_debug("APP_VECTOR_STORE_ERROR", f"ERRO CRÍTICO no app.py: {e}")
            
            # Stack trace completo
            import traceback
            stack_trace = traceback.format_exc()
            charset_debugger.log_debug("APP_VECTOR_STORE_STACK", f"Stack trace completo do app.py:\n{stack_trace}")
            
            # Relatório completo de debug
            charset_debugger.print_debug_report()
            
            os.remove(file_path)
            return jsonify({'error': f'Erro na vetorização ZERO-CHARSET: {str(e)}'}), 500
        
        # Limpar arquivo temporário
        try:
            os.remove(file_path)
        except:
            pass
        
        emit_progress('completed', 100, f'Documento {filename} processado com sucesso! {len(result["chunks"])} chunks criados.')
        
        return jsonify({
            'success': True,
            'message': 'Documento processado com sucesso',
            'filename': filename,
            'file_name': filename,  # Adicionar campo esperado pelo front-end
            'collection_name': collection_name,  # Adicionar campo esperado pelo front-end
            'chunks_count': len(result['chunks']),
            'collection': collection_name
        })
    
    except Exception as e:
        # Limpar arquivo temporário em caso de erro
        try:
            if 'file_path' in locals():
                os.remove(file_path)
        except:
            pass
        
        print(f"❌ Erro durante upload: {e}", file=sys.stderr)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500





@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para chat com RAG com suporte a múltiplas collections e threshold de similaridade."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        message = data.get('message')
        collection_names = data.get('collection_names')  # Pode ser string, lista ou None
        collection_name = data.get('collection_name')  # Compatibilidade com versão anterior
        session_id = data.get('session_id')
        similarity_threshold = data.get('similarity_threshold', 0.0)  # Threshold de similaridade (0.0 a 1.0)
        
        if not message:
            return jsonify({'error': 'Mensagem é obrigatória'}), 400
        
        # Validar threshold de similaridade
        if not isinstance(similarity_threshold, (int, float)) or similarity_threshold < 0.0 or similarity_threshold > 1.0:
            similarity_threshold = 0.0
        
        # Para busca por similaridade, criar sessão temporária se não fornecida
        if not session_id:
            session_id = chat_manager.create_session("Busca por Similaridade")
        
        # Suporte a compatibilidade: se collection_name foi fornecido mas collection_names não
        if collection_name and not collection_names:
            collection_names = collection_name
        
        # Processar mensagem usando o ChatManager
        result = chat_manager.chat(
            session_id=session_id,
            message=message,
            collection_names=collection_names,
            similarity_threshold=similarity_threshold
        )
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'sources': result['sources'],
            'session_id': result['session_id'],
            'collections_used': result.get('collections_used', []),
            'processed_by': result.get('processed_by', 'unknown'),
            'similarity_threshold': similarity_threshold
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """Lista sessões de chat."""
    try:
        sessions = chat_manager.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        print(f"❌ Erro na rota /api/sessions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Cria uma nova sessão de chat."""
    try:
        print(f"🔍 Criando sessão...", file=sys.stderr)
        data = request.get_json() or {}
        session_name = data.get('name', 'Nova Sessão')
        print(f"📝 Nome da sessão: {session_name}", file=sys.stderr)
        
        session_id = chat_manager.create_session(session_name)
        print(f"✅ Sessão criada com ID: {session_id}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name
        })
    except Exception as e:
        print(f"❌ Erro ao criar sessão: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Deleta uma sessão de chat."""
    try:
        success = chat_manager.delete_session(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Sessão deletada com sucesso'
            })
        else:
            return jsonify({'error': 'Sessão não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Obtém uma sessão específica com suas mensagens."""
    try:
        session = chat_manager.get_session(session_id)
        
        if session:
            return jsonify({
                'success': True,
                'session': session
            })
        else:
            return jsonify({'error': 'Sessão não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id: str):
    """Obtém as mensagens de uma sessão específica."""
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = chat_manager.get_session_messages(session_id, limit)
        
        return jsonify({
            'success': True,
            'messages': messages,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>/name', methods=['PUT'])
def update_session_name(session_id: str):
    """Atualiza o nome de uma sessão."""
    try:
        data = request.get_json()
        name = data.get('name', 'Nova Sessão')
        
        success = chat_manager.session_service.update_session_name(session_id, name)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Nome da sessão atualizado com sucesso'
            })
        else:
            return jsonify({'error': 'Sessão não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """Lista documentos disponíveis no MinIO."""
    print("=== ENDPOINT /api/documents CHAMADO ===", file=sys.stderr)
    try:
        print("🔍 Chamando storage_manager.get_document_list()", file=sys.stderr)
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents) if documents else 0}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no endpoint /api/documents: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/documents', methods=['GET'])
def list_collection_documents(collection_name: str):
    """Lista documentos originais de uma collection."""
    try:
        print(f"🔍 Listando documentos originais da collection: {collection_name}", file=sys.stderr)
        limit = request.args.get('limit', 1000, type=int)
        
        documents = vector_store.list_collection_documents(
            collection_name=collection_name,
            limit=limit
        )
        
        print(f"📄 Encontrados {len(documents)} documentos originais", file=sys.stderr)
        for i, doc in enumerate(documents[:3]):  # Log dos primeiros 3 para debug
            print(f"   Doc {i+1}: {doc.get('name', 'Sem nome')} - {doc.get('file_type', 'tipo desconhecido')}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total': len(documents),
            'collection_name': collection_name
        })
        
    except Exception as e:
        print(f"❌ Erro ao listar documentos da collection {collection_name}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/recalculate-count', methods=['POST'])
def recalculate_collection_count(collection_name: str):
    """Recalcula a contagem de documentos de uma collection."""
    try:
        vector_store._recalculate_collection_document_count(collection_name)
        return jsonify({
            'success': True,
            'message': f'Contagem de documentos da collection "{collection_name}" recalculada'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<document_name>/content', methods=['GET'])
def get_document_content(document_name: str):
    """Obtém o conteúdo de um documento específico."""
    try:
        # Decodificar o nome do documento se necessário
        import urllib.parse
        document_name = urllib.parse.unquote(document_name)
        
        # Buscar o documento no MinIO
        try:
            content_bytes = storage_manager.storage.download_file(document_name)
            content = content_bytes.decode('utf-8')
        except Exception as e:
            return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        
        return jsonify({
            'success': True,
            'content': content,
            'document_name': document_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/content', methods=['GET'])
def get_collection_content(collection_name: str):
    """Obtém o conteúdo de todos os documentos de uma collection para geração de Q&A."""
    try:
        # Verificar se é uma requisição para documento específico
        document_name = request.args.get('document')
        
        if document_name:
            # Buscar documento específico no storage
            try:
                # Primeiro, tentar encontrar o documento na collection para obter o caminho processado
                documents = vector_store.list_collection_documents(collection_name)
                
                # DEBUG: Mostrar todos os documentos disponíveis
                print(f"🔍 DEBUG [CONTENT_SEARCH] Procurando documento: '{document_name}'", file=sys.stderr)
                print(f"🔍 DEBUG [CONTENT_AVAILABLE] Documentos disponíveis na collection '{collection_name}':", file=sys.stderr)
                for i, doc in enumerate(documents):
                    print(f"  📄 {i+1}. name='{doc.get('name')}', file_name='{doc.get('file_name')}', minio_path='{doc.get('minio_path')}'", file=sys.stderr)
                
                # Encontrar o documento específico por nome original
                target_doc = None
                for doc in documents:
                    # Comparar pelos campos disponíveis
                    doc_name = doc.get('name', '')
                    doc_file_name = doc.get('file_name', '')
                    doc_minio_path = doc.get('minio_path', '')
                    
                    print(f"🔍 DEBUG [CONTENT_COMPARE] Comparando '{document_name}' com:", file=sys.stderr)
                    print(f"  - name: '{doc_name}'", file=sys.stderr)
                    print(f"  - file_name: '{doc_file_name}'", file=sys.stderr)
                    print(f"  - minio_path: '{doc_minio_path}'", file=sys.stderr)
                    
                    # Tentar várias formas de match
                    matches = [
                        doc_name == document_name,
                        doc_file_name == document_name,
                        doc_minio_path == document_name,
                        document_name in doc_minio_path,  # Match parcial
                        doc_name in document_name,        # Nome contém o documento
                        document_name.endswith(doc_name), # Document name termina com o nome do doc
                    ]
                    
                    print(f"  - Matches: {matches}", file=sys.stderr)
                    
                    if any(matches):
                        target_doc = doc
                        print(f"✅ DEBUG [CONTENT_FOUND] Documento encontrado via: {['name==', 'file_name==', 'minio_path==', 'in_minio_path', 'name_in', 'ends_with_name'][matches.index(True)]}", file=sys.stderr)
                        break
                
                if not target_doc:
                    return jsonify({'error': f'Documento {document_name} não encontrado na collection {collection_name}'}), 404
                
                # Usar os chunks do documento que já temos disponíveis
                chunks = target_doc.get('chunks', [])
                if not chunks:
                    print(f"❌ DEBUG [CONTENT_ERROR] Documento encontrado mas sem chunks disponíveis", file=sys.stderr)
                    return jsonify({'error': f'Documento {document_name} não possui chunks disponíveis para geração de Q&A'}), 404
                
                print(f"✅ DEBUG [CONTENT_CHUNKS] Documento tem {len(chunks)} chunks disponíveis", file=sys.stderr)
                
                # Concatenar todos os chunks para formar o conteúdo completo
                content_parts = []
                for chunk in sorted(chunks, key=lambda x: x.get('chunk_index', 0)):
                    chunk_content = chunk.get('content', '')
                    if chunk_content and chunk_content.strip():
                        content_parts.append(chunk_content.strip())
                        print(f"📄 DEBUG [CONTENT_CHUNK] Chunk {chunk.get('chunk_index', '?')}: {len(chunk_content)} chars", file=sys.stderr)
                
                content = '\n\n'.join(content_parts)
                print(f"✅ DEBUG [CONTENT_ASSEMBLED] Conteúdo montado: {len(content)} caracteres totais", file=sys.stderr)
                
                print(f"✅ Conteúdo obtido com sucesso. Tamanho: {len(content)} caracteres", file=sys.stderr)
                
                return jsonify({
                    'success': True,
                    'content': content,
                    'document_name': target_doc.get('name', document_name),
                    'chunks_count': len(chunks),
                    'source': 'chunks_from_qdrant',
                    'document_count': 1
                })
            except Exception as e:
                print(f"❌ Erro ao buscar documento: {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        else:
            # Comportamento original - conteúdo da collection
            documents = vector_store.list_collection_documents(collection_name)
            
            # Concatenar conteúdo de todos os documentos
            content = ""
            for doc in documents:
                if doc.get('content'):
                    content += doc['content'] + "\n\n"
            
            return jsonify({
                'success': True,
                'content': content,
                'document_count': len(documents)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/qa-generate', methods=['POST'])
def generate_qa():
    """Gera perguntas e respostas a partir de um documento (apenas geração, sem vetorização)."""
    try:
        data = request.get_json()
        print(f"🔍 Dados recebidos no qa-generate: {data is not None}", file=sys.stderr)
        
        if not data:
            print("❌ Nenhum dado JSON fornecido", file=sys.stderr)
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        content = data.get('content')
        num_questions = data.get('num_questions', 10)
        difficulty = data.get('difficulty', 'Intermediário')
        temperature = data.get('temperature', 0.5)
        context_keywords = data.get('context_keywords', '')
        custom_prompt = data.get('custom_prompt', '')
        
        print(f"📄 Tamanho do conteúdo: {len(content) if content else 0}", file=sys.stderr)
        
        # Debug individual das variáveis
        try:
            print(f"🔢 num_questions: {num_questions} (tipo: {type(num_questions)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com num_questions: {e}", file=sys.stderr)
            
        try:
            print(f"🎚️ difficulty: '{difficulty}' (tipo: {type(difficulty)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com difficulty: {e}", file=sys.stderr)
            
        try:
            print(f"🌡️ temperature: {temperature} (tipo: {type(temperature)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com temperature: {e}", file=sys.stderr)
            
        try:
            print(f"🔤 Context keywords: '{context_keywords}' (tipo: {type(context_keywords)})", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com context_keywords: {e}", file=sys.stderr)
            
        try:
            print(f"📝 Custom prompt length: {len(custom_prompt) if custom_prompt else 0}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro com custom_prompt: {e}", file=sys.stderr)
        
        if not content:
            print("❌ Conteúdo vazio ou não fornecido", file=sys.stderr)
            return jsonify({'error': 'Conteúdo é obrigatório'}), 400
        
        # Sanitizar conteúdo antes do processamento
        content = sanitize_content(content)
        print(f"🧼 Conteúdo sanitizado para processamento Q&A", file=sys.stderr)
        
        if not content.strip():
            print("❌ Conteúdo contém apenas espaços em branco após sanitização", file=sys.stderr)
            return jsonify({'error': 'Conteúdo não pode estar vazio'}), 400
        
        print(f"✅ Validações passadas. qa_generator: {type(qa_generator)}", file=sys.stderr)
        
        # Processar custom prompt substituindo placeholders
        if custom_prompt:
            processed_prompt = custom_prompt.format(
                num_questions=num_questions,
                context_keywords=context_keywords,
                difficulty=difficulty,
                document_text=content
            )
            print(f"🔧 Prompt processado (primeiros 100 chars): {repr(processed_prompt[:100])}", file=sys.stderr)
        else:
            processed_prompt = custom_prompt
            print(f"🔧 Usando prompt padrão", file=sys.stderr)
        
        # Parâmetros para geração de Q&A
        params = {
            'num_questions': num_questions,
            'context_keywords': context_keywords,
            'difficulty': difficulty,
            'temperature': temperature,
            'custom_prompt': processed_prompt
        }
        
        # Gerar Q&A
        print(f"🚀 Iniciando geração de Q&A com {len(content)} caracteres...", file=sys.stderr)
        print(f"📋 Parâmetros completos: {params}", file=sys.stderr)
        
        emit_qa_progress('generating', 10, 'Iniciando geração de Q&As...')
        
        try:
            print("⚡ Prestes a chamar qa_generator.generate_qa_pairs()", file=sys.stderr)
            emit_qa_progress('generating', 30, 'Processando conteúdo com IA...')
            
            qa_content = qa_generator.generate_qa_pairs(content, params)
            
            emit_qa_progress('generating', 80, 'Formatando perguntas e respostas...')
            print(f"✅ Função generate_qa_pairs retornou!", file=sys.stderr)
            print(f"📊 Resultado da geração: {type(qa_content)}, length: {len(qa_content) if qa_content else 0}", file=sys.stderr)
            if qa_content:
                print(f"📄 Preview: {repr(qa_content[:100])}", file=sys.stderr)
        except Exception as gen_error:
            emit_qa_progress('error', 0, f'Erro na geração: {str(gen_error)}')
            print(f"❌ Erro durante geração: {str(gen_error)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Erro na geração de Q&A: {str(gen_error)}'}), 500
        
        if not qa_content:
            print("❌ Q&A generator retornou conteúdo vazio", file=sys.stderr)
            return jsonify({'error': 'Não foi possível gerar perguntas e respostas'}), 400
        
        if not qa_content.strip():
            print("❌ Q&A generator retornou apenas espaços em branco", file=sys.stderr)
            return jsonify({'error': 'Conteúdo Q&A gerado está vazio'}), 400
        
        # Converter para documentos (apenas para contar)
        emit_qa_progress('generating', 95, 'Finalizando geração...')
        documents = qa_generator.qa_to_documents(qa_content, "temp")
        
        emit_qa_progress('completed', 100, f'{len(documents)} pares de Q&A gerados com sucesso!')
        
        return jsonify({
            'success': True,
            'message': f'{len(documents)} pares de Q&A gerados com sucesso',
            'qa_content': qa_content,
            'qa_count': len(documents)
        })
            
    except Exception as e:
        print(f"❌ Erro ao gerar Q&A: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/qa-vectorize', methods=['POST'])
def vectorize_qa():
    """Vetoriza Q&As já gerados em uma collection específica."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        qa_content = data.get('qa_content')
        collection_name = data.get('collection_name')
        
        if not qa_content or not collection_name:
            return jsonify({'error': 'Conteúdo Q&A e collection são obrigatórios'}), 400
        
        emit_qa_progress('vectorizing', 10, 'Preparando documentos para vetorização...')
        
        # Converter para documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        emit_qa_progress('vectorizing', 30, f'Vetorizando {len(documents)} pares de Q&A...')
        
        # Inserir no banco de vetores
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        emit_qa_progress('vectorizing', 90, 'Finalizando inserção na collection...')
        
        if success:
            emit_qa_progress('completed', 100, f'{len(documents)} pares de Q&A vetorizados com sucesso!')
            return jsonify({
                'success': True,
                'message': f'{len(documents)} pares de Q&A inseridos com sucesso na collection {collection_name}',
                'qa_count': len(documents)
            })
        else:
            emit_qa_progress('error', 0, 'Erro ao inserir Q&A no banco de vetores')
            return jsonify({'error': 'Erro ao inserir Q&A no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/create-qa-embeddings', methods=['POST'])
def create_qa_embeddings():
    """Cria embeddings a partir dos Q&As gerados e insere em uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        qa_content = data.get('qa_content')
        collection_name = data.get('collection_name')
        embedding_model = data.get('embedding_model', config.DEFAULT_EMBEDDING_MODEL)
        
        if not qa_content or not collection_name:
            return jsonify({'error': 'Conteúdo Q&A e nome da collection são obrigatórios'}), 400
        
        # Converter Q&A em documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        if not documents:
            return jsonify({'error': 'Não foi possível processar os Q&As'}), 400
        
        # Inserir documentos na nova collection
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" criada com {len(documents)} Q&As como embeddings',
                'collection_name': collection_name,
                'documents_count': len(documents),
                'embedding_model': embedding_model
            })
        else:
            return jsonify({'error': 'Erro ao criar embeddings no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/semantic-search', methods=['POST'])
def semantic_search():
    """Endpoint para busca semântica que aciona o N8N."""
    try:
        from src.semantic_search_service import SemanticSearchService
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        question = data.get('question')
        session_id = data.get('session_id')
        collection_names = data.get('collection_names', [])
        collection_name = data.get('collection_name', '')  # Compatibilidade com versão anterior
        models = data.get('models', {})
        
        # Se não há collection_names mas há collection_name, usar como lista
        if not collection_names and collection_name:
            collection_names = [collection_name]
        
        if not question:
            return jsonify({'error': 'Pergunta é obrigatória'}), 400
        
        # Verificar se pelo menos um modelo foi selecionado
        openai_enabled = models.get('openai', False)
        gemini_enabled = models.get('gemini', False)
        
        if not openai_enabled and not gemini_enabled:
            return jsonify({'error': 'Pelo menos um modelo deve ser selecionado'}), 400
        
        # Usar o serviço de busca semântica
        semantic_service = SemanticSearchService()
        result = semantic_service.search_with_n8n(
            question=question,
            session_id=session_id,
            collection_names=collection_names,
            openai_enabled=openai_enabled,
            gemini_enabled=gemini_enabled
        )
        
        if result['success']:
            # Salvar a pergunta do usuário e as respostas no banco de dados
            try:
                from src.session_service import SessionService
                session_service = SessionService()
                
                # Salvar a pergunta do usuário
                if session_id:
                    session_service.add_message(session_id, 'user', question)
                    
                    # Salvar as respostas dos modelos
                    responses = result.get('responses', {})
                    for model_name, response_data in responses.items():
                        if response_data and isinstance(response_data, dict):
                            response_content = response_data.get('response', '')
                            if response_content:
                                # Criar conteúdo formatado para a resposta do modelo
                                formatted_response = f"**{model_name.upper()} Response:**\n{response_content}"
                                session_service.add_message(session_id, 'assistant', formatted_response, 
                                                          sources=response_data.get('sources', []))
                        elif response_data and isinstance(response_data, str):
                            # Caso a resposta seja apenas uma string
                            formatted_response = f"**{model_name.upper()} Response:**\n{response_data}"
                            session_service.add_message(session_id, 'assistant', formatted_response,
                                                        sources=result.get('sources', []))
                            
            except Exception as save_error:
                # Log do erro, mas não interrompe o fluxo
                print(f"⚠️ Erro ao salvar mensagens: {save_error}", file=sys.stderr)
            
            return jsonify(result)
        else:
            # Determinar o status code baseado no tipo de erro
            if 'não configurada' in result.get('error', ''):
                status_code = 500
            elif 'não está acessível' in result.get('error', '') or 'conexão' in result.get('error', ''):
                status_code = 503
            elif 'Timeout' in result.get('error', ''):
                status_code = 504
            elif 'Webhook' in result.get('error', ''):
                status_code = 503
            else:
                status_code = 500
            
            return jsonify(result), status_code
            
    except Exception as e:
        print(f"❌ Erro na busca semântica: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/collections-by-model', methods=['GET'])
def debug_collections_by_model():
    """Endpoint de debug para verificar collections por modelo."""
    try:
        from src.semantic_search_by_model_service import SemanticSearchByModelService
        
        service = SemanticSearchByModelService()
        all_collections = service.vector_store.list_collections()
        
        debug_info = {
            'total_collections': len(all_collections),
            'collections': [],
            'models_available': list(config.EMBEDDING_MODELS.keys())
        }
        
        for collection in all_collections:
            collection_debug = {
                'name': collection.get('name'),
                'exists_in_qdrant': collection.get('exists_in_qdrant'),
                'embedding_model': collection.get('embedding_model'),
                'model_config': collection.get('model_config', {}),
                'document_count': collection.get('document_count', 0),
                'created_at': collection.get('created_at')
            }
            debug_info['collections'].append(collection_debug)
        
        # Testar cada modelo
        debug_info['collections_by_model'] = {}
        for model_id in config.EMBEDDING_MODELS.keys():
            model_collections = service.get_collections_by_model(model_id)
            debug_info['collections_by_model'][model_id] = model_collections
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        print(f"❌ Erro no debug de collections: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/debug/fix-collections-status', methods=['POST'])
def fix_collections_status():
    """Corrige o status exists_in_qdrant das collections verificando diretamente no Qdrant."""
    try:
        from src.semantic_search_by_model_service import SemanticSearchByModelService
        
        service = SemanticSearchByModelService()
        all_collections = service.vector_store.list_collections()
        
        fixed_collections = []
        errors = []
        
        for collection in all_collections:
            collection_name = collection.get('name')
            current_status = collection.get('exists_in_qdrant', False)
            
            if collection_name:
                # Verificar status real no Qdrant
                real_status = service._check_collection_exists_in_qdrant(collection_name)
                
                if current_status != real_status:
                    try:
                        # Tentar atualizar o status no sistema
                        # Isso depende de como o vector_store salva os metadados
                        print(f"🔄 Corrigindo status de '{collection_name}': {current_status} → {real_status}")
                        fixed_collections.append({
                            'name': collection_name,
                            'old_status': current_status,
                            'new_status': real_status
                        })
                    except Exception as e:
                        errors.append({
                            'collection': collection_name,
                            'error': str(e)
                        })
        
        return jsonify({
            'success': True,
            'fixed_collections': fixed_collections,
            'errors': errors,
            'message': f'Verificadas {len(all_collections)} collections, {len(fixed_collections)} corrigidas'
        })
        
    except Exception as e:
        print(f"❌ Erro ao corrigir status das collections: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/semantic-search-by-model', methods=['POST'])
def semantic_search_by_model():
    """Busca semântica por modelo específico com retorno de chunks."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        query = data.get('query', '').strip()
        model_id = data.get('model', '').strip()
        top_k = data.get('top_k', 20)  # Aumentado para busca mais robusta
        similarity_threshold = data.get('similarity_threshold', 0.3)  # Threshold mais restritivo (30%)
        
        if not query:
            return jsonify({'success': False, 'error': 'Query não fornecida'}), 400
        
        if not model_id:
            return jsonify({'success': False, 'error': 'Modelo não especificado'}), 400
        
        # Verificar se o modelo existe
        if model_id not in config.EMBEDDING_MODELS:
            return jsonify({
                'success': False, 
                'error': f'Modelo {model_id} não encontrado'
            }), 400
        
        # Importar e usar o serviço
        from src.semantic_search_by_model_service import SemanticSearchByModelService
        
        search_service = SemanticSearchByModelService()
        result = search_service.search_and_generate_response(
            query=query,
            model_id=model_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Erro na busca semântica por modelo: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500


@app.route('/api/debug/gemini-models', methods=['GET'])
def debug_gemini_models():
    """Lista modelos Gemini disponíveis para debug."""
    try:
        import google.generativeai as genai
        
        if not config.GEMINI_API_KEY:
            return jsonify({
                'success': False,
                'error': 'GEMINI_API_KEY não configurada'
            })
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # Testar modelos conhecidos
        models_to_test = [
            "gemini-1.5-flash",
            "gemini-1.5-pro", 
            "gemini-pro-1.5",
            "gemini-1.0-pro",
            "gemini-pro"  # modelo antigo para verificar
        ]
        
        available_models = []
        unavailable_models = []
        
        for model_name in models_to_test:
            try:
                model = genai.GenerativeModel(model_name)
                # Fazer um teste simples
                response = model.generate_content("Teste", generation_config={"max_output_tokens": 10})
                if response and response.text:
                    available_models.append(model_name)
                else:
                    unavailable_models.append(f"{model_name} (resposta vazia)")
            except Exception as e:
                unavailable_models.append(f"{model_name} (erro: {str(e)[:100]})")
        
        return jsonify({
            'success': True,
            'available_models': available_models,
            'unavailable_models': unavailable_models,
            'current_config': config.GEMINI_MODEL,
            'api_key_configured': bool(config.GEMINI_API_KEY)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/debug/collections-count-comparison', methods=['GET'])
def debug_collections_count_comparison():
    """Compara as contagens entre collections view e busca semântica."""
    try:
        from src.semantic_search_by_model_service import SemanticSearchByModelService
        
        semantic_service = SemanticSearchByModelService()
        
        # Obter informações das collections
        all_collections = vector_store.list_collections()
        
        comparison = {
            'collections_view': {},
            'semantic_search': {},
            'differences': []
        }
        
        # Para cada modelo, verificar contagens
        for model_id in ['openai', 'gemini']:
            # Collections view - contagem do metadata
            model_collections = [c for c in all_collections 
                               if c.get('model_config', {}).get('provider') == model_id 
                               or c.get('embedding_model') == model_id]
            
            collections_view_total = sum(c.get('chunks_count', 0) for c in model_collections)
            collections_view_names = [c.get('name') for c in model_collections]
            
            # Semantic search - contagem real do Qdrant
            semantic_collections = semantic_service.get_collections_by_model(model_id)
            semantic_total = 0
            qdrant_counts = {}
            
            for collection_name in semantic_collections:
                try:
                    collection_info = vector_store.client.get_collection(collection_name)
                    count = collection_info.points_count
                    qdrant_counts[collection_name] = count
                    semantic_total += count
                except Exception as e:
                    qdrant_counts[collection_name] = f"erro: {str(e)}"
            
            comparison['collections_view'][model_id] = {
                'collections': collections_view_names,
                'total_chunks': collections_view_total,
                'source': 'metadata_cache'
            }
            
            comparison['semantic_search'][model_id] = {
                'collections': semantic_collections,
                'total_chunks': semantic_total,
                'qdrant_counts': qdrant_counts,
                'source': 'qdrant_real_time'
            }
            
            if collections_view_total != semantic_total:
                comparison['differences'].append({
                    'model': model_id,
                    'collections_view': collections_view_total,
                    'semantic_search': semantic_total,
                    'difference': abs(collections_view_total - semantic_total),
                    'issue': 'metadata vs real count mismatch'
                })
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'explanation': {
                'collections_view': 'Usa contagem do metadata cache (pode estar desatualizada)',
                'semantic_search': 'Usa contagem real do Qdrant (sempre atual)'
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=== ROTAS REGISTRADAS ===", file=sys.stderr)
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}", file=sys.stderr)
    print("=========================", file=sys.stderr)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) 