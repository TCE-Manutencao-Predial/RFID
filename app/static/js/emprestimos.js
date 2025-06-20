// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 20;
let totalRegistros = 0;
let etiquetaVerificada = false;

// Sistema de Toast (reutilizado do etiquetas.js)
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
  atualizarEstatisticas();
});

function inicializarEventos() {
  // Eventos de filtro
  document.getElementById("filtroColaborador").addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroEtiqueta").addEventListener("input", debounce(aplicarFiltros, 500));
  document.getElementById("filtroStatus").addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataInicio").addEventListener("change", aplicarFiltros);
  document.getElementById("filtroDataFim").addEventListener("change", aplicarFiltros);

  // Formatar código RFID ao sair do campo
  const campoEtiqueta = document.getElementById("emprestimoEtiqueta");
  if (campoEtiqueta) {
    campoEtiqueta.addEventListener("blur", function () {
      if (this.value.trim()) {
        this.value = padronizarCodigoRFID(this.value);
      }
    });
  }
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

function atualizarDados() {
  carregarDados(true, true);
}

// Padronizar código RFID (reutilizado do etiquetas.js)
function padronizarCodigoRFID(codigo) {
  codigo = codigo.trim().toUpperCase();
  const TAMANHO_PADRAO = 24;

  if (codigo.length >= TAMANHO_PADRAO) {
    return codigo.substring(0, TAMANHO_PADRAO);
  }

  const padraoInicial = /^[A-Z]{3}[0-9][A-Z]{4}/;

  if (padraoInicial.test(codigo)) {
    return codigo.padEnd(TAMANHO_PADRAO, "0");
  } else {
    if (/^\d+$/.test(codigo)) {
      const prefixo = "AAA0AAAA";
      const numeroZeros = TAMANHO_PADRAO - prefixo.length - codigo.length;

      if (numeroZeros > 0) {
        return prefixo + "0".repeat(numeroZeros) + codigo;
      } else {
        const tamanhoNumero = TAMANHO_PADRAO - prefixo.length;
        return prefixo + codigo.slice(-tamanhoNumero).padStart(tamanhoNumero, "0");
      }
    }

    return codigo.padEnd(TAMANHO_PADRAO, "0");
  }
}

async function carregarDados(forceRefresh = false, showToastMessage = false) {
  mostrarLoading();
  let response = null;

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

    const url = `/RFID/api/emprestimos?${params}`;
    response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      totalRegistros = data.total;
      renderizarTabela(data.emprestimos);
      atualizarPaginacao();

      if (showToastMessage && data.emprestimos.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${data.emprestimos.length} empréstimos carregados${cacheInfo}`, "success");
      }
    } else {
      throw new Error(data.error || "Erro ao carregar dados");
    }
  } catch (error) {
    console.error("Erro:", error);
    let errorMessage = "Erro ao carregar os dados";

    if (error.message.includes("404")) {
      errorMessage = "API não encontrada. Verifique se o servidor está rodando.";
    } else if (error.message.includes("500")) {
      errorMessage = "Erro interno do servidor.";
    } else if (error.message) {
      errorMessage = error.message;
    }

    mostrarErro(errorMessage);
    showToast(errorMessage, "error");
  }
}

function obterFiltros() {
  const filtros = {};

  const colaborador = document.getElementById("filtroColaborador").value.trim();
  if (colaborador) filtros.id_colaborador = colaborador;

  const etiqueta = document.getElementById("filtroEtiqueta").value.trim();
  if (etiqueta) filtros.etiqueta = etiqueta;

  const status = document.getElementById("filtroStatus").value;
  if (status) filtros.status = status;

  const dataInicio = document.getElementById("filtroDataInicio").value;
  if (dataInicio) filtros.data_inicio = dataInicio;

  const dataFim = document.getElementById("filtroDataFim").value;
  if (dataFim) filtros.data_fim = dataFim;

  return filtros;
}

function renderizarTabela(emprestimos) {
  const tbody = document.getElementById("tabelaCorpo");
  const tabela = document.getElementById("tabelaEmprestimos");
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const paginacao = document.getElementById("paginacao");

  loadingState.style.display = "none";

  if (emprestimos.length === 0) {
    tabela.style.display = "none";
    paginacao.style.display = "none";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  tabela.style.display = "table";
  paginacao.style.display = "flex";

  tbody.innerHTML = "";

  emprestimos.forEach((emprestimo) => {
    const tr = document.createElement("tr");

    // Determinar status e ações
    let statusBadge;
    let acoesBtns = "";

    if (emprestimo.status === "ativo") {
      tr.classList.add("emprestimo-ativo");
      statusBadge = '<span class="rfid-badge rfid-badge-active">Em Empréstimo</span>';

      // Calcular tempo decorrido
      const tempoDecorrido = calcularTempoDecorrido(emprestimo.dataEmprestimo);

      acoesBtns = `
        <button class="rfid-action-btn rfid-action-btn-return" 
                onclick="abrirModalDevolucao(${emprestimo.id}, ${emprestimo.id_colaborador}, '${emprestimo.EtiquetaRFID_hex}', '${emprestimo.descricao_ferramenta || ""}', '${emprestimo.dataEmprestimo_formatada}')"
                title="Registrar devolução">
            <i class="fas fa-undo"></i> Devolver
        </button>
      `;
    } else {
      tr.classList.add("emprestimo-devolvido");
      statusBadge = '<span class="rfid-badge rfid-badge-destroyed">Devolvido</span>';

      acoesBtns = `
        <button class="rfid-action-btn rfid-action-btn-primary" 
                onclick="visualizarDetalhes(${emprestimo.id})"
                title="Ver detalhes">
            <i class="fas fa-eye"></i> Detalhes
        </button>
      `;
    }

    // Adicionar botão de histórico
    acoesBtns += `
      <button class="historico-btn" 
              onclick="verHistoricoFerramenta('${emprestimo.EtiquetaRFID_hex}')"
              title="Ver histórico da ferramenta">
          <i class="fas fa-history"></i>
      </button>
    `;

    tr.innerHTML = `
      <td>${emprestimo.id}</td>
      <td>${emprestimo.id_colaborador}</td>
      <td>
        <span class="rfid-etiqueta">${emprestimo.EtiquetaRFID_hex}</span>
        <br>
        <small>${emprestimo.descricao_ferramenta || "-"}</small>
      </td>
      <td class="date-cell">${emprestimo.dataEmprestimo_formatada || "-"}</td>
      <td class="date-cell">${emprestimo.dataDevolucao_formatada || "-"}</td>
      <td>${statusBadge}</td>
      <td>
        <div class="rfid-actions">
            ${acoesBtns}
        </div>
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function calcularTempoDecorrido(dataEmprestimo) {
  const agora = new Date();
  let dataEmp;

  if (typeof dataEmprestimo === "string") {
    dataEmp = new Date(dataEmprestimo);
  } else {
    dataEmp = dataEmprestimo;
  }

  const diff = agora - dataEmp;
  const dias = Math.floor(diff / (1000 * 60 * 60 * 24));
  const horas = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

  if (dias > 0) {
    return { texto: `${dias} dia(s) e ${horas} hora(s)`, alerta: dias > 7 };
  } else {
    return { texto: `${horas} hora(s)`, alerta: false };
  }
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

let lastScrollY = 0;

function criarBotaoPagina(texto, ativo, onclick) {
  const btn = document.createElement("button");
  btn.type = "button";
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

function mostrarErro(mensagem) {
  const emptyState = document.getElementById("emptyState");
  emptyState.innerHTML = `
    <i class="fas fa-exclamation-triangle" style="color: var(--rfid-danger);"></i>
    <h3>Erro ao carregar dados</h3>
    <p>${mensagem}</p>
    <button class="rfid-btn rfid-btn-primary" onclick="carregarDados()">
        <i class="fas fa-redo"></i> Tentar Novamente
    </button>
  `;
  emptyState.style.display = "block";
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("tabelaEmprestimos").style.display = "none";
}

// Modais
function abrirModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.style.display = "block";
  setTimeout(() => modal.classList.add("active"), 10);
}

function fecharModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.remove("active");
  setTimeout(() => modal.style.display = "none", 300);

  // Limpar formulários ao fechar
  if (modalId === "modalEmprestimo") {
    document.getElementById("formEmprestimo").reset();
    document.getElementById("disponibilidadeInfo").style.display = "none";
    etiquetaVerificada = false;
  }
}

// Novo Empréstimo
function abrirModalNovoEmprestimo() {
  document.getElementById("modalTitulo").textContent = "Novo Empréstimo";
  document.getElementById("formEmprestimo").reset();
  document.getElementById("disponibilidadeInfo").style.display = "none";
  etiquetaVerificada = false;
  abrirModal("modalEmprestimo");
}

async function verificarDisponibilidade() {
  let etiqueta = document.getElementById("emprestimoEtiqueta").value.trim();

  if (!etiqueta) {
    showToast("Digite o código da etiqueta", "warning");
    return;
  }

  // Padronizar código
  etiqueta = padronizarCodigoRFID(etiqueta);
  document.getElementById("emprestimoEtiqueta").value = etiqueta;

  const btnVerificar = document.querySelector(".btn-check-availability");
  btnVerificar.disabled = true;
  btnVerificar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando...';

  try {
    const response = await fetch(`/RFID/api/emprestimos/ferramenta/${etiqueta}/disponibilidade`);
    const data = await response.json();

    const infoDiv = document.getElementById("disponibilidadeInfo");

    if (data.success && data.disponivel) {
      infoDiv.className = "availability-info disponivel";
      infoDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <strong>Disponível!</strong> ${data.descricao || "Ferramenta sem descrição"}
      `;
      etiquetaVerificada = true;
    } else if (data.success && !data.disponivel) {
      infoDiv.className = "availability-info indisponivel";
      let mensagem = `<i class="fas fa-times-circle"></i> <strong>${data.motivo}</strong>`;

      if (data.emprestimo_ativo) {
        mensagem += `<br>Emprestada para colaborador ${data.emprestimo_ativo.id_colaborador} desde ${data.emprestimo_ativo.data_emprestimo}`;
      }

      infoDiv.innerHTML = mensagem;
      etiquetaVerificada = false;
    } else {
      infoDiv.className = "availability-info aviso";
      infoDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        ${data.error || "Erro ao verificar disponibilidade"}
      `;
      etiquetaVerificada = false;
    }

    infoDiv.style.display = "block";
  } catch (error) {
    showToast("Erro ao verificar disponibilidade", "error");
    console.error(error);
  } finally {
    btnVerificar.disabled = false;
    btnVerificar.innerHTML = '<i class="fas fa-search"></i> Verificar';
  }
}

async function salvarEmprestimo(event) {
  event.preventDefault();

  const colaborador = document.getElementById("emprestimoColaborador").value.trim();
  let etiqueta = document.getElementById("emprestimoEtiqueta").value.trim();
  const observacao = document.getElementById("emprestimoObservacao").value.trim();

  if (!colaborador || !etiqueta) {
    showToast("Preencha todos os campos obrigatórios", "error");
    return;
  }

  // Padronizar código
  etiqueta = padronizarCodigoRFID(etiqueta);

  const btnSalvar = document.getElementById("btnSalvarEmprestimo");
  btnSalvar.classList.add("btn-loading");
  btnSalvar.disabled = true;

  try {
    const response = await fetch("/RFID/api/emprestimos", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        id_colaborador: parseInt(colaborador),
        EtiquetaRFID_hex: etiqueta,
        Observacao: observacao,
      }),
    });

    const result = await response.json();

    if (result.success) {
      showToast("Empréstimo registrado com sucesso!", "success");
      fecharModal("modalEmprestimo");
      carregarDados(true);
      atualizarEstatisticas();
    } else {
      showToast(result.error || "Erro ao registrar empréstimo", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    showToast("Erro ao registrar empréstimo", "error");
  } finally {
    btnSalvar.classList.remove("btn-loading");
    btnSalvar.disabled = false;
  }
}

// Devolução
function abrirModalDevolucao(id, colaborador, etiqueta, descricao, dataEmprestimo) {
  document.getElementById("devolucaoId").value = id;
  document.getElementById("devolucaoColaborador").textContent = colaborador;
  document.getElementById("devolucaoFerramenta").textContent = `${etiqueta} - ${descricao || "Sem descrição"}`;
  document.getElementById("devolucaoDataEmprestimo").textContent = dataEmprestimo;

  // Calcular tempo decorrido
  const tempo = calcularTempoDecorrido(dataEmprestimo.split(" às ")[0]);
  const spanTempo = document.getElementById("devolucaoTempo");
  spanTempo.textContent = tempo.texto;
  if (tempo.alerta) {
    spanTempo.classList.add("tempo-alerta");
  } else {
    spanTempo.classList.remove("tempo-alerta");
  }

  abrirModal("modalDevolucao");
}

async function confirmarDevolucao(event) {
  event.preventDefault();

  const id = document.getElementById("devolucaoId").value;
  const observacao = document.getElementById("devolucaoObservacao").value.trim();

  const btnConfirmar = document.getElementById("btnConfirmarDevolucao");
  btnConfirmar.classList.add("btn-loading");
  btnConfirmar.disabled = true;

  try {
    const response = await fetch(`/RFID/api/emprestimos/${id}/devolver`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        observacao_devolucao: observacao,
      }),
    });

    const result = await response.json();

    if (result.success) {
      showToast("Devolução registrada com sucesso!", "success");
      fecharModal("modalDevolucao");
      carregarDados(true);
      atualizarEstatisticas();
    } else {
      showToast(result.error || "Erro ao registrar devolução", "error");
    }
  } catch (error) {
    console.error("Erro:", error);
    showToast("Erro ao registrar devolução", "error");
  } finally {
    btnConfirmar.classList.remove("btn-loading");
    btnConfirmar.disabled = false;
  }
}

