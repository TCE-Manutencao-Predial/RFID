// Variáveis globais
let paginaAtual = 1;
const registrosPorPagina = 20;
let totalRegistros = 0;
let etiquetaVerificada = false;

// Cache de funcionários
let cacheFuncionarios = new Map();
let cacheTimestamp = null;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutos

/**
 * Formata código de etiqueta RFID removendo prefixos conhecidos
 * Mantém o código original intacto em data-attributes para edição
 * @param {string} codigoRFID - Código completo da etiqueta
 * @returns {string} - Código formatado para visualização
 */
function formatarEtiquetaRFID(codigoRFID) {
  if (!codigoRFID) return "-";
  
  const codigo = codigoRFID.toUpperCase();
  
  // Padrões conhecidos (ordenados do mais específico ao mais genérico)
  const padroes = [
    // Padrão: AAA0AAAA seguido de zeros e sufixo
    { regex: /^[A-F0-9]{8}0+([A-F0-9]{4,})$/, grupo: 1 },
    // Padrão: 32366259FC0000400000 seguido de sufixo
    { regex: /^32366259FC0{4}40{4}([A-F0-9]{4,})$/i, grupo: 1 },
    // Padrão: 6170617200000000 seguido de sufixo
    { regex: /^61706172(0{8,})([A-F0-9]{4,})$/i, grupo: 2 },
    // Padrão: zeros seguidos de sufixo (pelo menos 4 dígitos)
    { regex: /^0+([A-F0-9]{4,})$/, grupo: 1 },
  ];
  
  // Tentar cada padrão
  for (const padrao of padroes) {
    const match = codigo.match(padrao.regex);
    if (match && match[padrao.grupo]) {
      return match[padrao.grupo];
    }
  }
  
  // Se não corresponder a nenhum padrão, retornar o código completo
  return codigoRFID;
}

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
  carregarFuncionarios(); // Carregar funcionários no cache
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

  // Busca de ferramentas
  const campoBusca = document.getElementById("buscaFerramenta");
  if (campoBusca) {
    campoBusca.addEventListener("input", debounce(buscarFerramentas, 300));
    campoBusca.addEventListener("focus", function() {
      if (this.value.trim().length >= 2) {
        buscarFerramentas();
      }
    });
  }

  // Busca de colaboradores
  const campoBuscaColaborador = document.getElementById("buscaColaborador");
  if (campoBuscaColaborador) {
    campoBuscaColaborador.addEventListener("input", debounce(buscarColaboradores, 300));
    campoBuscaColaborador.addEventListener("focus", function() {
      if (this.value.trim().length >= 2) {
        buscarColaboradores();
      }
    });
  }
  
  // Fechar sugestões ao clicar fora
  document.addEventListener("click", function(e) {
    if (!e.target.closest(".search-container")) {
      document.getElementById("sugestoesFerramenta").classList.remove("show");
      document.getElementById("sugestoesColaborador").classList.remove("show");
    }
  });
}

// Funções de API de Funcionários
async function carregarFuncionarios(forceRefresh = false) {
  // Verificar se o cache ainda é válido
  if (!forceRefresh && cacheFuncionarios.size > 0 && cacheTimestamp && 
      (Date.now() - cacheTimestamp < CACHE_DURATION)) {
    return;
  }

  try {
    const response = await fetch('https://automacao.tce.go.gov.br/checklistpredial/api/funcionarios/listar');
    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();
    if (data.success) {
      // Limpar cache antigo
      cacheFuncionarios.clear();
      
      // Popular cache com mapeamento ID -> dados do funcionário
      data.funcionarios.forEach(func => {
        cacheFuncionarios.set(func.id, {
          id: func.id,
          nome: func.nome,
          empresa: func.empresa
        });
      });
      
      cacheTimestamp = Date.now();
      console.log(`Cache de funcionários atualizado: ${cacheFuncionarios.size} registros`);
    }
  } catch (error) {
    console.error("Erro ao carregar funcionários:", error);
    // Não mostrar toast aqui para não poluir a interface
  }
}

function obterNomeFuncionario(idColaborador) {
  const funcionario = cacheFuncionarios.get(parseInt(idColaborador));
  if (funcionario) {
    return `${funcionario.nome} (${funcionario.empresa})`;
  }
  return `ID: ${idColaborador}`;
}

