// leitores.js - JavaScript para página de leituras RFID

// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 50; // Mais registros para leituras
let totalRegistros = 0;
let autoRefreshInterval = null;
let antenasDisponiveis = [];

// 1) Nova variável global para guardar o scroll
let lastScrollY = 0;

// Sistema de Toast (reutilizado)
function showToast(message, type = "info", title = "") {
  const toastContainer = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icons = {
    success: "fa-check-circle",
    error: "fa-exclamation-circle",
    warning: "fa-exclamation-triangle",
    info: "fa-info-circle",
  };

  const titles = {
    success: "Sucesso",
    error: "Erro",
    warning: "Aviso",
    info: "Informação",
  };

  toast.innerHTML = `
    <i class="fas ${icons[type]} toast-icon"></i>
    <div class="toast-content">
        <div class="toast-title">${title || titles[type]}</div>
        <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">
        <i class="fas fa-times"></i>
    </button>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  }, 5000);

  toast.addEventListener("click", () => {
    toast.style.animation = "slideOut 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  });
}

// Inicialização
document.addEventListener("DOMContentLoaded", function () {
  inicializarEventos();
  carregarAntenas();
  carregarDados();
  carregarEstatisticas();
  configurarAutoRefresh();
});

function inicializarEventos() {
  // Eventos de filtro
  document.getElementById("filtroEtiqueta").addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroAntena").addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataInicio").addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataFim").addEventListener("change", aplicarFiltros);
  document.getElementById("filtroRecentes").addEventListener("change", aplicarFiltroRecentes);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function aplicarFiltros() {
  paginaAtual = 1;
  carregarDados();
}

function aplicarFiltroRecentes() {
  const minutos = document.getElementById("filtroRecentes").value;
  
  if (minutos) {
    // Limpar filtros de data ao usar recentes
    document.getElementById("filtroDataInicio").value = "";
    document.getElementById("filtroDataFim").value = "";
  }
  
  aplicarFiltros();
}

function atualizarDados() {
  carregarDados(true, true);
  carregarEstatisticas(true);
}

async function carregarDados(forceRefresh = false, showToastMessage = false) {
  mostrarLoading();
  let response = null;
  try {
    const offset = (paginaAtual - 1) * registrosPorPagina;
    const filtros = obterFiltros();

    // Construir query string
    const params = new URLSearchParams({
      limite: registrosPorPagina,
      offset: offset,
      ...filtros,
    });

    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    // Verificar se é filtro de recentes
    const minutosRecentes = document.getElementById("filtroRecentes").value;
    let url;
    
    if (minutosRecentes) {
      url = `/RFID/api/leituras/ultimas/${minutosRecentes}?${params}`;
    } else {
      url = `/RFID/api/leituras?${params}`;
    }

    response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      totalRegistros = data.total;
      renderizarTabela(data.leituras);
      atualizarPaginacao();
      window.scrollTo(0, lastScrollY); // restaura a posição guardada

      if (showToastMessage && data.leituras.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${data.leituras.length} leituras carregadas${cacheInfo}`, "success");
      }
    } else {
      throw new Error(data.error || "Erro ao carregar dados");
    }
  } catch (error) {
    console.error("Erro:", error);
    mostrarErro(error.message);
    showToast(error.message, "error");
  }
}

function obterFiltros() {
  const filtros = {};

  const etiqueta = document.getElementById("filtroEtiqueta").value.trim();
  if (etiqueta) filtros.etiqueta = etiqueta;

  const antena = document.getElementById("filtroAntena").value;
  if (antena) filtros.antena = antena;

  const dataInicio = document.getElementById("filtroDataInicio").value;
  if (dataInicio) {
    // Converter para formato esperado pela API
    filtros.horario_inicio = dataInicio.replace('T', ' ') + ':00';
  }

  const dataFim = document.getElementById("filtroDataFim").value;
  if (dataFim) {
    filtros.horario_fim = dataFim.replace('T', ' ') + ':00';
  }

  return filtros;
}

