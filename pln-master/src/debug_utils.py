"""Sistema de debug robusto para detectar problemas de charset."""

import sys
import traceback
import json
import unicodedata
from typing import Any, Dict, List, Optional
from datetime import datetime


class CharsetDebugger:
    """Sistema completo de debug para problemas de charset."""
    
    def __init__(self):
        self.debug_log = []
        self.error_count = 0
        
    def log_debug(self, stage: str, message: str, data: Any = None):
        """Log detalhado de debug."""
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "stage": stage,
            "message": message,
            "data_type": type(data).__name__ if data is not None else None,
            "data_length": len(str(data)) if data is not None else 0
        }
        self.debug_log.append(entry)
        print(f"🔍 DEBUG [{stage}] {message}", file=sys.stderr)
        if data is not None and len(str(data)) < 100:
            print(f"    📊 Data: {repr(data)[:100]}", file=sys.stderr)
        sys.stderr.flush()
    
    def check_text_safety(self, text: Any, location: str) -> Dict[str, Any]:
        """Verificação completa de segurança do texto."""
        result = {
            "location": location,
            "is_safe": True,
            "issues": [],
            "text_info": {},
            "recommendations": []
        }
        
        try:
            # Verificar tipo
            if not isinstance(text, str):
                text = str(text)
                result["issues"].append(f"Converted from {type(text).__name__} to str")
            
            # Informações básicas do texto
            result["text_info"] = {
                "length": len(text),
                "first_10_chars": repr(text[:10]),
                "last_10_chars": repr(text[-10:]) if len(text) > 10 else "",
                "encoding_attempts": {}
            }
            
            # Teste UTF-8 strict
            try:
                text.encode('utf-8', 'strict')
                result["text_info"]["encoding_attempts"]["utf8_strict"] = "✅ PASS"
            except UnicodeEncodeError as e:
                result["is_safe"] = False
                result["issues"].append(f"UTF-8 strict failed: {e}")
                result["text_info"]["encoding_attempts"]["utf8_strict"] = f"❌ FAIL: {e}"
                
                # Analisar posição específica do erro
                if hasattr(e, 'start') and hasattr(e, 'end'):
                    problematic_chars = text[e.start:e.end]
                    result["issues"].append(f"Problematic chars at {e.start}-{e.end}: {repr(problematic_chars)}")
                    
                    # Analisar caracteres problemáticos
                    for i, char in enumerate(problematic_chars):
                        char_info = {
                            "char": repr(char),
                            "unicode_name": unicodedata.name(char, "UNKNOWN"),
                            "unicode_category": unicodedata.category(char),
                            "code_point": ord(char)
                        }
                        result["issues"].append(f"Char {i}: {char_info}")
            
            # Teste JSON serialization
            try:
                json.dumps(text)
                result["text_info"]["encoding_attempts"]["json_serializable"] = "✅ PASS"
            except Exception as e:
                result["is_safe"] = False
                result["issues"].append(f"JSON serialization failed: {e}")
                result["text_info"]["encoding_attempts"]["json_serializable"] = f"❌ FAIL: {e}"
            
            # Teste ASCII
            try:
                text.encode('ascii', 'strict')
                result["text_info"]["encoding_attempts"]["ascii_strict"] = "✅ PASS"
            except UnicodeEncodeError as e:
                result["text_info"]["encoding_attempts"]["ascii_strict"] = f"⚠️ FAIL: {e}"
                result["recommendations"].append("Consider ASCII fallback if other methods fail")
            
            # Verificar surrogates específicos
            if any(0xD800 <= ord(c) <= 0xDFFF for c in text):
                result["is_safe"] = False
                result["issues"].append("Contains UTF-16 surrogates")
                result["recommendations"].append("Remove or replace surrogate characters")
            
            # Verificar caracteres de controle
            control_chars = [c for c in text if unicodedata.category(c).startswith('C')]
            if control_chars:
                result["issues"].append(f"Contains {len(control_chars)} control characters")
                result["recommendations"].append("Remove control characters")
            
        except Exception as e:
            result["is_safe"] = False
            result["issues"].append(f"Unexpected error in safety check: {e}")
            result["text_info"]["error"] = str(e)
        
        return result
    
    def safe_text_operation(self, operation_name: str, text: Any, operation_func, fallback_func=None):
        """Executa operação com texto de forma segura, com debug completo."""
        self.log_debug(f"OPERATION_START", f"Starting {operation_name}")
        
        # Verificar segurança antes da operação
        safety_check = self.check_text_safety(text, f"before_{operation_name}")
        self.log_debug(f"SAFETY_CHECK", f"Safety check for {operation_name}", safety_check)
        
        if not safety_check["is_safe"]:
            self.error_count += 1
            self.log_debug(f"SAFETY_FAIL", f"Text is not safe for {operation_name}")
            
            if fallback_func:
                self.log_debug(f"FALLBACK", f"Using fallback for {operation_name}")
                try:
                    return fallback_func(text)
                except Exception as e:
                    self.log_debug(f"FALLBACK_FAIL", f"Fallback failed: {e}")
                    raise e
            else:
                raise ValueError(f"Text is not safe for {operation_name}: {safety_check['issues']}")
        
        # Executar operação principal
        try:
            self.log_debug(f"OPERATION_EXEC", f"Executing {operation_name}")
            result = operation_func(text)
            self.log_debug(f"OPERATION_SUCCESS", f"{operation_name} completed successfully")
            return result
        except Exception as e:
            self.error_count += 1
            self.log_debug(f"OPERATION_FAIL", f"{operation_name} failed: {e}")
            
            # Capturar stack trace completo
            stack_trace = traceback.format_exc()
            self.log_debug(f"STACK_TRACE", f"Full stack trace:\n{stack_trace}")
            
            # Se há fallback, tentar usar
            if fallback_func:
                self.log_debug(f"FALLBACK_RETRY", f"Retrying {operation_name} with fallback")
                try:
                    return fallback_func(text)
                except Exception as fallback_error:
                    self.log_debug(f"FALLBACK_FAIL", f"Fallback also failed: {fallback_error}")
                    raise fallback_error
            
            raise e
    
    def get_debug_report(self) -> Dict[str, Any]:
        """Gera relatório completo de debug."""
        return {
            "total_operations": len(self.debug_log),
            "total_errors": self.error_count,
            "error_rate": self.error_count / len(self.debug_log) if self.debug_log else 0,
            "debug_log": self.debug_log[-50:],  # Últimas 50 entradas
            "summary": {
                "stages": list(set(entry["stage"] for entry in self.debug_log)),
                "most_common_issues": []  # TODO: implementar análise
            }
        }
    
    def print_debug_report(self):
        """Imprime relatório de debug formatado."""
        report = self.get_debug_report()
        print("\n" + "="*60, file=sys.stderr)
        print("🔍 RELATÓRIO DE DEBUG CHARSET", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print(f"📊 Total de operações: {report['total_operations']}", file=sys.stderr)
        print(f"❌ Total de erros: {report['total_errors']}", file=sys.stderr)
        print(f"📈 Taxa de erro: {report['error_rate']:.2%}", file=sys.stderr)
        print(f"🎯 Estágios verificados: {', '.join(report['summary']['stages'])}", file=sys.stderr)
        print("="*60, file=sys.stderr)
        sys.stderr.flush()


# Instância global do debugger
charset_debugger = CharsetDebugger()


def debug_text_operation(operation_name: str, fallback_func=None):
    """Decorator para operações de texto com debug automático."""
    def decorator(func):
        def wrapper(text, *args, **kwargs):
            return charset_debugger.safe_text_operation(
                operation_name=operation_name,
                text=text,
                operation_func=lambda t: func(t, *args, **kwargs),
                fallback_func=fallback_func
            )
        return wrapper
    return decorator


def ascii_fallback(text: str) -> str:
    """Fallback ASCII padrão."""
    if not isinstance(text, str):
        text = str(text)
    ascii_text = ''.join(c for c in text if ord(c) < 127 and (c.isprintable() or c in '\n\r\t '))
    return ascii_text or "Text_with_charset_issues"


def emergency_fallback(text: str) -> str:
    """Fallback de emergência extremo."""
    return f"Emergency_placeholder_{hash(str(text)) % 10000}"