// Empréstimos Pendentes
async function abrirModalPendentes() {
  abrirModal("modalPendentes");

  const loadingDiv = document.getElementById("loadingPendentes");
  const listaDiv = document.getElementById("listaPendentes");

  loadingDiv.style.display = "block";
  listaDiv.innerHTML = "";

  try {
    const response = await fetch("/RFID/api/emprestimos/pendentes");
    const data = await response.json();

    loadingDiv.style.display = "none";

    if (data.success && data.emprestimos.length > 0) {
      data.emprestimos.forEach((emp) => {
        const tempo = calcularTempoDecorrido(emp.dataEmprestimo);
        const card = document.createElement("div");
        card.className = `pendente-card ${tempo.alerta ? "alerta" : ""}`;

        card.innerHTML = `
          <div class="pendente-icon">
            <i class="fas fa-tools"></i>
          </div>
          <div class="pendente-info">
            <h4>${emp.descricao_ferramenta || "Ferramenta sem descrição"}</h4>
            <div class="pendente-details">
              <div class="pendente-detail">
                <strong>Colaborador:</strong> ${emp.id_colaborador}
              </div>
              <div class="pendente-detail">
                <strong>Etiqueta:</strong> ${emp.EtiquetaRFID_hex}
              </div>
              <div class="pendente-detail">
                <strong>Tempo:</strong> <span class="${tempo.alerta ? "tempo-alerta" : ""}">${tempo.texto}</span>
              </div>
              <div class="pendente-detail">
                <strong>Data:</strong> ${emp.dataEmprestimo_formatada}
              </div>
            </div>
          </div>
          <div class="pendente-actions">
            <button class="rfid-btn rfid-btn-success" 
                    onclick="fecharModal('modalPendentes'); abrirModalDevolucao(${emp.id}, ${emp.id_colaborador}, '${emp.EtiquetaRFID_hex}', '${emp.descricao_ferramenta || ""}', '${emp.dataEmprestimo_formatada}')">
              <i class="fas fa-undo"></i> Devolver
            </button>
          </div>
        `;

        listaDiv.appendChild(card);
      });
    } else {
      listaDiv.innerHTML = `
        <div class="rfid-empty">
          <i class="fas fa-check-circle"></i>
          <h3>Nenhum empréstimo pendente</h3>
          <p>Todas as ferramentas foram devolvidas</p>
        </div>
      `;
    }
  } catch (error) {
    console.error("Erro:", error);
    loadingDiv.style.display = "none";
    listaDiv.innerHTML = `
      <div class="rfid-empty">
        <i class="fas fa-exclamation-triangle"></i>
        <h3>Erro ao carregar pendentes</h3>
        <p>Tente novamente mais tarde</p>
      </div>
    `;
  }
}

