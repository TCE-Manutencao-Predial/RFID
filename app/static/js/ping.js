// ping.js - JavaScript para página de PING

// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 50;
let totalRegistros = 0;
let autoRefreshInterval = null;
let antenasDisponiveis = [];
let lastScrollY = 0;

// Sistema de Toast
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
  // Carregar estatísticas APÓS os dados principais para não bloquear
  setTimeout(() => carregarEstatisticas(), 100);
});

function inicializarEventos() {
  // Eventos de filtro
  document.getElementById("filtroEtiqueta")
    .addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroAntena")
    .addEventListener("change", aplicarFiltros);
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
      url = `/RFID/api/ping/ultimos/${minutosRecentes}?${params}`;
    } else {
      url = `/RFID/api/ping?${params}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      totalRegistros = data.total;
      renderizarTabela(data.pings);
      atualizarPaginacao();
      window.scrollTo(0, lastScrollY);

      if (showToastMessage && data.pings.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${data.pings.length} registros de PING carregados${cacheInfo}`, "success");
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
  if (antena) {
    if (antena.startsWith('leitor:')) {
      filtros.codigo_leitor = antena.substring(7);
    } else {
      filtros.antena = antena;
    }
  }

  const dataInicio = document.getElementById("filtroDataInicio").value;
  if (dataInicio) {
    filtros.horario_inicio = dataInicio.replace('T', ' ') + ':00';
  }

  const dataFim = document.getElementById("filtroDataFim").value;
  if (dataFim) {
    filtros.horario_fim = dataFim.replace('T', ' ') + ':00';
  }

  return filtros;
}