async function buscarColaboradores() {
  const termo = document.getElementById("buscaColaborador").value.trim();
  const sugestoesDiv = document.getElementById("sugestoesColaborador");
  
  if (termo.length < 2) {
    sugestoesDiv.classList.remove("show");
    return;
  }
  
  try {
    const response = await fetch(`https://automacao.tce.go.gov.br/checklistpredial/api/funcionarios/buscar?nome=${encodeURIComponent(termo)}`);
    const data = await response.json();
    
    if (data.success && data.funcionarios.length > 0) {
      sugestoesDiv.innerHTML = "";
      
      // Limitar a 10 sugestões
      const funcionarios = data.funcionarios.slice(0, 10);
      
      funcionarios.forEach(func => {
        const item = document.createElement("div");
        item.className = "suggestion-item";
        item.innerHTML = `
          <div class="etiqueta-codigo">${func.nome}</div>
          <div class="etiqueta-descricao">${func.empresa}</div>
        `;
        
        item.addEventListener("click", function() {
          selecionarColaborador(func.id, func.nome, func.empresa);
        });
        
        sugestoesDiv.appendChild(item);
      });
      
      sugestoesDiv.classList.add("show");
    } else {
      sugestoesDiv.innerHTML = '<div class="no-results">Nenhum colaborador encontrado</div>';
      sugestoesDiv.classList.add("show");
    }
  } catch (error) {
    console.error("Erro ao buscar colaboradores:", error);
    sugestoesDiv.classList.remove("show");
  }
}