function renderizarTabela(leituras) {
  const tbody = document.getElementById("tabelaCorpo");
  const tabela = document.getElementById("tabelaLeituras");
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const paginacao = document.getElementById("paginacao");

  loadingState.style.display = "none";

  if (leituras.length === 0) {
    tabela.style.display = "none";
    paginacao.style.display = "none";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  tabela.style.display = "table";
  paginacao.style.display = "flex";

  tbody.innerHTML = "";

  leituras.forEach((leitura, index) => {
    const tr = document.createElement("tr");
    
    // Adicionar classe para leituras recentes
    const agora = new Date();
    const horaLeitura = new Date(leitura.horario);
    const diffMinutos = (agora - horaLeitura) / (1000 * 60);
    
    if (diffMinutos < 5) {
      tr.classList.add("leitura-recente");
    }

    // Status da etiqueta
    let statusBadge = '';
    switch (leitura.status_etiqueta) {
      case 'ativa':
        statusBadge = '<span class="rfid-badge rfid-badge-active">Cadastrada</span>';
        break;
      case 'destruida':
        statusBadge = '<span class="rfid-badge rfid-badge-destroyed">Destruída</span>';
        break;
      default:
        statusBadge = '<span class="rfid-badge rfid-badge-nao-cadastrada">Não Cadastrada</span>';
    }

    // Indicador RSSI
    const rssiClass = getRSSIClass(leitura.rssi);
    const rssiIndicator = `
      <div class="rssi-indicator ${rssiClass}">
        <span class="rssi-value">${leitura.rssi}</span>
        <div class="rssi-bars">
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
        </div>
      </div>
    `;

    tr.innerHTML = `
      <td>${leitura.horario_formatado || leitura.horario}</td>
      <td><span class="rfid-etiqueta">${leitura.etiqueta_hex}</span></td>
      <td>${leitura.descricao_equipamento || '-'}</td>
      <td><span class="antena-badge">Antena ${leitura.antena}</span></td>
      <td>${rssiIndicator}</td>
      <td>${statusBadge}</td>
      <td>
        <div class="rfid-actions">
          <button class="rfid-action-btn rfid-action-btn-info" 
                  onclick="verDetalhesEtiqueta('${leitura.etiqueta_hex}', '${leitura.descricao_equipamento || 'Sem descrição'}', '${leitura.status_etiqueta}')"
                  title="Ver histórico">
            <i class="fas fa-history"></i> Histórico
          </button>
        </div>
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function getRSSIClass(rssi) {
  const valor = Math.abs(parseInt(rssi));
  if (valor <= 50) return 'rssi-excellent';
  if (valor <= 60) return 'rssi-good';
  if (valor <= 70) return 'rssi-fair';
  return 'rssi-poor';
}

async function carregarAntenas() {
  try {
    const response = await fetch('/RFID/api/leituras/antenas');
    const data = await response.json();

    if (data.success) {
      antenasDisponiveis = data.antenas;
      const select = document.getElementById("filtroAntena");
      
      // Limpar e adicionar opção padrão
      select.innerHTML = '<option value="">Todas as Antenas</option>';
      
      // Adicionar antenas
      data.antenas.forEach(antena => {
        const option = document.createElement('option');
        option.value = antena.Antena;
        option.textContent = `Antena ${antena.Antena} (${antena.total_leituras} leituras)`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error("Erro ao carregar antenas:", error);
  }
}

async function carregarEstatisticas(forceRefresh = false) {
  try {
    const params = new URLSearchParams();
    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    const response = await fetch(`/RFID/api/leituras/estatisticas?${params}`);
    const data = await response.json();

    if (data.success && data.estatisticas) {
      const stats = data.estatisticas;
      
      document.getElementById("totalLeituras").textContent = 
        formatarNumero(stats.total_leituras || 0);
      
      document.getElementById("etiquetasUnicas").textContent = 
        formatarNumero(stats.total_etiquetas_unicas || 0);
      
      document.getElementById("antenasAtivas").textContent = 
        stats.total_antenas || 0;
      
      document.getElementById("ultimaLeitura").textContent = 
        stats.ultima_leitura_formatada || '--';
    }
  } catch (error) {
    console.error("Erro ao carregar estatísticas:", error);
  }
}

function formatarNumero(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function verDetalhesEtiqueta(codigo, descricao, status) {
  // Preencher informações básicas
  document.getElementById("detalhesCodigo").textContent = codigo;
  document.getElementById("detalhesDescricao").textContent = descricao;
  
  // Status badge
  let statusHtml = '';
  switch (status) {
    case 'ativa':
      statusHtml = '<span class="rfid-badge rfid-badge-active">Cadastrada Ativa</span>';
      break;
    case 'destruida':
      statusHtml = '<span class="rfid-badge rfid-badge-destroyed">Cadastrada Destruída</span>';
      break;
    default:
      statusHtml = '<span class="rfid-badge rfid-badge-nao-cadastrada">Não Cadastrada</span>';
  }
  document.getElementById("detalhesStatus").innerHTML = statusHtml;
  
  // Carregar histórico
  carregarHistoricoEtiqueta(codigo);
  
  // Abrir modal
  abrirModal("modalDetalhes");
}

async function carregarHistoricoEtiqueta(codigo) {
  const historicoLoading = document.getElementById("historicoLoading");
  const historicoContent = document.getElementById("historicoContent");
  
  historicoLoading.style.display = "block";
  historicoContent.innerHTML = "";
  
  try {
    const response = await fetch(`/RFID/api/leituras/etiqueta/${codigo}?limite=50`);
    const data = await response.json();
    
    if (data.success && data.leituras.length > 0) {
      let html = '<div class="historico-list">';
      
      data.leituras.forEach(leitura => {
        const rssiClass = getRSSIClass(leitura.RSSI);
        html += `
          <div class="historico-item">
            <div class="historico-time">
              <i class="fas fa-clock"></i>
              ${leitura.horario_formatado || leitura.Horario}
            </div>
            <div class="historico-details">
              <div class="historico-antena">
                <i class="fas fa-satellite"></i>
                Antena ${leitura.Antena}
              </div>
              <div class="rssi-indicator ${rssiClass}">
                RSSI: ${leitura.RSSI}
              </div>
              <div>
                <i class="fas fa-microchip"></i>
                Leitor: ${leitura.CodigoLeitor}
              </div>
            </div>
          </div>
        `;
      });
      
      html += '</div>';
      historicoContent.innerHTML = html;
    } else {
      historicoContent.innerHTML = '<p class="text-center">Nenhum histórico encontrado</p>';
    }
  } catch (error) {
    console.error("Erro ao carregar histórico:", error);
    historicoContent.innerHTML = '<p class="text-center text-danger">Erro ao carregar histórico</p>';
  } finally {
    historicoLoading.style.display = "none";
  }
}

// Funções de modal
function abrirModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.style.display = "block";
  setTimeout(() => modal.classList.add("active"), 10);
}

function fecharModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.remove("active");
  setTimeout(() => modal.style.display = "none", 300);
}

// Auto-refresh configurável
function configurarAutoRefresh() {
  // Por enquanto, sem auto-refresh automático
  // Pode ser implementado com checkbox ou configuração
}

// Funções de paginação (reutilizadas)
function atualizarPaginacao() {
  const inicio = (paginaAtual - 1) * registrosPorPagina + 1;
  const fim = Math.min(paginaAtual * registrosPorPagina, totalRegistros);

  document.getElementById("registroInicio").textContent = totalRegistros > 0 ? inicio : 0;
  document.getElementById("registroFim").textContent = fim;
  document.getElementById("registroTotal").textContent = totalRegistros;

  const totalPaginas = Math.ceil(totalRegistros / registrosPorPagina);
  const controles = document.getElementById("paginacaoControles");
  controles.innerHTML = "";

  // Botão Anterior
  const btnAnterior = criarBotaoPagina("Anterior", paginaAtual > 1, () => {
    paginaAtual--;
    carregarDados();
  });
  controles.appendChild(btnAnterior);

  // Páginas
  const maxPaginas = 5;
  let inicioPag = Math.max(1, paginaAtual - Math.floor(maxPaginas / 2));
  let fimPag = Math.min(totalPaginas, inicioPag + maxPaginas - 1);

  if (fimPag - inicioPag < maxPaginas - 1) {
    inicioPag = Math.max(1, fimPag - maxPaginas + 1);
  }

  for (let i = inicioPag; i <= fimPag; i++) {
    const btn = criarBotaoPagina(i, true, () => {
      paginaAtual = i;
      carregarDados();
    });

    if (i === paginaAtual) {
      btn.classList.add("active");
    }

    controles.appendChild(btn);
  }

  // Botão Próximo
  const btnProximo = criarBotaoPagina("Próximo", paginaAtual < totalPaginas, () => {
    paginaAtual++;
    carregarDados();
  });
  controles.appendChild(btnProximo);
}

// 2) Substitua a função criarBotaoPagina por esta versão que salva o scroll
function criarBotaoPagina(texto, ativo, onclick) {
  const btn = document.createElement("button");
  btn.className = "rfid-page-btn";
  btn.textContent = texto;
  btn.disabled = !ativo;
  if (ativo && onclick) {
    btn.addEventListener("click", () => {
      lastScrollY = window.scrollY;  // salva posição
      onclick();
      btn.blur();                   // remove foco
    });
  }
  return btn;
}

function mostrarLoading() {
  document.getElementById("loadingState").style.display = "block";
  // document.getElementById("tabelaLeituras").style.display = "none"; // comentado
  document.getElementById("emptyState").style.display = "none";
  document.getElementById("paginacao").style.display = "none";
}

function mostrarErro(mensagem, detalhe = "") {
  const emptyState = document.getElementById("emptyState");
  emptyState.innerHTML = `
    <i class="fas fa-exclamation-triangle" style="color: var(--rfid-danger);"></i>
    <h3>Erro ao carregar dados</h3>
    <p>${mensagem}</p>
    ${detalhe ? `<p style="font-size: 0.85rem; color: #6c757d; margin-top: 10px;">${detalhe}</p>` : ""}
    <button class="rfid-btn rfid-btn-primary" onclick="carregarDados()">
        <i class="fas fa-redo"></i> Tentar Novamente
    </button>
  `;
  emptyState.style.display = "block";
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("tabelaLeituras").style.display = "none";
}

function exportarDados() {
  showToast("Funcionalidade de exportação será implementada em breve!", "info");
}

// Navegação
function navegarPara(secao) {
    switch(secao) {
        case 'etiquetas':
            window.location.href = '/RFID/';
            break;
            
        case 'inventarios':
            window.location.href = '/RFID/inventarios';
            break;
        
        case 'leitores':
            // Já estamos aqui - poderia recarregar ou não fazer nada
            // window.location.href = '/RFID/leitores';
            break;
        
        case 'emprestimos':
            window.location.href = '/RFID/emprestimos';
            break;
        
        default:
            showToast('Seção não encontrada', 'error');
    }
}


// Adicionar tooltips aos botões de navegação
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar data-tooltip aos botões de navegação
    const navButtons = document.querySelectorAll('.rfid-nav-btn');
    navButtons.forEach(btn => {
        const texto = btn.querySelector('span').textContent;
        btn.setAttribute('data-tooltip', texto);
    });
    
    // Remover classe active de todos os botões primeiro
    const allNavButtons = document.querySelectorAll('.rfid-nav-btn');
    allNavButtons.forEach(btn => btn.classList.remove('active'));
    
    // Destacar botão da página atual
    const currentPath = window.location.pathname;
    
    // Lógica específica para cada página
    if (currentPath === '/RFID/' || 
        currentPath === '/RFID' || 
        currentPath === '/RFID/index' || 
        currentPath === '/RFID/etiquetas') {
        document.querySelector('.rfid-nav-btn[onclick*="etiquetas"]')?.classList.add('active');
    } else if (currentPath.includes('inventarios')) {
        document.querySelector('.rfid-nav-btn[onclick*="inventarios"]')?.classList.add('active');
    } else if (currentPath.includes('leitores')) {
        document.querySelector('.rfid-nav-btn[onclick*="leitores"]')?.classList.add('active');
    } else if (currentPath.includes('emprestimos')) {
        document.querySelector('.rfid-nav-btn[onclick*="emprestimos"]')?.classList.add('active');
    }
});