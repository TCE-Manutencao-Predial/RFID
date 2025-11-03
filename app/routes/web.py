# app/routes/web.py
from flask import Blueprint, render_template, current_app, request, abort, jsonify
import logging
import requests
import urllib3

# Suprimir avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

web_bp = Blueprint('web', __name__)
logger = logging.getLogger('controlerfid.web')

# URLs da API do HelpDesk Monitor
HELPDESK_API_BASE = 'https://automacao.tce.go.gov.br/helpdeskmonitor/api'
HELPDESK_API_USUARIOS = f'{HELPDESK_API_BASE}/usuarios_htpasswd'

# Cache de competências dos usuários (evita múltiplas requisições)
_cache_competencias = {}
_cache_timeout = 300  # 5 minutos

def obter_usuario_atual():
    """Obtém o nome do usuário autenticado via HTTP Basic Auth."""
    # Apache passa o usuário autenticado via REMOTE_USER
    # Também verifica HTTP_REMOTE_USER, headers HTTP e request.remote_user
    usuario = (request.environ.get('REMOTE_USER') or 
               request.environ.get('HTTP_REMOTE_USER') or
               request.headers.get('X-Remote-User') or
               request.headers.get('Remote-User') or
               getattr(request, 'remote_user', None) or '')
    
    # Log para debug
    if not usuario:
        logger.warning(f"Usuário não autenticado. REMOTE_USER: {request.environ.get('REMOTE_USER')}, "
                      f"HTTP_REMOTE_USER: {request.environ.get('HTTP_REMOTE_USER')}, "
                      f"X-Remote-User header: {request.headers.get('X-Remote-User')}, "
                      f"Remote-User header: {request.headers.get('Remote-User')}")
    
    return usuario.lower() if usuario else None

def obter_competencias_usuario(usuario_htpasswd):
    """
    Obtém as competências (funções) de um usuário consultando a API do HelpDesk Monitor.
    
    Returns:
        list: Lista de competências (funções) do usuário, ou lista vazia se não encontrado
    """
    if not usuario_htpasswd:
        return []
    
    # Verificar cache
    if usuario_htpasswd in _cache_competencias:
        return _cache_competencias[usuario_htpasswd]
    
    try:
        # Consultar API do HelpDesk Monitor (ignorando verificação SSL)
        url = f"{HELPDESK_API_USUARIOS}/{usuario_htpasswd}"
        response = requests.get(url, timeout=5, verify=False)
        
        if response.status_code == 200:
            dados = response.json()
            # A API pode retornar o campo 'funcoes' (lista) ou precisamos buscar nos técnicos
            competencias = dados.get('funcoes', [])
            
            # Se não houver funcoes direto, buscar nos técnicos
            if not competencias:
                url_tecnico = f"{HELPDESK_API_BASE}/contatos_tecnicos"
                response_tecnico = requests.get(url_tecnico, timeout=5, verify=False)
                if response_tecnico.status_code == 200:
                    tecnicos = response_tecnico.json()
                    usuario_lower = usuario_htpasswd.lower()
                    for tecnico in tecnicos:
                        nome_usuario = tecnico.get('nome_usuario_htpasswd')
                        if nome_usuario and nome_usuario.lower() == usuario_lower:
                            competencias = tecnico.get('funcoes', [])
                            break
            
            # Cachear resultado
            _cache_competencias[usuario_htpasswd] = competencias
            logger.info(f"Competências obtidas para {usuario_htpasswd}: {competencias}")
            return competencias
        else:
            logger.warning(f"Usuário {usuario_htpasswd} não encontrado na API do HelpDesk Monitor")
            _cache_competencias[usuario_htpasswd] = []
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao consultar API do HelpDesk Monitor para {usuario_htpasswd}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao obter competências para {usuario_htpasswd}: {e}")
        return []

def usuario_tem_competencia(competencia_requerida):
    """
    Verifica se o usuário atual possui uma competência específica.
    
    Args:
        competencia_requerida: Nome da competência (ex: 'RFID', 'TI')
    
    Returns:
        bool: True se o usuário possui a competência
    """
    usuario = obter_usuario_atual()
    if not usuario:
        return False
    
    competencias = obter_competencias_usuario(usuario)
    competencia_upper = competencia_requerida.upper()
    
    return competencia_upper in [c.upper() for c in competencias]

def usuario_pode_acessar_sistema():
    """Verifica se o usuário tem a competência RFID para acessar o sistema."""
    return usuario_tem_competencia('RFID')

def usuario_pode_acessar_ping():
    """Verifica se o usuário tem a competência TI para acessar funcionalidades PING."""
    return usuario_tem_competencia('TI')

@web_bp.route('/')
@web_bp.route('/index')
@web_bp.route('/index.html')
@web_bp.route('/etiquetas')
def etiquetas():
    """Página principal de controle de etiquetas RFID."""
    # Verificar se o usuário tem competência RFID
    if not usuario_pode_acessar_sistema():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar o sistema sem a competência RFID")
        abort(403)  # Forbidden
    
    gerenciador = current_app.config.get('GERENCIADOR_RFID')
    if not gerenciador:
        logger.error("Gerenciador RFID não inicializado")
        abort(500)
    
    # Obter estatísticas
    stats_result = gerenciador.obter_estatisticas()
    estatisticas = stats_result.get('estatisticas', {})
    
    # Passar informação de acesso ao PING para o template
    usuario_atual = obter_usuario_atual()
    pode_acessar_ping = usuario_pode_acessar_ping()
    
    return render_template('etiquetas.html', 
                         estatisticas=estatisticas,
                         usuario_atual=usuario_atual,
                         pode_acessar_ping=pode_acessar_ping)