function selecionarColaborador(id, nome, empresa) {
  // Preencher o campo hidden com o ID
  document.getElementById("emprestimoColaborador").value = id;
  
  // Mostrar informações do colaborador selecionado
  const box = document.getElementById("colaboradorSelecionado");
  box.textContent = `${nome} - ${empresa}`;
  box.classList.add("show");
  
  // Limpar busca e esconder sugestões
  document.getElementById("buscaColaborador").value = "";
  document.getElementById("sugestoesColaborador").classList.remove("show");
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
  carregarFuncionarios(true); // Atualizar cache de funcionários
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
    
    // Guardar o filtro de colaborador para aplicar no frontend
    const filtroColaboradorTexto = document.getElementById("filtroColaborador").value.trim();

    const params = new URLSearchParams({
      limite: registrosPorPagina,
      offset: offset,
    });

    // Adicionar outros filtros (exceto colaborador que será filtrado no frontend)
    if (filtros.etiqueta) params.append('etiqueta', filtros.etiqueta);
    if (filtros.status) params.append('status', filtros.status);
    if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params.append('data_fim', filtros.data_fim);

    if (forceRefresh) {
      params.append("force_refresh", "true");
    }

    // Se há filtro de colaborador, buscar mais registros para compensar a filtragem no frontend
    if (filtroColaboradorTexto) {
      params.set('limite', registrosPorPagina * 5); // Buscar 5x mais registros
    }

    const url = `/RFID/api/emprestimos?${params}`;
    response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      let emprestimos = data.emprestimos;
      
      // Aplicar filtro de colaborador no frontend se necessário
      if (filtroColaboradorTexto) {
        const textoBusca = filtroColaboradorTexto.toLowerCase();
        
        emprestimos = emprestimos.filter(emp => {
          const funcionario = cacheFuncionarios.get(parseInt(emp.id_colaborador));
          if (!funcionario) return false;
          
          const nomeCompleto = `${funcionario.nome} ${funcionario.empresa}`.toLowerCase();
          
          return funcionario.nome.toLowerCase().includes(textoBusca) || 
                 funcionario.empresa.toLowerCase().includes(textoBusca) ||
                 nomeCompleto.includes(textoBusca);
        });
        
        // Ajustar total de registros
        totalRegistros = emprestimos.length;
        
        // Aplicar paginação manualmente
        const inicio = (paginaAtual - 1) * registrosPorPagina;
        emprestimos = emprestimos.slice(inicio, inicio + registrosPorPagina);
      } else {
        totalRegistros = data.total;
      }
      
      renderizarTabela(emprestimos);
      atualizarPaginacao();

      if (showToastMessage && emprestimos.length > 0) {
        const cacheInfo = data.from_cache ? " (do cache)" : " (atualizado)";
        showToast(`${emprestimos.length} empréstimos carregados${cacheInfo}`, "success");
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

  // Nota: o filtro de colaborador será aplicado no frontend
  // por isso não é adicionado aqui

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

    // Obter nome do colaborador
    const nomeColaborador = obterNomeFuncionario(emprestimo.id_colaborador);

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
      <td title="${nomeColaborador}">${nomeColaborador}</td>
      <td>
        <span class="rfid-etiqueta" 
              data-codigo-completo="${emprestimo.EtiquetaRFID_hex}"
              title="Código completo: ${emprestimo.EtiquetaRFID_hex}">
          ${formatarEtiquetaRFID(emprestimo.EtiquetaRFID_hex)}
        </span>
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

  // Log para debug
  console.log("Data original:", dataEmprestimo);

  if (typeof dataEmprestimo === "string") {
    // Remover " às " se existir e tratar diferentes formatos
    const dataLimpa = dataEmprestimo.replace(" às ", " ");
    
    // Tentar diferentes formatos de data
    // Formato brasileiro: DD/MM/YYYY HH:MM
    if (dataLimpa.includes("/")) {
      const [dataParte, horaParte] = dataLimpa.split(" ");
      const [dia, mes, ano] = dataParte.split("/");
      const dataFormatada = `${ano}-${mes}-${dia}${horaParte ? ' ' + horaParte : ''}`;
      dataEmp = new Date(dataFormatada);
    } else {
      // Formato ISO ou americano
      dataEmp = new Date(dataLimpa);
    }
  } else {
    dataEmp = dataEmprestimo;
  }

  // Verificar se a data é válida
  if (isNaN(dataEmp.getTime())) {
    console.error("Data inválida:", dataEmprestimo);
    return { texto: "Tempo indisponível", alerta: false };
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
    document.getElementById("colaboradorSelecionado").textContent = "";
    document.getElementById("colaboradorSelecionado").classList.remove("show");
    etiquetaVerificada = false;
  }
}

// Novo Empréstimo
function abrirModalNovoEmprestimo() {
  document.getElementById("formEmprestimo").reset();
  document.getElementById("ferramentaSelecionada").classList.remove("show");
  document.getElementById("sugestoesFerramenta").classList.remove("show");
  document.getElementById("sugestoesColaborador").classList.remove("show");
  // limpar as divs selecionadas
  document.getElementById("codigoSelecionado").textContent = "";
  document.getElementById("colaboradorSelecionado").textContent = "";
  document.getElementById("colaboradorSelecionado").classList.remove("show");
  etiquetaVerificada = false;
  abrirModal("modalEmprestimo");
}

async function verificarDisponibilidade() {
  const etiqueta = document.getElementById("emprestimoEtiqueta").value.trim();

  if (!etiqueta) {
    showToast("Selecione uma ferramenta primeiro", "warning");
    return;
  }

  try {
    const response = await fetch(`/RFID/api/emprestimos/ferramenta/${etiqueta}/disponibilidade`);
    const data = await response.json();

    const infoDiv = document.getElementById("disponibilidadeInfo");

    if (data.success && data.disponivel) {
      infoDiv.className = "availability-info disponivel";
      infoDiv.innerHTML = `<i class="fas fa-check-circle"></i> Disponível para empréstimo`;
      etiquetaVerificada = true;
    } else if (data.success && !data.disponivel) {
      infoDiv.className = "availability-info indisponivel";
      let mensagem = `<i class="fas fa-times-circle"></i> ${data.motivo}`;

      if (data.emprestimo_ativo) {
        // Buscar nome do colaborador
        const nomeColaborador = obterNomeFuncionario(data.emprestimo_ativo.id_colaborador);
        mensagem += ` (${nomeColaborador})`;
      }

      infoDiv.innerHTML = mensagem;
      etiquetaVerificada = false;
    } else {
      infoDiv.className = "availability-info aviso";
      infoDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${data.error || "Erro ao verificar"}`;
      etiquetaVerificada = false;
    }

    infoDiv.style.display = "block";
  } catch (error) {
    showToast("Erro ao verificar disponibilidade", "error");
    console.error(error);
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
  
  // Buscar nome do colaborador
  const nomeColaborador = obterNomeFuncionario(colaborador);
  document.getElementById("devolucaoColaborador").textContent = nomeColaborador;
  
  document.getElementById("devolucaoFerramenta").textContent = `${etiqueta} - ${descricao || "Sem descrição"}`;
  document.getElementById("devolucaoDataEmprestimo").textContent = dataEmprestimo;

  // Calcular tempo decorrido - extrair apenas a data se vier com " às "
  let dataParaCalculo = dataEmprestimo;
  if (dataEmprestimo.includes(" às ")) {
    // Se vier no formato "DD/MM/YYYY às HH:MM", usar a string completa
    dataParaCalculo = dataEmprestimo;
  }
  
  const tempo = calcularTempoDecorrido(dataParaCalculo);
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
        const nomeColaborador = obterNomeFuncionario(emp.id_colaborador);
        
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
                <strong>Colaborador:</strong> ${nomeColaborador}
              </div>
              <div class="pendente-detail">
                <strong>Etiqueta:</strong> 
                <span title="${emp.EtiquetaRFID_hex}">${formatarEtiquetaRFID(emp.EtiquetaRFID_hex)}</span>
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
async function visualizarDetalhes(id) {
  try {
    // Buscar o empréstimo específico
    const response = await fetch(`/RFID/api/emprestimos?limite=1&offset=0`);
    const data = await response.json();
    
    if (data.success) {
      // Encontrar o empréstimo pelo ID
      const emprestimo = data.emprestimos.find(e => e.id === id);
      
      if (emprestimo) {
        // Criar modal de detalhes
        const modalHtml = `
          <div class="modal-overlay" id="modalDetalhes" style="display: block;">
            <div class="modal">
              <div class="modal-header">
                <h3 class="modal-title">
                  <i class="fas fa-info-circle"></i>
                  Detalhes do Empréstimo #${emprestimo.id}
                </h3>
                <button class="modal-close" onclick="document.getElementById('modalDetalhes').remove()">
                  <i class="fas fa-times"></i>
                </button>
              </div>
              <div class="modal-body">
                <div class="info-devolucao">
                  <p><strong>ID do Empréstimo:</strong> ${emprestimo.id}</p>
                  <p><strong>Colaborador:</strong> ${obterNomeFuncionario(emprestimo.id_colaborador)}</p>
                  <p><strong>Ferramenta:</strong> 
                    <span title="${emprestimo.EtiquetaRFID_hex}">${formatarEtiquetaRFID(emprestimo.EtiquetaRFID_hex)}</span>
                  </p>
                  <p><strong>Descrição:</strong> ${emprestimo.descricao_ferramenta || "Sem descrição"}</p>
                  <p><strong>Data do Empréstimo:</strong> ${emprestimo.dataEmprestimo_formatada}</p>
                  <p><strong>Data da Devolução:</strong> ${emprestimo.dataDevolucao_formatada || "Não devolvido"}</p>
                  <p><strong>Status:</strong> ${emprestimo.status === 'ativo' ? 'Em Empréstimo' : 'Devolvido'}</p>
                  ${emprestimo.Observacao ? `<p><strong>Observações:</strong> ${emprestimo.Observacao}</p>` : ''}
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="rfid-btn rfid-btn-primary" onclick="document.getElementById('modalDetalhes').remove()">
                  <i class="fas fa-times"></i> Fechar
                </button>
              </div>
            </div>
          </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Adicionar classe active após inserir
        setTimeout(() => {
          document.getElementById('modalDetalhes').classList.add('active');
        }, 10);
      } else {
        showToast("Empréstimo não encontrado", "error");
      }
    }
  } catch (error) {
    console.error("Erro ao buscar detalhes:", error);
    showToast("Erro ao carregar detalhes do empréstimo", "error");
  }
}

