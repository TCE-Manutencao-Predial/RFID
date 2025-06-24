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

// FUNÇÃO QUE ESTAVA FALTANDO
function aplicarFiltros() {
  paginaAtual = 1; // Resetar para primeira página ao aplicar filtros
  carregarDados();
}

// FUNÇÃO QUE ESTAVA FALTANDO (chamada pelo botão Atualizar)
function atualizarDados() {
  carregarDados(true, true); // force_refresh = true, showToastMessage = true
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

    // Adicionar force_refresh se necessário
    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    const url = `/RFID/api/etiquetas?${params}`;
    //console.log("URL da requisição:", url);

    response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      //console.log("Dados recebidos:", data); // Debug para verificar os dados
      totalRegistros = data.total;
      renderizarTabela(data.etiquetas);
      window.scrollTo(0, lastScrollY); // restaura posição
      atualizarPaginacao();

      if (showToastMessage && data.etiquetas.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${data.etiquetas.length} etiquetas carregadas${cacheInfo}`, "success");
      }
    } else {
      throw new Error(data.error || "Erro ao carregar dados");
    }
  } catch (error) {
    console.error("Erro:", error);
    let errorMessage = "Erro ao carregar os dados";
    let detailMessage = "";

    if (error.message.includes("404")) {
      errorMessage = "API não encontrada. Verifique se o servidor está rodando.";
    } else if (error.message.includes("500")) {
      errorMessage = "Erro interno do servidor.";
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
  //console.log("Valor do filtro status:", status);
  if (status !== "") {
    filtros.destruida = status;
  }

  //console.log("Filtros a serem enviados:", filtros);
  return filtros;
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

    // Determinar status baseado no campo ativa do backend
    let statusBadge;
    let statusTooltip = "";
    let acoesBtns = "";

    // Usar o campo 'ativa' que vem do backend
    if (etiqueta.ativa === false) {
      // Etiqueta destruída
      statusBadge = '<span class="rfid-badge rfid-badge-destroyed">Destruída</span>';
      if (etiqueta.data_destruicao_formatada) {
        statusTooltip = `title="Destruída em ${etiqueta.data_destruicao_formatada}"`;
      }

      // Ações para etiqueta destruída
      acoesBtns = `
                        <button class="rfid-action-btn rfid-action-btn-warning" 
                                onclick="editarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}', '${etiqueta.Descricao || ""}')"
                                title="Editar etiqueta">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="rfid-action-btn rfid-action-btn-success" 
                                onclick="restaurarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}')"
                                title="Restaurar etiqueta">
                            <i class="fas fa-undo"></i> Restaurar
                        </button>
                    `;
    } else {
      // Etiqueta ativa
      statusBadge = '<span class="rfid-badge rfid-badge-active">Ativa</span>';
      statusTooltip = 'title="Etiqueta ativa"';

      // Ações para etiqueta ativa
      acoesBtns = `
                        <button class="rfid-action-btn rfid-action-btn-primary" 
                                onclick="editarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}', '${etiqueta.Descricao || ""}')"
                                title="Editar etiqueta">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="rfid-action-btn rfid-action-btn-danger" 
                                onclick="destruirEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}')"
                                title="Destruir etiqueta">
                            <i class="fas fa-trash"></i> Destruir
                        </button>
                    `;
    }

    tr.innerHTML = `
                    <td><span class="rfid-etiqueta">${etiqueta.EtiquetaRFID_hex || "-"}</span></td>
                    <td>${etiqueta.Descricao || "-"}</td>
                    <td ${statusTooltip}>${statusBadge}</td>
                    <td>
                        <div class="rfid-actions">
                            ${acoesBtns}
                        </div>
                    </td>
                `;

    // Adicionar classe visual para etiquetas destruídas
    if (etiqueta.ativa === false) {
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
  btn.type = "button";             // evita comportamento de submit e foco
  btn.className = "rfid-page-btn";
  btn.textContent = texto;
  btn.disabled = !ativo;
  if (ativo && onclick) {
    btn.addEventListener("click", () => {
      lastScrollY = window.scrollY; // salva posição
      onclick();
      btn.blur();                  // remove foco
    });
  }
  return btn;
}

function mostrarLoading() {
  document.getElementById("loadingState").style.display = "block";
  // NÃO oculta a tabela para não reposicionar o scroll
  // document.getElementById("tabelaEtiquetas").style.display = "none";
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

// Adicionar funções CRUD ao JavaScript existente

// Variável para armazenar dados da foto
let fotoBase64 = null;

// Função para abrir modal de nova etiqueta
function abrirModalNovaEtiqueta() {
  document.getElementById("modalTitulo").textContent = "Nova Etiqueta";
  document.getElementById("formEtiqueta").reset();
  document.getElementById("etiquetaId").value = "";
  document.getElementById("fotoPreview").style.display = "none";
  fotoBase64 = null;
  abrirModal("modalEtiqueta");
}

// Função para abrir modal de edição
function editarEtiqueta(id, codigo, descricao) {
  document.getElementById("modalTitulo").textContent = "Editar Etiqueta";
  document.getElementById("etiquetaId").value = id;
  document.getElementById("etiquetaCodigo").value = codigo;
  document.getElementById("etiquetaDescricao").value = descricao || "";
  document.getElementById("fotoPreview").style.display = "none";
  fotoBase64 = null;
  abrirModal("modalEtiqueta");
}

// Função para abrir modal
function abrirModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.style.display = "block";
  setTimeout(() => modal.classList.add("active"), 10);
}

// Função para fechar modal
function fecharModal(modalId) {
    const modal = document.getElementById(modalId);
    
    // Remover a verificação de dados não salvos para esta função
    // A verificação só deve acontecer quando o usuário clica em Cancelar ou no X
    modal.classList.remove('active');
    setTimeout(() => modal.style.display = 'none', 300);
}

// Nova função específica para cancelar modal (com confirmação)
function cancelarModal(modalId) {
    const modal = document.getElementById(modalId);
    
    if (modalId === 'modalEtiqueta') {
        const codigo = document.getElementById('etiquetaCodigo').value;
        const descricao = document.getElementById('etiquetaDescricao').value;
        
        // Se houver dados não salvos, confirmar antes de fechar
        if ((codigo || descricao) && !document.getElementById('etiquetaId').value) {
            if (!confirm('Há dados não salvos. Deseja realmente fechar?')) {
                return;
            }
        }
    }
    
    fecharModal(modalId);
}

// Preview da foto
function previewFoto(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();

    // Validar tamanho do arquivo (5MB)
    if (input.files[0].size > 5 * 1024 * 1024) {
      showToast("A foto deve ter no máximo 5MB", "error");
      input.value = "";
      return;
    }

    reader.onload = function (e) {
      document.getElementById("fotoPreview").src = e.target.result;
      document.getElementById("fotoPreview").style.display = "block";

      // Extrair apenas a parte base64 (remover o prefixo data:image/...;base64,)
      const base64String = e.target.result.split(",")[1];
      fotoBase64 = base64String;
    };

    reader.readAsDataURL(input.files[0]);
  }
}

// 2. MODIFICAR função para padronizar código RFID com zeros
function padronizarCodigoRFID(codigo) {
    // Remove espaços e converte para maiúsculas
    codigo = codigo.trim().toUpperCase();
    
    // Define o tamanho padrão baseado nos exemplos (24 caracteres)
    const TAMANHO_PADRAO = 24;
    
    // Se o código já tem o tamanho correto, retorna como está
    if (codigo.length >= TAMANHO_PADRAO) {
        return codigo.substring(0, TAMANHO_PADRAO);
    }
    
    // Padrão identificado: AAA0AAAA + zeros + número
    // Vamos verificar se o código segue o padrão inicial
    const padraoInicial = /^[A-Z]{3}[0-9][A-Z]{4}/;
    
    if (padraoInicial.test(codigo)) {
        // Código começa com o padrão correto
        // Preenche com zeros até completar 24 caracteres
        return codigo.padEnd(TAMANHO_PADRAO, '0');
    } else {
        // Verificar se é um código hexadecimal válido (números + letras A-F)
        const hexValido = /^[0-9A-F]+$/;
        
        if (hexValido.test(codigo)) {
            // É um código hexadecimal válido
            const prefixo = 'AAA0AAAA';
            const numeroZeros = TAMANHO_PADRAO - prefixo.length - codigo.length;
            
            if (numeroZeros > 0) {
                // Adiciona zeros à esquerda do código hexadecimal
                return prefixo + '0'.repeat(numeroZeros) + codigo;
            } else {
                // Se o código é muito grande, usa apenas os últimos caracteres
                const tamanhoNumero = TAMANHO_PADRAO - prefixo.length;
                return prefixo + codigo.slice(-tamanhoNumero).padStart(tamanhoNumero, '0');
            }
        }
        
        // Para outros casos, apenas preenche com zeros à direita
        return codigo.padEnd(TAMANHO_PADRAO, '0');
    }
}

// Salvar etiqueta (criar ou editar)
async function salvarEtiqueta(event) {
    event.preventDefault();
    
    const id = document.getElementById('etiquetaId').value;
    let codigo = document.getElementById('etiquetaCodigo').value.trim();
    const descricao = document.getElementById('etiquetaDescricao').value.trim();
    
    if (!codigo) {
        showToast('O código da etiqueta é obrigatório', 'error');
        return;
    }
    
    // APLICAR PADDING DE ZEROS
    codigo = padronizarCodigoRFID(codigo);
    
    // Atualizar o campo visual para mostrar o código completo
    document.getElementById('etiquetaCodigo').value = codigo;
    
    const btnSalvar = document.getElementById('btnSalvarEtiqueta');
    btnSalvar.classList.add('btn-loading');
    btnSalvar.disabled = true;
    
    try {
        let response;
        const dados = {
            EtiquetaRFID_hex: codigo,
            Descricao: descricao
        };
        
        if (fotoBase64) {
            dados.Foto = fotoBase64;
        }
        
        if (id) {
            // Editar etiqueta existente
            response = await fetch(`/RFID/api/etiquetas/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
        } else {
            // Criar nova etiqueta
            response = await fetch('/RFID/api/etiquetas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showToast(
                id ? 'Etiqueta atualizada com sucesso!' : 'Etiqueta criada com sucesso!', 
                'success'
            );
            fecharModal('modalEtiqueta');
            carregarDados(true);
            atualizarEstatisticas();
        } else {
            showToast(result.error || 'Erro ao salvar etiqueta', 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        showToast('Erro ao salvar etiqueta', 'error');
    } finally {
        btnSalvar.classList.remove('btn-loading');
        btnSalvar.disabled = false;
    }
}

// Destruir etiqueta
function destruirEtiqueta(id, codigo) {
  document.getElementById("confirmTitulo").innerHTML = '<i class="fas fa-trash"></i> Destruir Etiqueta';
  document.getElementById("confirmIcon").className = "fas fa-exclamation-triangle";
  document.getElementById("confirmIcon").style.color = "var(--rfid-danger)";
  document.getElementById("confirmMensagem").innerHTML = `Tem certeza que deseja marcar a etiqueta <strong>${codigo}</strong> como destruída?<br>
                 <small>Esta ação pode ser revertida posteriormente.</small>`;

  const btnConfirmar = document.getElementById("btnConfirmar");
  btnConfirmar.className = "rfid-btn rfid-btn-danger";
  btnConfirmar.innerHTML = '<i class="fas fa-trash"></i> Destruir';
  btnConfirmar.onclick = async function () {
    btnConfirmar.classList.add("btn-loading");
    btnConfirmar.disabled = true;

    try {
      const response = await fetch(`/RFID/api/etiquetas/${id}/destruir`, {
        method: "POST",
      });

      const result = await response.json();

      if (result.success) {
        showToast("Etiqueta marcada como destruída", "success");
        fecharModal("modalConfirmacao");
        carregarDados(true);
        atualizarEstatisticas();
      } else {
        showToast(result.error || "Erro ao destruir etiqueta", "error");
      }
    } catch (error) {
      console.error("Erro:", error);
      showToast("Erro ao destruir etiqueta", "error");
    } finally {
      btnConfirmar.classList.remove("btn-loading");
      btnConfirmar.disabled = false;
    }
  };

  abrirModal("modalConfirmacao");
}

// Restaurar etiqueta
function restaurarEtiqueta(id, codigo) {
  document.getElementById("confirmTitulo").innerHTML = '<i class="fas fa-undo"></i> Restaurar Etiqueta';
  document.getElementById("confirmIcon").className = "fas fa-check-circle";
  document.getElementById("confirmIcon").style.color = "var(--rfid-success)";
  document.getElementById("confirmMensagem").innerHTML = `Deseja restaurar a etiqueta <strong>${codigo}</strong>?<br>
                 <small>A etiqueta voltará ao status ativo.</small>`;

  const btnConfirmar = document.getElementById("btnConfirmar");
  btnConfirmar.className = "rfid-btn rfid-btn-success";
  btnConfirmar.innerHTML = '<i class="fas fa-undo"></i> Restaurar';
  btnConfirmar.onclick = async function () {
    btnConfirmar.classList.add("btn-loading");
    btnConfirmar.disabled = true;

    try {
      const response = await fetch(`/RFID/api/etiquetas/${id}/restaurar`, {
        method: "POST",
      });

      const result = await response.json();

      if (result.success) {
        showToast("Etiqueta restaurada com sucesso", "success");
        fecharModal("modalConfirmacao");
        carregarDados(true);
        atualizarEstatisticas();
      } else {
        showToast(result.error || "Erro ao restaurar etiqueta", "error");
      }
    } catch (error) {
      console.error("Erro:", error);
      showToast("Erro ao restaurar etiqueta", "error");
    } finally {
      btnConfirmar.classList.remove("btn-loading");
      btnConfirmar.disabled = false;
    }
  };

  abrirModal("modalConfirmacao");
}

// Atualizar estatísticas
async function atualizarEstatisticas() {
  try {
    const response = await fetch("/RFID/api/estatisticas?force_refresh=true");
    const result = await response.json();

    if (result.success) {
      const stats = result.estatisticas;
      document.getElementById("totalEtiquetas").textContent = stats.total || 0;
      document.getElementById("etiquetasAtivas").textContent = stats.ativas || 0;
      document.getElementById("etiquetasDestruidas").textContent = stats.destruidas || 0;
      document.getElementById("percentualAtivas").textContent = `${stats.percentual_ativas || 0}%`;
    }
  } catch (error) {
    console.error("Erro ao atualizar estatísticas:", error);
  }
}

// Modificar a função renderizarTabela para incluir botões de ação
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

    // Determinar status baseado no campo ativa do backend
    let statusBadge;
    let statusTooltip = "";
    let acoesBtns = "";

    // Usar o campo 'ativa' que vem do backend
    if (etiqueta.ativa === false) {
      // Etiqueta destruída
      statusBadge = '<span class="rfid-badge rfid-badge-destroyed">Destruída</span>';
      if (etiqueta.data_destruicao_formatada) {
        statusTooltip = `title="Destruída em ${etiqueta.data_destruicao_formatada}"`;
      }

      // Ações para etiqueta destruída
      acoesBtns = `
                        <button class="rfid-action-btn rfid-action-btn-warning" 
                                onclick="editarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}', '${etiqueta.Descricao || ""}')"
                                title="Editar etiqueta">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="rfid-action-btn rfid-action-btn-success" 
                                onclick="restaurarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}')"
                                title="Restaurar etiqueta">
                            <i class="fas fa-undo"></i> Restaurar
                        </button>
                    `;
    } else {
      // Etiqueta ativa
      statusBadge = '<span class="rfid-badge rfid-badge-active">Ativa</span>';
      statusTooltip = 'title="Etiqueta ativa"';

      // Ações para etiqueta ativa
      acoesBtns = `
                        <button class="rfid-action-btn rfid-action-btn-primary" 
                                onclick="editarEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}', '${etiqueta.Descricao || ""}')"
                                title="Editar etiqueta">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="rfid-action-btn rfid-action-btn-danger" 
                                onclick="destruirEtiqueta(${etiqueta.id_listaEtiquetasRFID}, '${etiqueta.EtiquetaRFID_hex}')"
                                title="Destruir etiqueta">
                            <i class="fas fa-trash"></i> Destruir
                        </button>
                    `;
    }

    tr.innerHTML = `
                    <td><span class="rfid-etiqueta">${etiqueta.EtiquetaRFID_hex || "-"}</span></td>
                    <td>${etiqueta.Descricao || "-"}</td>
                    <td ${statusTooltip}>${statusBadge}</td>
                    <td>
                        <div class="rfid-actions">
                            ${acoesBtns}
                        </div>
                    </td>
                `;

    // Adicionar classe visual para etiquetas destruídas
    if (etiqueta.ativa === false) {
      tr.classList.add("etiqueta-destruida");
    }

    tbody.appendChild(tr);
  });
}