@web_bp.route('/inventarios')
@web_bp.route('/inventarios.html')
def inventarios():
    """Página de gerenciamento de inventários RFID."""
    # Verificar se o usuário tem competência RFID
    if not usuario_pode_acessar_sistema():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar inventários sem a competência RFID")
        abort(403)  # Forbidden
    
    gerenciador = current_app.config.get('GERENCIADOR_RFID')
    if not gerenciador:
        logger.error("Gerenciador RFID não inicializado")
        abort(500)
    
    # Passar informação de acesso ao PING para o template
    usuario_atual = obter_usuario_atual()
    pode_acessar_ping = usuario_pode_acessar_ping()
    
    # Futuramente: obter dados específicos de inventários
    # Por enquanto, renderiza a página básica
    return render_template('inventarios.html',
                         usuario_atual=usuario_atual,
                         pode_acessar_ping=pode_acessar_ping)

@web_bp.route('/leitores')
@web_bp.route('/leitores.html')
def leitores():
    """Página de gerenciamento de leitores RFID."""
    # Verificar se o usuário tem competência RFID
    if not usuario_pode_acessar_sistema():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar leitores sem a competência RFID")
        abort(403)  # Forbidden
    
    gerenciador = current_app.config.get('GERENCIADOR_RFID')
    if not gerenciador:
        logger.error("Gerenciador RFID não inicializado")
        abort(500)
    
    # Passar informação de acesso ao PING para o template
    usuario_atual = obter_usuario_atual()
    pode_acessar_ping = usuario_pode_acessar_ping()
    
    # Futuramente: obter dados específicos de leitores
    # Por enquanto, renderiza a página básica
    return render_template('leitores.html',
                         usuario_atual=usuario_atual,
                         pode_acessar_ping=pode_acessar_ping)

@web_bp.route('/emprestimos')
@web_bp.route('/emprestimos.html')
def emprestimos():
    """Página de gerenciamento de empréstimos de ferramentas."""
    # Verificar se o usuário tem competência RFID
    if not usuario_pode_acessar_sistema():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar empréstimos sem a competência RFID")
        abort(403)  # Forbidden
    
    gerenciador = current_app.config.get('GERENCIADOR_RFID')
    if not gerenciador:
        logger.error("Gerenciador RFID não inicializado")
        abort(500)
    
    # Passar informação de acesso ao PING para o template
    usuario_atual = obter_usuario_atual()
    pode_acessar_ping = usuario_pode_acessar_ping()
    
    # Futuramente: obter dados específicos de empréstimos
    # Por enquanto, renderiza a página básica
    return render_template('emprestimos.html',
                         usuario_atual=usuario_atual,
                         pode_acessar_ping=pode_acessar_ping)

@web_bp.route('/ping')
@web_bp.route('/ping.html')
def ping():
    """Página de monitoramento de registros PING."""
    # Verificar se o usuário tem competência RFID (acesso básico ao sistema)
    if not usuario_pode_acessar_sistema():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar PING sem a competência RFID")
        abort(403)  # Forbidden
    
    # Verificar se o usuário tem competência TI (acesso ao PING)
    if not usuario_pode_acessar_ping():
        usuario = obter_usuario_atual()
        logger.warning(f"Usuário '{usuario}' tentou acessar página PING sem a competência TI")
        abort(403)  # Forbidden
    
    gerenciador = current_app.config.get('GERENCIADOR_RFID')
    if not gerenciador:
        logger.error("Gerenciador RFID não inicializado")
        abort(500)
    
    usuario_atual = obter_usuario_atual()
    
    # Renderiza a página de PING
    return render_template('ping.html',
                         usuario_atual=usuario_atual,
                         pode_acessar_ping=True)

@web_bp.route('/debug/auth')
def debug_auth():
    """Endpoint de debug para verificar autenticação (apenas para desenvolvimento)."""
    # Remover em produção ou proteger adequadamente
    environ_data = {
        'REMOTE_USER': request.environ.get('REMOTE_USER'),
        'HTTP_REMOTE_USER': request.environ.get('HTTP_REMOTE_USER'),
        'HTTP_AUTHORIZATION': 'PRESENT' if request.environ.get('HTTP_AUTHORIZATION') else 'MISSING',
        'REQUEST_METHOD': request.environ.get('REQUEST_METHOD'),
        'PATH_INFO': request.environ.get('PATH_INFO'),
    }
    
    # Headers relevantes
    headers_data = {
        'X-Remote-User': request.headers.get('X-Remote-User'),
        'Remote-User': request.headers.get('Remote-User'),
        'Authorization': 'PRESENT' if request.headers.get('Authorization') else 'MISSING',
    }
    
    usuario = obter_usuario_atual()
    competencias = obter_competencias_usuario(usuario) if usuario else []
    
    return jsonify({
        'usuario_detectado': usuario,
        'competencias': competencias,
        'pode_acessar_sistema': usuario_pode_acessar_sistema(),
        'pode_acessar_ping': usuario_pode_acessar_ping(),
        'environ': environ_data,
        'headers': headers_data,
        'cache_size': len(_cache_competencias)
    })