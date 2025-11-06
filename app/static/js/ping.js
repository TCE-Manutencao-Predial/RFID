// ping.js - JavaScript para página de PING
// Refatorado para usar tabela pingsRFID

// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 50;
let totalRegistros = 0;
let autoRefreshInterval = null;
let locaisDisponiveis = [];
let lastScrollY = 0;

/**
 * Formata local e antena para exibição
 * @param {string} local - Local (B1, B2, S1)
 * @param {string} antena - Número da antena
 * @returns {string} - Formato local_antena
 */
function formatarLocalAntena(local, antena) {
  if (!local || !antena) return "-";
  return `${local} - A${antena}`;
}

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
  carregarLocais();
  carregarDados();
  setTimeout(() => carregarEstatisticas(), 100);
});

function inicializarEventos() {
  // Eventos de filtro
  document.getElementById("filtroLocal")?.addEventListener("change", aplicarFiltros);
  document.getElementById("filtroAntena")?.addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataInicio")?.addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataFim")?.addEventListener("change", aplicarFiltros);
}

function aplicarFiltros() {
  paginaAtual = 1;
  carregarDados();
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

    const params = new URLSearchParams({
      limite: registrosPorPagina,
      offset: offset,
      ...filtros,
    });

    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    const url = `/RFID/api/ping?${params}`;
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

  const local = document.getElementById("filtroLocal")?.value;
  if (local) filtros.local = local;

  const antena = document.getElementById("filtroAntena")?.value;
  if (antena) filtros.antena = antena;

  const dataInicio = document.getElementById("filtroDataInicio")?.value;
  if (dataInicio) {
    filtros.horario_inicio = dataInicio.replace('T', ' ') + ':00';
  }

  const dataFim = document.getElementById("filtroDataFim")?.value;
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

    tr.innerHTML = `
      <td data-horario="${ping.horario}">${ping.horario_formatado || ping.horario}</td>
      <td><span class="local-badge">${ping.local}</span></td>
      <td><span class="antena-badge">${ping.antena}</span></td>
      <td>
        <div class="rfid-actions">
          <button class="rfid-action-btn rfid-action-btn-photo" 
                  onclick="verFotoPing('${ping.local}', '${ping.antena}', '${ping.horario}')"
                  title="Ver foto">
            <i class="fas fa-camera"></i> Foto
          </button>
        </div>
      </td>
    `;

    tbody.appendChild(tr);
  });
}

