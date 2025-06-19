// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 20;
let totalRegistros = 0;

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

  // Auto-remover após 5 segundos
  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  }, 5000);

  // Remover ao clicar
  toast.addEventListener("click", () => {
    toast.style.animation = "slideOut 0.3s ease-out";
    setTimeout(() => toast.remove(), 300);
  });
}

// Inicialização
document.addEventListener("DOMContentLoaded", function () {
  inicializarEventos();
  carregarDados();
});

function inicializarEventos() {
  // Eventos de filtro
  document.getElementById("filtroEtiqueta").addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroDescricao").addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroStatus").addEventListener("change", aplicarFiltros);
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

async function carregarDados(forceRefresh = false, showToastMessage = false) {
  mostrarLoading();
  let response = null; // Declarar response no escopo da função

  try {
    const offset = (paginaAtual - 1) * registrosPorPagina;
    const filtros = obterFiltros();

    // Construir query string
    const params = new URLSearchParams({
      limite: registrosPorPagina,
      offset: offset,
      ...filtros,
    });

    // Adicionar force_refresh se necessário
    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    // IMPORTANTE: URL corrigida com /RFID/api
    response = await fetch(`/RFID/api/etiquetas?${params}`);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      totalRegistros = data.total;
      renderizarTabela(data.etiquetas);
      atualizarPaginacao();

      // Mostrar toast apenas quando solicitado (atualização manual)
      if (showToastMessage && data.etiquetas.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${data.etiquetas.length} etiquetas carregadas${cacheInfo}`, "success");
      }
    } else {
      throw new Error(data.error || "Erro ao carregar dados");
    }
  } catch (error) {
    console.error("Erro:", error);

    // Mensagem de erro mais detalhada
    let errorMessage = "Erro ao carregar os dados";
    let detailMessage = "";

    if (error.message.includes("404")) {
      errorMessage = "API não encontrada. Verifique se o servidor está rodando.";
    } else if (error.message.includes("500")) {
      errorMessage = "Erro interno do servidor.";
      // Tentar obter mais detalhes do erro
      if (response) {
        try {
          const errorData = await response.json();
          if (errorData.error) {
            detailMessage = errorData.error;
          }
        } catch (e) {
          console.error("Erro ao processar resposta de erro:", e);
        }
      }
    } else if (error.message.includes("NetworkError")) {
      errorMessage = "Erro de conexão. Verifique sua internet.";
    } else if (error.message) {
      errorMessage = error.message;
    }

    mostrarErro(errorMessage, detailMessage);
    showToast(detailMessage || errorMessage, "error");
  }
}

function obterFiltros() {
  const filtros = {};

  const etiqueta = document.getElementById("filtroEtiqueta").value.trim();
  if (etiqueta) filtros.etiqueta = etiqueta;

  const descricao = document.getElementById("filtroDescricao").value.trim();
  if (descricao) filtros.descricao = descricao;

  const status = document.getElementById("filtroStatus").value;
  if (status !== "") filtros.destruida = status;

  return filtros;
}

function aplicarFiltros() {
  paginaAtual = 1;
  carregarDados();
}

function atualizarDados() {
  showToast("Atualizando dados do servidor...", "info");
  // Forçar atualização do servidor, ignorando cache
  carregarDados(true, true);
  atualizarEstatisticas(true);
}

async function atualizarEstatisticas(forceRefresh = false) {
  try {
    // Construir URL com parâmetro de força refresh se necessário
    let url = "/RFID/api/estatisticas";
    if (forceRefresh) {
      url += "?force_refresh=true";
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      const stats = data.estatisticas;
      document.getElementById("totalEtiquetas").textContent = stats.total || 0;
      document.getElementById("etiquetasAtivas").textContent = stats.ativas || 0;
      document.getElementById("etiquetasDestruidas").textContent = stats.destruidas || 0;
      document.getElementById("percentualAtivas").textContent = (stats.percentual_ativas || 0) + "%";

      // Mostrar informação de cache apenas em modo debug
      if (forceRefresh && data.from_cache === false) {
        console.log("Estatísticas atualizadas do servidor");
      }
    }
  } catch (error) {
    console.error("Erro ao atualizar estatísticas:", error);
    // Não mostrar toast para erros de estatísticas, apenas log
  }
}

function renderizarTabela(etiquetas) {
  const tbody = document.getElementById("tabelaCorpo");
  const tabela = document.getElementById("tabelaEtiquetas");
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const paginacao = document.getElementById("paginacao");

  loadingState.style.display = "none";

  if (etiquetas.length === 0) {
    tabela.style.display = "none";
    paginacao.style.display = "none";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  tabela.style.display = "table";
  paginacao.style.display = "flex";

  tbody.innerHTML = "";

  etiquetas.forEach((etiqueta) => {
    const tr = document.createElement("tr");

    // Determinar status baseado no campo Destruida
    let statusBadge;
    let statusTooltip = "";
    
    if (etiqueta.Destruida) {
      // Etiqueta destruída - tem data no campo Destruida
      statusBadge = '<span class="rfid-badge rfid-badge-destroyed">Destruída</span>';
      if (etiqueta.data_destruicao_formatada) {
        statusTooltip = `title="Destruída em ${etiqueta.data_destruicao_formatada}"`;
      }
    } else {
      // Etiqueta ativa - campo Destruida é NULL
      statusBadge = '<span class="rfid-badge rfid-badge-active">Ativa</span>';
      statusTooltip = 'title="Etiqueta ativa"';
    }

    tr.innerHTML = `
                    <td><span class="rfid-etiqueta">${etiqueta.EtiquetaRFID_hex || "-"}</span></td>
                    <td>${etiqueta.Descricao || "-"}</td>
                    <td ${statusTooltip}>${statusBadge}</td>
                `;

    // Adicionar classe visual para etiquetas destruídas
    if (etiqueta.Destruida) {
      tr.classList.add("etiqueta-destruida");
    }

    tbody.appendChild(tr);
  });
}

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
    carregarDados(); // Sem toast na paginação
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
      carregarDados(); // Sem toast na paginação
    });

    if (i === paginaAtual) {
      btn.classList.add("active");
    }

    controles.appendChild(btn);
  }

  // Botão Próximo
  const btnProximo = criarBotaoPagina("Próximo", paginaAtual < totalPaginas, () => {
    paginaAtual++;
    carregarDados(); // Sem toast na paginação
  });
  controles.appendChild(btnProximo);
}

function criarBotaoPagina(texto, ativo, onclick) {
  const btn = document.createElement("button");
  btn.className = "rfid-page-btn";
  btn.textContent = texto;
  btn.disabled = !ativo;
  if (ativo && onclick) {
    btn.addEventListener("click", onclick);
  }
  return btn;
}

function mostrarLoading() {
  document.getElementById("loadingState").style.display = "block";
  document.getElementById("tabelaEtiquetas").style.display = "none";
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
  document.getElementById("tabelaEtiquetas").style.display = "none";
}

function exportarDados() {
  showToast("Funcionalidade de exportação será implementada em breve!", "info");
}