// Fechar modal ao clicar fora
/*window.onclick = function (event) {
  if (event.target.classList.contains("modal-overlay")) {
    fecharModal(event.target.id);
  }
};*/

// Drag and drop para upload de foto
const uploadArea = document.querySelector(".photo-upload-area");
if (uploadArea) {
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("drag-over");
  });

  uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("drag-over");
  });

  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("drag-over");

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const fileInput = document.getElementById("etiquetaFoto");
      fileInput.files = files;
      previewFoto(fileInput);
    }
  });
}

// Carregar estatísticas ao iniciar
document.addEventListener("DOMContentLoaded", function () {
  atualizarEstatisticas();
});

// 4. MODIFICAR evento para formatar código ao sair do campo
document.addEventListener('DOMContentLoaded', function() {
    const campoCodigoRFID = document.getElementById('etiquetaCodigo');
    
    if (campoCodigoRFID) {
        // Formatar ao sair do campo (blur)
        campoCodigoRFID.addEventListener('blur', function() {
            if (this.value.trim()) {
                this.value = padronizarCodigoRFID(this.value);
            }
        });
        
        // Adicionar placeholder com exemplo
        campoCodigoRFID.placeholder = 'Ex: AAA0AAAA0000000000002808, 2808 ou A1B2';
        
        // Adicionar atributo de tamanho máximo
        campoCodigoRFID.maxLength = 24;
        
        // Adicionar validação em tempo real para aceitar apenas caracteres hexadecimais
        campoCodigoRFID.addEventListener('input', function() {
            // Permitir apenas caracteres hexadecimais (0-9, A-F) e o padrão completo
            const valor = this.value.toUpperCase();
            const hexValido = /^[0-9A-F]*$/;
            const padraoCompleto = /^[A-Z0-9]*$/;
            
            if (!hexValido.test(valor) && !padraoCompleto.test(valor)) {
                // Remove caracteres inválidos
                this.value = valor.replace(/[^0-9A-F]/g, '');
            } else {
                this.value = valor;
            }
        });
    }
});


function navegarPara(secao) {
    switch(secao) {
        case 'etiquetas':
            // Já estamos aqui - poderia recarregar ou não fazer nada
            // window.location.href = '/RFID/';
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
        
        default:
            showToast('Seção não encontrada', 'error');
    }
}

// Adicionar indicador visual para página atual
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar data-tooltip aos botões de navegação
    const navButtons = document.querySelectorAll('.rfid-nav-btn');
    navButtons.forEach(btn => {
        const texto = btn.querySelector('span').textContent;
        btn.setAttribute('data-tooltip', texto);
    });
    
    // Destacar botão da página atual
    const currentPath = window.location.pathname;
    if (currentPath.includes('inventarios')) {
        document.querySelector('.rfid-nav-btn[onclick*="inventarios"]')?.classList.add('active');
    } else if (currentPath.includes('leitores')) {
        document.querySelector('.rfid-nav-btn[onclick*="leitores"]')?.classList.add('active');
    } else if (currentPath.includes('emprestimos')) {
        document.querySelector('.rfid-nav-btn[onclick*="emprestimos"]')?.classList.add('active');
    }
});