async function verHistoricoFerramenta(etiqueta) {
  try {
    const response = await fetch(`/RFID/api/emprestimos/ferramenta/${etiqueta}/historico`);
    const data = await response.json();
    
    if (data.success && data.emprestimos) {
      // Criar modal de histórico
      let historicoHtml = '';
      
      if (data.emprestimos.length > 0) {
        // Ordenar por data decrescente
        const emprestimos = data.emprestimos.sort((a, b) => {
          return new Date(b.dataEmprestimo) - new Date(a.dataEmprestimo);
        });
        
        historicoHtml = emprestimos.map(emp => {
          const colaborador = obterNomeFuncionario(emp.id_colaborador);
          const status = emp.status === 'ativo' ? 
            '<span class="rfid-badge rfid-badge-active">Em Empréstimo</span>' : 
            '<span class="rfid-badge rfid-badge-destroyed">Devolvido</span>';
          
          return `
            <div class="pendente-card" style="margin-bottom: 10px;">
              <div class="pendente-info">
                <div class="pendente-details">
                  <div class="pendente-detail">
                    <strong>Colaborador:</strong> ${colaborador}
                  </div>
                  <div class="pendente-detail">
                    <strong>Empréstimo:</strong> ${emp.dataEmprestimo_formatada}
                  </div>
                  <div class="pendente-detail">
                    <strong>Devolução:</strong> ${emp.dataDevolucao_formatada || "Não devolvido"}
                  </div>
                  <div class="pendente-detail">
                    <strong>Status:</strong> ${status}
                  </div>
                </div>
              </div>
            </div>
          `;
        }).join('');
      } else {
        historicoHtml = '<p style="text-align: center; color: #666;">Nenhum histórico encontrado para esta ferramenta.</p>';
      }
      
      const modalHtml = `
        <div class="modal-overlay" id="modalHistorico" style="display: block;">
          <div class="modal modal-large">
            <div class="modal-header">
              <h3 class="modal-title">
                <i class="fas fa-history"></i>
                Histórico da Ferramenta
              </h3>
              <button class="modal-close" onclick="document.getElementById('modalHistorico').remove()">
                <i class="fas fa-times"></i>
              </button>
            </div>
            <div class="modal-body">
              <div class="info-devolucao" style="margin-bottom: 20px;">
                <p><strong>Etiqueta RFID:</strong> ${etiqueta}</p>
                <p><strong>Total de Empréstimos:</strong> ${data.total || data.emprestimos.length}</p>
              </div>
              <div style="max-height: 400px; overflow-y: auto;">
                ${historicoHtml}
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="rfid-btn rfid-btn-primary" onclick="document.getElementById('modalHistorico').remove()">
                <i class="fas fa-times"></i> Fechar
              </button>
            </div>
          </div>
        </div>
      `;
      
      document.body.insertAdjacentHTML('beforeend', modalHtml);
      
      // Adicionar classe active após inserir
      setTimeout(() => {
        document.getElementById('modalHistorico').classList.add('active');
      }, 10);
    } else {
      showToast("Erro ao carregar histórico", "error");
    }
  } catch (error) {
    console.error("Erro ao buscar histórico:", error);
    showToast("Erro ao carregar histórico da ferramenta", "error");
  }
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

    case "ping":
      window.location.href = "/RFID/ping";
      break;

    default:
      showToast("Seção não encontrada", "error");
  }
}