// Estatísticas
async function atualizarEstatisticas() {
  try {
    const response = await fetch("/RFID/api/emprestimos/estatisticas?force_refresh=true");
    const result = await response.json();

    if (result.success) {
      const stats = result.estatisticas;
      document.getElementById("totalEmprestimos").textContent = stats.total_emprestimos || 0;
      document.getElementById("emprestimosAtivos").textContent = stats.emprestimos_ativos || 0;
      document.getElementById("emprestimosDevolvidos").textContent = stats.emprestimos_devolvidos || 0;
      document.getElementById("percentualAtivos").textContent = `${stats.percentual_ativos || 0}%`;
    }
  } catch (error) {
    console.error("Erro ao atualizar estatísticas:", error);
  }
}

// Funções auxiliares
function visualizarDetalhes(id) {
  showToast("Funcionalidade de detalhes será implementada em breve!", "info");
}

function verHistoricoFerramenta(etiqueta) {
  showToast(`Histórico da ferramenta ${etiqueta} será implementado em breve!`, "info");
}

function exportarDados() {
  showToast("Funcionalidade de exportação será implementada em breve!", "info");
}

// Navegação
function navegarPara(secao) {
  switch (secao) {
    case "etiquetas":
      window.location.href = "/RFID/";
      break;

    case "inventarios":
      window.location.href = "/RFID/inventarios";
      break;

    case "leitores":
      window.location.href = "/RFID/leitores";
      break;

    case "emprestimos":
      // Já estamos aqui
      break;

    default:
      showToast("Seção não encontrada", "error");
  }
}

// Adicionar indicador visual para página atual
document.addEventListener("DOMContentLoaded", function () {
  // Adicionar data-tooltip aos botões de navegação
  const navButtons = document.querySelectorAll(".rfid-nav-btn");
  navButtons.forEach((btn) => {
    const texto = btn.querySelector("span").textContent;
    btn.setAttribute("data-tooltip", texto);
  });
});