function renderizarTabela(pings) {
  const tbody = document.getElementById("tabelaCorpo");
  const tabela = document.getElementById("tabelaPings");
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const paginacao = document.getElementById("paginacao");

  loadingState.style.display = "none";

  if (pings.length === 0) {
    tabela.style.display = "none";
    paginacao.style.display = "none";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  tabela.style.display = "table";
  paginacao.style.display = "flex";

  tbody.innerHTML = "";

  pings.forEach((ping) => {
    const tr = document.createElement("tr");
    
    // Adicionar classe para PINGs recentes
    const agora = new Date();
    const horaPing = new Date(ping.horario);
    const diffMinutos = (agora - horaPing) / (1000 * 60);
    
    if (diffMinutos < 5) {
      tr.classList.add("ping-recente");
    }

    // Indicador RSSI
    const rssiClass = getRSSIClass(ping.rssi);
    const rssiIndicator = `
      <div class="rssi-indicator ${rssiClass}">
        <span class="rssi-value">${ping.rssi}</span>
        <div class="rssi-bars">
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
          <div class="rssi-bar"></div>
        </div>
      </div>
    `;

    // Usar antena_completa se disponível
    const antenaDisplay = ping.antena_completa || `Antena ${ping.antena}`;

    // Indicador de foto
    const fotoIndicador = ping.tem_foto
      ? '<i class="fas fa-check-circle foto-disponivel" title="Foto disponível"></i> Sim'
      : '<i class="fas fa-times-circle foto-indisponivel" title="Sem foto"></i> Não';

    // Botão de foto - só mostrar se tem foto disponível
    const botaoFoto = ping.tem_foto 
      ? `<button class="rfid-action-btn rfid-action-btn-photo" 
                onclick="verFotoPing('${ping.etiqueta_hex}')"
                title="Ver foto">
          <i class="fas fa-camera"></i> Foto
        </button>`
      : '';

    tr.innerHTML = `
      <td>${ping.horario_formatado || ping.horario}</td>
      <td><span class="ping-badge">${ping.etiqueta_hex}</span></td>
      <td><span class="antena-badge">${antenaDisplay}</span></td>
      <td>${rssiIndicator}</td>
      <td>${fotoIndicador}</td>
      <td>
        <div class="rfid-actions">
          <button class="rfid-action-btn rfid-action-btn-info" 
                  onclick="verDetalhesPing('${ping.etiqueta_hex}')"
                  title="Ver histórico">
            <i class="fas fa-history"></i> Histórico
          </button>
          ${botaoFoto}
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
    const response = await fetch('/RFID/api/ping/antenas');
    const data = await response.json();

    if (data.success) {
      antenasDisponiveis = data.antenas;
      const select = document.getElementById("filtroAntena");
      select.innerHTML = '<option value="">Todas as Antenas</option>';

      // Agrupar antenas por código do leitor
      const antenasAgrupadas = {};
      data.antenas.forEach(antena => {
        if (!antenasAgrupadas[antena.codigo_leitor]) {
          antenasAgrupadas[antena.codigo_leitor] = [];
        }
        antenasAgrupadas[antena.codigo_leitor].push(antena);
      });

      Object.keys(antenasAgrupadas).sort().forEach(codigoLeitor => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `Leitor ${codigoLeitor}`;
        antenasAgrupadas[codigoLeitor].forEach(antena => {
          const option = document.createElement('option');
          option.value = antena.antena;
          option.textContent = `[${codigoLeitor}] A${antena.antena}`;
          optgroup.appendChild(option);
        });
        select.appendChild(optgroup);
      });
      
      // Adicionar opção de filtrar por leitor completo
      const leitoresUnicos = Object.keys(antenasAgrupadas);
      if (leitoresUnicos.length > 1) {
        const separador = document.createElement('option');
        separador.disabled = true;
        separador.textContent = '─────────────';
        select.appendChild(separador);
        
        leitoresUnicos.forEach(codigoLeitor => {
          const option = document.createElement('option');
          option.value = `leitor:${codigoLeitor}`;
          option.textContent = `Todas do Leitor ${codigoLeitor}`;
          select.appendChild(option);
        });
      }
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

    const response = await fetch(`/RFID/api/ping/estatisticas?${params}`);
    const data = await response.json();

    if (data.success && data.estatisticas) {
      const stats = data.estatisticas;
      
      document.getElementById("totalPings").textContent = 
        formatarNumero(stats.total_pings || 0);
      
      document.getElementById("pingsComFoto").textContent = 
        formatarNumero(stats.pings_com_foto || 0);
      
      document.getElementById("antenasAtivas").textContent = 
        stats.total_antenas || 0;
      
      document.getElementById("ultimoPing").textContent = 
        stats.ultimo_ping_formatado || '--';
    }
  } catch (error) {
    console.error("Erro ao carregar estatísticas:", error);
  }
}

function formatarNumero(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function verDetalhesPing(codigo) {
  // Preencher informações básicas
  document.getElementById("detalhesCodigo").textContent = codigo;
  
  // Carregar histórico
  carregarHistoricoPing(codigo);
  
  // Abrir modal
  abrirModal("modalDetalhes");
}

async function carregarHistoricoPing(codigo) {
  const historicoLoading = document.getElementById("historicoLoading");
  const historicoContent = document.getElementById("historicoContent");
  
  historicoLoading.style.display = "block";
  historicoContent.innerHTML = "";
  
  try {
    const response = await fetch(`/RFID/api/ping/etiqueta/${codigo}?limite=50`);
    const data = await response.json();
    
    if (data.success && data.pings.length > 0) {
      let html = '<div class="historico-list">';
      
      data.pings.forEach(ping => {
        const rssiClass = getRSSIClass(ping.RSSI);
        const antenaDisplay = ping.CodigoLeitor 
          ? `[${ping.CodigoLeitor}] A${ping.Antena}` 
          : `Antena ${ping.Antena}`;
        const temFoto = ping.TemFoto ? '<i class="fas fa-camera foto-disponivel"></i>' : '';
          
        html += `
          <div class="historico-item">
            <div class="historico-time">
              <i class="fas fa-clock"></i>
              ${ping.horario_formatado || ping.Horario}
              ${temFoto}
            </div>
            <div class="historico-details">
              <div class="historico-antena">
                <i class="fas fa-satellite"></i>
                ${antenaDisplay}
              </div>
              <div class="rssi-indicator ${rssiClass}">
                RSSI: ${ping.RSSI}
              </div>
              <div>
                <i class="fas fa-microchip"></i>
                Leitor: ${ping.CodigoLeitor}
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

async function verFotoPing(codigo) {
  try {
    // Preencher informações no modal
    document.getElementById("fotoEtiquetaCodigo").textContent = codigo;
    document.getElementById("fotoEtiquetaInfo").textContent = "Verificando disponibilidade...";
    
    // Mostrar loading
    const fotoContainer = document.getElementById("fotoContainer");
    const fotoLoading = document.getElementById("fotoLoading");
    
    fotoContainer.innerHTML = '';
    fotoLoading.style.display = "block";
    
    // Abrir modal
    abrirModal("modalFoto");

    // Verificar se o PING tem foto
    const infoResponse = await fetch(`/RFID/api/ping/foto/info/${codigo}`);
    
    if (!infoResponse.ok) {
      throw new Error(`Erro HTTP: ${infoResponse.status}`);
    }
    
    const infoData = await infoResponse.json();
    
    if (!infoData.success) {
      throw new Error(infoData.error || "Erro ao verificar foto");
    }
    
    // Atualizar informações da foto
    document.getElementById("fotoEtiquetaInfo").textContent = 
      `Total de fotos: ${infoData.total_fotos} | Última foto: ${infoData.ultima_foto ? new Date(infoData.ultima_foto).toLocaleString('pt-BR') : 'N/A'}`;
    
    if (!infoData.tem_foto) {
      fotoLoading.style.display = "none";
      fotoContainer.innerHTML = `
        <div class="foto-erro">
          <i class="fas fa-image"></i>
          <p>Este PING não possui foto disponível</p>
          <small>Nenhuma foto foi encontrada nos registros deste PING.</small>
        </div>
      `;
      return;
    }
    
    // Carregar a foto
    const fotoUrl = `/RFID/api/ping/foto/${codigo}?t=${Date.now()}`;
    
    const img = new Image();
    img.onload = function() {
      fotoLoading.style.display = "none";
      fotoContainer.innerHTML = `
        <img src="${fotoUrl}" alt="Foto do PING ${codigo}" class="foto-etiqueta" />
        <div class="foto-controls">
          <button class="rfid-btn rfid-btn-secondary" onclick="downloadFoto('${codigo}')">
            <i class="fas fa-download"></i> Baixar
          </button>
          <button class="rfid-btn rfid-btn-secondary" onclick="abrirFotoNovaAba('${fotoUrl}')">
            <i class="fas fa-external-link-alt"></i> Nova Aba
          </button>
        </div>
      `;
    };
    
    img.onerror = function() {
      fotoLoading.style.display = "none";
      fotoContainer.innerHTML = `
        <div class="foto-erro">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Erro ao carregar a imagem</p>
          <small>A imagem pode estar corrompida ou em um formato não suportado.</small>
          <button class="rfid-btn rfid-btn-primary" onclick="verFotoPing('${codigo}')">
            <i class="fas fa-redo"></i> Tentar Novamente
          </button>
        </div>
      `;
    };
    
    img.src = fotoUrl;
    
  } catch (error) {
    console.error("Erro ao verificar foto:", error);
    
    const fotoLoading = document.getElementById("fotoLoading");
    const fotoContainer = document.getElementById("fotoContainer");
    
    fotoLoading.style.display = "none";
    fotoContainer.innerHTML = `
      <div class="foto-erro">
        <i class="fas fa-exclamation-triangle"></i>
        <p>Erro ao carregar foto</p>
        <small>${error.message}</small>
        <button class="rfid-btn rfid-btn-primary" onclick="verFotoPing('${codigo}')">
          <i class="fas fa-redo"></i> Tentar Novamente
        </button>
      </div>
    `;
    
    showToast(`Erro ao carregar foto: ${error.message}`, "error");
  }
}

function downloadFoto(codigo) {
  const link = document.createElement('a');
  link.href = `/RFID/api/ping/foto/${codigo}`;
  link.download = `ping_${codigo}.jpg`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("Download iniciado", "success");
}

function abrirFotoNovaAba(url) {
  window.open(url, '_blank');
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

// Funções de paginação
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

function criarBotaoPagina(texto, ativo, onclick) {
  const btn = document.createElement("button");
  btn.className = "rfid-page-btn";
  btn.textContent = texto;
  btn.disabled = !ativo;
  if (ativo && onclick) {
    btn.addEventListener("click", () => {
      lastScrollY = window.scrollY;
      onclick();
      btn.blur();
    });
  }
  return btn;
}

function mostrarLoading() {
  document.getElementById("loadingState").style.display = "block";
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
  document.getElementById("tabelaPings").style.display = "none";
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
      window.location.href = '/RFID/leitores';
      break;
    
    case 'emprestimos':
      window.location.href = '/RFID/emprestimos';
      break;
    
    case 'ping':
      // Já estamos aqui
      break;
    
    default:
      showToast('Seção não encontrada', 'error');
  }
}

// Destacar botão da página atual
document.addEventListener('DOMContentLoaded', function() {
  const allNavButtons = document.querySelectorAll('.rfid-nav-btn');
  allNavButtons.forEach(btn => btn.classList.remove('active'));
  
  const currentPath = window.location.pathname;
  if (currentPath.includes('ping')) {
    document.querySelector('.rfid-nav-btn[onclick*="ping"]')?.classList.add('active');
  }
});