// Busca de ferramentas para empréstimo
async function buscarFerramentas() {
  const termo = document.getElementById("buscaFerramenta").value.trim();
  const sugestoesDiv = document.getElementById("sugestoesFerramenta");
  
  if (termo.length < 2) {
    sugestoesDiv.classList.remove("show");
    return;
  }
  
  try {
    // Buscar tanto por código quanto por descrição
    const params = new URLSearchParams({
      limite: 10,
      destruida: 0  // Apenas ferramentas ativas
    });
    
    // Se o termo parece um código (tem números), buscar por etiqueta
    if (/\d/.test(termo)) {
      params.append('etiqueta', termo);
    } else {
      // Senão, buscar por descrição
      params.append('descricao', termo);
    }
    
    const response = await fetch(`/RFID/api/etiquetas?${params}`);
    const data = await response.json();
    
    if (data.success && data.etiquetas.length > 0) {
      sugestoesDiv.innerHTML = "";
      
      data.etiquetas.forEach(etiqueta => {
        const item = document.createElement("div");
        item.className = "suggestion-item";
        item.innerHTML = `
          <div class="etiqueta-codigo" title="${etiqueta.EtiquetaRFID_hex}">
            ${formatarEtiquetaRFID(etiqueta.EtiquetaRFID_hex)}
          </div>
          <div class="etiqueta-descricao">${etiqueta.Descricao || "Sem descrição"}</div>
        `;
        
        item.addEventListener("click", function() {
          selecionarFerramenta(etiqueta.EtiquetaRFID_hex, etiqueta.Descricao);
        });
        
        sugestoesDiv.appendChild(item);
      });
      
      sugestoesDiv.classList.add("show");
    } else {
      sugestoesDiv.innerHTML = '<div class="no-results">Nenhuma ferramenta encontrada</div>';
      sugestoesDiv.classList.add("show");
    }
  } catch (error) {
    console.error("Erro ao buscar ferramentas:", error);
    sugestoesDiv.classList.remove("show");
  }
}

function selecionarFerramenta(codigo, descricao) {
  // preencher a div em vez do input
  const box = document.getElementById("codigoSelecionado");
  box.textContent = `${codigo} – ${descricao || "Sem descrição"}`;
  box.classList.add("show");

  document.getElementById("buscaFerramenta").value = "";
  document.getElementById("sugestoesFerramenta").classList.remove("show");

  // verificar disponibilidade
  document.getElementById("emprestimoEtiqueta").value = codigo; // continua guardando valor oculto
  verificarDisponibilidade();
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