async function carregarLocais() {
  try {
    const response = await fetch('/RFID/api/ping/locais');
    const data = await response.json();

    if (data.success) {
      locaisDisponiveis = data.locais;
      
      // Preencher filtro de local
      const selectLocal = document.getElementById("filtroLocal");
      if (selectLocal) {
        selectLocal.innerHTML = '<option value="">Todos os Locais</option>';
        const locaisUnicos = [...new Set(data.locais.map(l => l.local))].sort();
        locaisUnicos.forEach(local => {
          const option = document.createElement('option');
          option.value = local;
          option.textContent = local;
          selectLocal.appendChild(option);
        });
      }

      // Preencher filtro de antena
      const selectAntena = document.getElementById("filtroAntena");
      if (selectAntena) {
        selectAntena.innerHTML = '<option value="">Todas as Antenas</option>';
        const antenasUnicas = [...new Set(data.locais.map(l => l.antena))].sort((a, b) => Number(a) - Number(b));
        antenasUnicas.forEach(antena => {
          const option = document.createElement('option');
          option.value = antena;
          option.textContent = `Antena ${antena}`;
          selectAntena.appendChild(option);
        });
      }
    }
  } catch (error) {
    console.error("Erro ao carregar locais:", error);
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
  // Preencher informações básicas com formatação
  const elementoCodigo = document.getElementById("detalhesCodigo");
  elementoCodigo.textContent = formatarEtiquetaRFID(codigo);
  elementoCodigo.title = `Código completo: ${codigo}`;
  
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

async function verFotoPing(local, antena, horario) {
  try {
    // Preencher informações no modal
    document.getElementById("fotoEtiquetaCodigo").textContent = `${local} - A${antena}`;
    document.getElementById("fotoEtiquetaInfo").textContent = "Carregando...";
    
    // Mostrar loading e limpar controles
    const fotoContainer = document.getElementById("fotoContainer");
    const fotoLoading = document.getElementById("fotoLoading");
    const controlsCompact = document.getElementById("fotoControlsCompact");
    
    fotoContainer.innerHTML = '';
    fotoLoading.style.display = "block";
    controlsCompact.style.display = "none";
    controlsCompact.innerHTML = '';
    
    // Abrir modal
    abrirModal("modalFoto");

    // Construir URL com parâmetros
    const params = new URLSearchParams({
      local: local,
      antena: antena,
      horario: horario
    });

    // Carregar a foto diretamente
    const fotoUrl = `/RFID/api/ping/foto?${params}&t=${Date.now()}`;
    
    const fotoResponse = await fetch(fotoUrl);
    
    if (!fotoResponse.ok) {
      // Tentar obter detalhes do erro
      const errorData = await fotoResponse.json().catch(() => null);
      
      fotoLoading.style.display = "none";
      
      // Verificar tipo de erro específico
      if (errorData && errorData.error_type === 'no_photo') {
        // Foto vazia no banco de dados
        document.getElementById("fotoEtiquetaInfo").textContent = 
          `Local: ${local} | Antena: ${antena} | Horário: ${new Date(horario).toLocaleString('pt-BR')}`;
        
        // Esconder controles quando não há foto
        document.getElementById("fotoControlsCompact").style.display = "none";
        
        fotoContainer.innerHTML = `
          <div class="foto-erro">
            <i class="fas fa-image"></i>
            <p>Sem imagem no Banco de Dados</p>
            <small>Este PING foi registrado, mas não possui foto armazenada.</small>
          </div>
        `;
        return;
      }
      
      // Outros erros
      throw new Error(errorData?.error || `Erro HTTP: ${fotoResponse.status}`);
    }
    
    // Atualizar informações da foto
    document.getElementById("fotoEtiquetaInfo").textContent = 
      `Local: ${local} | Antena: ${antena} | Horário: ${new Date(horario).toLocaleString('pt-BR')}`;
    
    // Mostrar controles compactos
    controlsCompact.style.display = "grid";
    controlsCompact.innerHTML = `
      <button class="rfid-btn rfid-btn-secondary" onclick="downloadFoto('${local}', '${antena}', '${horario}')">
        <i class="fas fa-download"></i> Baixar
      </button>
      <button class="rfid-btn rfid-btn-secondary" onclick="abrirFotoNovaAba('${fotoUrl}')">
        <i class="fas fa-external-link-alt"></i> Nova Aba
      </button>
    `;
    
    // Verificar se a resposta é uma imagem
    const contentType = fotoResponse.headers.get('content-type');
    if (!contentType || !contentType.startsWith('image/')) {
      throw new Error('Resposta não é uma imagem válida');
    }
    
    // Criar blob da imagem
    const blob = await fotoResponse.blob();
    const imageUrl = URL.createObjectURL(blob);
    
    const img = new Image();
    img.onload = function() {
      fotoLoading.style.display = "none";
      fotoContainer.innerHTML = `
        <img src="${imageUrl}" alt="Foto do PING ${codigo}" class="foto-etiqueta" />
      `;
    };
    
    img.onerror = function() {
      fotoLoading.style.display = "none";
      fotoContainer.innerHTML = `
        <div class="foto-erro">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Erro ao renderizar a imagem</p>
          <small>A imagem pode estar corrompida ou em um formato não suportado.</small>
        </div>
      `;
      // Esconder controles se houver erro
      document.getElementById("fotoControlsCompact").style.display = "none";
    };
    
    img.src = imageUrl;
    
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
      </div>
    `;
    
    // Esconder controles em caso de erro
    document.getElementById("fotoControlsCompact").style.display = "none";
    
    showToast(`Erro ao carregar foto: ${error.message}`, "error");
  }
}

function downloadFoto(codigo, codigoLeitor, antena, horario) {
  const params = new URLSearchParams({
    codigo_leitor: codigoLeitor,
    antena: antena,
    horario: horario
  });
  const link = document.createElement('a');
  link.href = `/RFID/api/ping/foto/${codigo}?${params}`;
  link.download = `ping_${codigoLeitor}_A${antena}_${codigo}.jpg`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("Download iniciado", "success");
}

function abrirFotoNovaAba(url) {
  window.open(url, '_blank');
}

// Função para navegar entre fotos (anterior/próximo)
async function navegarFoto(codigoAtual, codigoLeitorAtual, antenaAtual, horarioAtual, direcao) {
  try {
    // Buscar dados da tabela atual - ID correto é tabelaCorpo
    const tbody = document.getElementById('tabelaCorpo');
    if (!tbody) {
      showToast("Tabela não encontrada", "error");
      return;
    }
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Encontrar a linha atual
    // Estrutura: [Horário, Código Leitor, Antena, PING Badge, RSSI, Foto, Ações]
    let indiceAtual = -1;
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const horario = row.cells[0]?.getAttribute('data-horario') || row.cells[0]?.textContent.trim();
      const leitor = row.cells[1]?.textContent.trim();
      const antena = row.cells[2]?.querySelector('.antena-badge')?.textContent.trim();
      
      if (leitor === codigoLeitorAtual && antena === antenaAtual && 
          (horario === horarioAtual || new Date(horario).getTime() === new Date(horarioAtual).getTime())) {
        indiceAtual = i;
        break;
      }
    }
    
    if (indiceAtual === -1) {
      showToast("Não foi possível localizar o PING atual na tabela", "warning");
      return;
    }
    
    // Calcular próximo índice
    let proximoIndice;
    if (direcao === 'anterior') {
      proximoIndice = indiceAtual - 1;
      if (proximoIndice < 0) {
        showToast("Este é o primeiro PING da página", "info");
        return;
      }
    } else {
      proximoIndice = indiceAtual + 1;
      if (proximoIndice >= rows.length) {
        showToast("Este é o último PING da página", "info");
        return;
      }
    }
    
    // Obter dados da próxima linha
    const proximaRow = rows[proximoIndice];
    const proximoHorario = proximaRow.cells[0]?.getAttribute('data-horario') || proximaRow.cells[0]?.textContent.trim();
    const proximoLeitor = proximaRow.cells[1]?.textContent.trim();
    const proximaAntena = proximaRow.cells[2]?.querySelector('.antena-badge')?.textContent.trim();
    // Obter código completo do atributo data, não do texto formatado
    const proximoCodigo = proximaRow.cells[3]?.querySelector('.ping-badge')?.getAttribute('data-codigo-completo') || 
                          proximaRow.cells[3]?.querySelector('.ping-badge')?.textContent.trim();
    
    // Carregar foto do próximo PING
    await verFotoPing(proximoCodigo, proximoLeitor, proximaAntena, proximoHorario);
    
  } catch (error) {
    console.error("Erro ao navegar entre fotos:", error);
    showToast(`Erro ao navegar: ${error.message}`, "error");
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

function mostrarErro(mensagem, detalhe = "", isTimeout = false) {
  const emptyState = document.getElementById("emptyState");
  
  // Se for erro de timeout (500), não exibir botão de tentar novamente
  const botaoRetry = isTimeout ? '' : `
    <button class="rfid-btn rfid-btn-primary" onclick="carregarDados()">
        <i class="fas fa-redo"></i> Tentar Novamente
    </button>
  `;
  
  emptyState.innerHTML = `
    <i class="fas fa-exclamation-triangle" style="color: var(--rfid-danger);"></i>
    <h3>Erro ao carregar dados</h3>
    <p>${mensagem}</p>
    ${detalhe ? `<p style="font-size: 0.85rem; color: #6c757d; margin-top: 10px;">${detalhe}</p>` : ""}
    ${botaoRetry}
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
