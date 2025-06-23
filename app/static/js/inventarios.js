// inventarios.js - Sistema de Inventários RFID

// ========================================================================
// VARIÁVEIS GLOBAIS
// ========================================================================
let inventarios = [];
let inventarioAtual = null;
let itensInventarioAtual = [];
let paginaAtual = 1;
const itensPorPagina = 20;

// Cache de funcionários
let cacheFuncionarios = new Map();
let cacheTimestamp = null;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutos

// ========================================================================
// FUNÇÕES DE INICIALIZAÇÃO
// ========================================================================

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de Inventários RFID inicializado');
    
    // Carregar funcionários primeiro
    carregarFuncionarios().then(() => {
        // Carregar dados iniciais após carregar funcionários
        carregarInventarios();
        carregarEstatisticas();
    });
    
    // Configurar event listeners
    configurarEventListeners();
    
    // Atualizar a cada 30 segundos
    setInterval(atualizarDados, 30000);
});

// Configurar event listeners
function configurarEventListeners() {
    // Filtros
    document.getElementById('filtroStatus').addEventListener('change', aplicarFiltros);
    document.getElementById('filtroDataInicio').addEventListener('change', aplicarFiltros);
    document.getElementById('filtroDataFim').addEventListener('change', aplicarFiltros);
    
    // Drag and drop para CSV
    const uploadArea = document.querySelector('.photo-upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
    }
    
    // Busca de colaboradores
    const campoBuscaColaborador = document.getElementById('buscaColaboradorInventario');
    if (campoBuscaColaborador) {
        campoBuscaColaborador.addEventListener('input', debounce(buscarColaboradores, 300));
        campoBuscaColaborador.addEventListener('focus', function() {
            if (this.value.trim().length >= 2) {
                buscarColaboradores();
            }
        });
    }
    
    // Fechar sugestões ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.search-container')) {
            const sugestoes = document.getElementById('sugestoesColaboradorInventario');
            if (sugestoes) sugestoes.classList.remove('show');
        }
    });
}

// ========================================================================
// FUNÇÕES DE API DE FUNCIONÁRIOS
// ========================================================================

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
    const termo = document.getElementById('buscaColaboradorInventario').value.trim();
    const sugestoesDiv = document.getElementById('sugestoesColaboradorInventario');
    
    if (termo.length < 2) {
        sugestoesDiv.classList.remove('show');
        return;
    }
    
    try {
        const response = await fetch(`https://automacao.tce.go.gov.br/checklistpredial/api/funcionarios/buscar?nome=${encodeURIComponent(termo)}`);
        const data = await response.json();
        
        if (data.success && data.funcionarios.length > 0) {
            sugestoesDiv.innerHTML = '';
            
            // Limitar a 10 sugestões
            const funcionarios = data.funcionarios.slice(0, 10);
            
            funcionarios.forEach(func => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerHTML = `
                    <div class="suggestion-nome">${func.nome}</div>
                    <div class="suggestion-empresa">${func.empresa}</div>
                `;
                
                item.addEventListener('click', function() {
                    selecionarColaborador(func.id, func.nome, func.empresa);
                });
                
                sugestoesDiv.appendChild(item);
            });
            
            sugestoesDiv.classList.add('show');
        } else {
            sugestoesDiv.innerHTML = '<div class="no-results">Nenhum colaborador encontrado</div>';
            sugestoesDiv.classList.add('show');
        }
    } catch (error) {
        console.error('Erro ao buscar colaboradores:', error);
        sugestoesDiv.classList.remove('show');
    }
}

function selecionarColaborador(id, nome, empresa) {
    // Preencher o campo hidden com o ID
    document.getElementById('inventarioColaborador').value = id;
    
    // Mostrar informações do colaborador selecionado
    const infoDiv = document.getElementById('colaboradorSelecionadoInfo');
    infoDiv.innerHTML = `
        <i class="fas fa-user-check"></i>
        <span>${nome} - ${empresa}</span>
    `;
    infoDiv.style.display = 'block';
    
    // Limpar busca e esconder sugestões
    document.getElementById('buscaColaboradorInventario').value = '';
    document.getElementById('sugestoesColaboradorInventario').classList.remove('show');
}

// ========================================================================
// FUNÇÕES DE NAVEGAÇÃO
// ========================================================================

function navegarPara(pagina) {
    const baseUrl = window.location.origin;
    const prefixo = '/RFID';
    
    switch(pagina) {
        case 'etiquetas':
            window.location.href = `${baseUrl}${prefixo}/`;
            break;
        case 'inventarios':
            window.location.href = `${baseUrl}${prefixo}/inventarios`;
            break;
        case 'leitores':
            window.location.href = `${baseUrl}${prefixo}/leitores`;
            break;
        case 'emprestimos':
            window.location.href = `${baseUrl}${prefixo}/emprestimos`;
            break;
        default:
            console.error('Página não encontrada:', pagina);
    }
}

// ========================================================================
// FUNÇÕES DE CARREGAMENTO DE DADOS
// ========================================================================

async function carregarInventarios() {
    mostrarLoading(true);
    
    try {
        const filtros = obterFiltros();
        const offset = (paginaAtual - 1) * itensPorPagina;
        
        const params = new URLSearchParams({
            limite: itensPorPagina,
            offset: offset
        });
        
        // Adicionar filtros
        if (filtros.status) params.append('status', filtros.status);
        if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
        if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
        
        const response = await fetch(`/RFID/api/inventarios?${params}`);
        const data = await response.json();
        
        if (data.success) {
            inventarios = data.inventarios;
            renderizarTabela(data.inventarios);
            renderizarPaginacao(data.total);
            
            // Mostrar/esconder elementos apropriados
            document.getElementById('tabelaInventarios').style.display = data.inventarios.length > 0 ? 'table' : 'none';
            document.getElementById('emptyState').style.display = data.inventarios.length === 0 ? 'block' : 'none';
            document.getElementById('paginacao').style.display = data.total > itensPorPagina ? 'block' : 'none';
        } else {
            mostrarToast('Erro ao carregar inventários', 'error');
        }
    } catch (error) {
        console.error('Erro ao carregar inventários:', error);
        mostrarToast('Erro ao conectar com o servidor', 'error');
    } finally {
        mostrarLoading(false);
    }
}

async function carregarEstatisticas() {
    try {
        const response = await fetch('/RFID/api/inventarios/estatisticas?periodo=30');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.estatisticas;
            document.getElementById('totalInventarios').textContent = stats.total_inventarios || 0;
            document.getElementById('inventariosAndamento').textContent = stats.inventarios_em_andamento || 0;
            document.getElementById('inventariosFinalizados').textContent = stats.inventarios_finalizados || 0;
            document.getElementById('taxaLocalizacao').textContent = `${stats.taxa_localizacao_media || 0}%`;
        }
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
    }
}

// ========================================================================
// FUNÇÕES DE RENDERIZAÇÃO
// ========================================================================

function renderizarTabela(inventarios) {
    const tbody = document.getElementById('tabelaCorpo');
    tbody.innerHTML = '';
    
    inventarios.forEach(inventario => {
        const tr = document.createElement('tr');
        const percentual = inventario.percentual_localizado || 0;
        const corBarra = percentual >= 80 ? 'var(--rfid-success)' : 
                        percentual >= 50 ? 'var(--rfid-warning)' : 'var(--rfid-danger)';
        
        tr.innerHTML = `
            <td style="font-weight: 600;">#${inventario.idInventarioRFID}</td>
            <td>${inventario.dataInventario_formatada || '-'}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="flex: 1; background: var(--rfid-border); border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="width: ${percentual}%; background: ${corBarra}; height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                    <span style="min-width: 50px; text-align: right; font-weight: 600;">
                        ${inventario.itens_localizados || 0}/${inventario.total_itens || 0}
                    </span>
                </div>
            </td>
            <td>
                <span class="rfid-badge ${inventario.Status === 'Finalizado' ? 'rfid-badge-active' : 'rfid-badge-destroyed'}">
                    ${inventario.Status}
                </span>
            </td>
            <td>
                <div class="rfid-actions">
                    <button class="rfid-action-btn rfid-action-btn-primary" 
                            onclick="visualizarInventario(${inventario.idInventarioRFID})"
                            title="Visualizar detalhes">
                        <i class="fas fa-eye"></i> Ver
                    </button>
                    ${inventario.Status === 'Em andamento' ? `
                        <button class="rfid-action-btn rfid-action-btn-warning" 
                                onclick="abrirModalUploadCSV(${inventario.idInventarioRFID})"
                                title="Importar leituras CSV">
                            <i class="fas fa-file-upload"></i> CSV
                        </button>
                        <button class="rfid-action-btn rfid-action-btn-success" 
                                onclick="confirmarFinalizarInventario(${inventario.idInventarioRFID})"
                                title="Finalizar inventário">
                            <i class="fas fa-check"></i> Finalizar
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function renderizarPaginacao(total) {
    const totalPaginas = Math.ceil(total / itensPorPagina);
    const inicio = ((paginaAtual - 1) * itensPorPagina) + 1;
    const fim = Math.min(paginaAtual * itensPorPagina, total);
    
    // Atualizar informações
    document.getElementById('registroInicio').textContent = total > 0 ? inicio : 0;
    document.getElementById('registroFim').textContent = fim;
    document.getElementById('registroTotal').textContent = total;
    
    // Renderizar controles
    const controles = document.getElementById('paginacaoControles');
    controles.innerHTML = '';
    
    // Botão anterior
    const btnAnterior = criarBotaoPaginacao('Anterior', paginaAtual > 1, () => {
        paginaAtual--;
        carregarInventarios();
    });
    controles.appendChild(btnAnterior);
    
    // Páginas
    const maxBotoes = 5;
    let inicioPag = Math.max(1, paginaAtual - Math.floor(maxBotoes / 2));
    let fimPag = Math.min(totalPaginas, inicioPag + maxBotoes - 1);
    
    if (fimPag - inicioPag < maxBotoes - 1) {
        inicioPag = Math.max(1, fimPag - maxBotoes + 1);
    }
    
    if (inicioPag > 1) {
        controles.appendChild(criarBotaoPaginacao('1', true, () => {
            paginaAtual = 1;
            carregarInventarios();
        }));
        
        if (inicioPag > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.style.margin = '0 5px';
            controles.appendChild(ellipsis);
        }
    }
    
    for (let i = inicioPag; i <= fimPag; i++) {
        const btn = criarBotaoPaginacao(i.toString(), true, () => {
            paginaAtual = i;
            carregarInventarios();
        });
        
        if (i === paginaAtual) {
            btn.classList.add('active');
        }
        
        controles.appendChild(btn);
    }
    
    if (fimPag < totalPaginas) {
        if (fimPag < totalPaginas - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.style.margin = '0 5px';
            controles.appendChild(ellipsis);
        }
        
        controles.appendChild(criarBotaoPaginacao(totalPaginas.toString(), true, () => {
            paginaAtual = totalPaginas;
            carregarInventarios();
        }));
    }
    
    // Botão próximo
    const btnProximo = criarBotaoPaginacao('Próximo', paginaAtual < totalPaginas, () => {
        paginaAtual++;
        carregarInventarios();
    });
    controles.appendChild(btnProximo);
}

function criarBotaoPaginacao(texto, habilitado, onClick) {
    const btn = document.createElement('button');
    btn.className = 'rfid-page-btn';
    btn.textContent = texto;
    btn.disabled = !habilitado;
    
    if (habilitado && onClick) {
        btn.onclick = onClick;
    }
    
    return btn;
}

// ========================================================================
// FUNÇÕES DE MODAL
// ========================================================================

function abrirModalNovoInventario() {
    document.getElementById('inventarioColaborador').value = '';
    document.getElementById('inventarioObservacao').value = '';
    document.getElementById('colaboradorSelecionadoInfo').style.display = 'none';
    document.getElementById('buscaColaboradorInventario').value = '';
    abrirModal('modalInventario');
}

function abrirModalUploadCSV(idInventario) {
    document.getElementById('csvInventarioId').value = idInventario;
    document.getElementById('arquivoCSV').value = '';
    document.getElementById('csvInfo').style.display = 'none';
    abrirModal('modalUploadCSV');
}

function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function fecharModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// ========================================================================
// FUNÇÕES DE INVENTÁRIO
// ========================================================================

async function criarInventario(event) {
    event.preventDefault();
    
    const btn = document.getElementById('btnCriarInventario');
    btn.disabled = true;
    btn.classList.add('btn-loading');
    
    try {
        const dados = {
            id_colaborador: parseInt(document.getElementById('inventarioColaborador').value),
            Observacao: document.getElementById('inventarioObservacao').value
        };
        
        const response = await fetch('/RFID/api/inventarios', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('Inventário criado com sucesso!', 'success');
            fecharModal('modalInventario');
            carregarInventarios();
            carregarEstatisticas();
            
            // Abrir detalhes do novo inventário
            setTimeout(() => {
                visualizarInventario(data.id_inventario);
            }, 500);
        } else {
            mostrarToast(data.error || 'Erro ao criar inventário', 'error');
        }
    } catch (error) {
        console.error('Erro ao criar inventário:', error);
        mostrarToast('Erro ao conectar com o servidor', 'error');
    } finally {
        btn.disabled = false;
        btn.classList.remove('btn-loading');
    }
}

async function visualizarInventario(idInventario) {
    try {
        const response = await fetch(`/RFID/api/inventarios/${idInventario}`);
        const data = await response.json();
        
        if (data.success) {
            inventarioAtual = data.inventario;
            itensInventarioAtual = data.itens;
            
            // Preencher informações
            document.getElementById('detalheInventarioId').textContent = inventarioAtual.idInventarioRFID;
            document.getElementById('detalheData').textContent = inventarioAtual.dataInventario_formatada || '-';
            document.getElementById('detalheStatus').innerHTML = `
                <span class="rfid-badge ${inventarioAtual.Status === 'Finalizado' ? 'rfid-badge-active' : 'rfid-badge-destroyed'}">
                    ${inventarioAtual.Status}
                </span>
            `;
            document.getElementById('detalheProgresso').textContent = 
                `${data.estatisticas.itens_localizados}/${data.estatisticas.total_itens} (${data.estatisticas.percentual_localizado}%)`;
            document.getElementById('detalheObservacoes').textContent = inventarioAtual.Observacao || 'Sem observações';
            
            // Estatísticas
            document.getElementById('estatTotal').textContent = data.estatisticas.total_itens;
            document.getElementById('estatLocalizados').textContent = data.estatisticas.itens_localizados;
            document.getElementById('estatNaoLocalizados').textContent = data.estatisticas.itens_nao_localizados;
            document.getElementById('estatTaxa').textContent = `${data.estatisticas.percentual_localizado}%`;
            
            // Renderizar itens
            renderizarItensInventario(data.itens);
            
            // Resetar filtros
            document.getElementById('filtroStatusItem').value = '';
            document.getElementById('filtroBuscarItem').value = '';
            
            abrirModal('modalDetalhes');
        } else {
            mostrarToast(data.error || 'Erro ao carregar inventário', 'error');
        }
    } catch (error) {
        console.error('Erro ao visualizar inventário:', error);
        mostrarToast('Erro ao conectar com o servidor', 'error');
    }
}

function renderizarItensInventario(itens) {
    const tbody = document.getElementById('tabelaItensInventario');
    tbody.innerHTML = '';
    
    itens.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="rfid-etiqueta">${item.EtiquetaRFID_hex}</td>
            <td>${item.DescricaoEtiqueta || '-'}</td>
            <td>
                <span class="rfid-badge ${item.Status === 'Localizado' ? 'rfid-badge-active' : 'rfid-badge-destroyed'}">
                    ${item.Status}
                </span>
            </td>
            <td style="font-size: 0.85rem; color: #6c757d;">
                ${item.ObservacaoItem || '-'}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filtrarItensInventario() {
    const statusFiltro = document.getElementById('filtroStatusItem').value.toLowerCase();
    const buscaFiltro = document.getElementById('filtroBuscarItem').value.toLowerCase();
    
    const itensFiltrados = itensInventarioAtual.filter(item => {
        const statusMatch = !statusFiltro || item.Status.toLowerCase() === statusFiltro;
        const buscaMatch = !buscaFiltro || 
                          item.EtiquetaRFID_hex.toLowerCase().includes(buscaFiltro) ||
                          (item.DescricaoEtiqueta && item.DescricaoEtiqueta.toLowerCase().includes(buscaFiltro));
        
        return statusMatch && buscaMatch;
    });
    
    renderizarItensInventario(itensFiltrados);
    
    // Atualizar estatísticas filtradas
    const localizados = itensFiltrados.filter(item => item.Status === 'Localizado').length;
    const total = itensFiltrados.length;
    const taxa = total > 0 ? Math.round((localizados / total) * 100) : 0;
    
    document.getElementById('estatTotal').textContent = total;
    document.getElementById('estatLocalizados').textContent = localizados;
    document.getElementById('estatNaoLocalizados').textContent = total - localizados;
    document.getElementById('estatTaxa').textContent = `${taxa}%`;
}

async function processarCSV(event) {
    event.preventDefault();
    
    const btn = document.getElementById('btnProcessarCSV');
    btn.disabled = true;
    btn.classList.add('btn-loading');
    
    try {
        const idInventario = document.getElementById('csvInventarioId').value;
        const arquivo = document.getElementById('arquivoCSV').files[0];
        
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        
        const response = await fetch(`/RFID/api/inventarios/${idInventario}/processar-csv`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            let mensagem = `CSV processado! ${data.etiquetas_atualizadas} etiquetas marcadas como localizadas.`;
            
            if (data.erros && data.erros.length > 0) {
                mensagem += ` (${data.erros.length} erros)`;
                console.warn('Erros no processamento:', data.erros);
            }
            
            mostrarToast(mensagem, 'success');
            fecharModal('modalUploadCSV');
            
            // Recarregar inventário se estiver visualizando
            if (inventarioAtual && inventarioAtual.idInventarioRFID == idInventario) {
                visualizarInventario(idInventario);
            }
            
            carregarInventarios();
        } else {
            mostrarToast(data.error || 'Erro ao processar CSV', 'error');
        }
    } catch (error) {
        console.error('Erro ao processar CSV:', error);
        mostrarToast('Erro ao conectar com o servidor', 'error');
    } finally {
        btn.disabled = false;
        btn.classList.remove('btn-loading');
    }
}

function confirmarFinalizarInventario(idInventario) {
    document.getElementById('confirmTitulo').innerHTML = '<i class="fas fa-check-circle"></i> Finalizar Inventário';
    document.getElementById('confirmMensagem').textContent = 
        'Tem certeza que deseja finalizar este inventário? Após finalizado, não será possível adicionar mais leituras.';
    document.getElementById('confirmIcon').className = 'fas fa-check-circle';
    document.getElementById('confirmIcon').style.color = 'var(--rfid-success)';
    
    const btnConfirmar = document.getElementById('btnConfirmar');
    btnConfirmar.className = 'rfid-btn rfid-btn-success';
    btnConfirmar.onclick = () => finalizarInventario(idInventario);
    
    abrirModal('modalConfirmacao');
}

async function finalizarInventario(idInventario) {
    try {
        const response = await fetch(`/RFID/api/inventarios/${idInventario}/finalizar`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('Inventário finalizado com sucesso!', 'success');
            fecharModal('modalConfirmacao');
            carregarInventarios();
            carregarEstatisticas();
        } else {
            mostrarToast(data.error || 'Erro ao finalizar inventário', 'error');
        }
    } catch (error) {
        console.error('Erro ao finalizar inventário:', error);
        mostrarToast('Erro ao conectar com o servidor', 'error');
    }
}

// ========================================================================
// FUNÇÕES DE UPLOAD CSV
// ========================================================================

function validarArquivoCSV(input) {
    const arquivo = input.files[0];
    
    if (arquivo) {
        if (!arquivo.name.toLowerCase().endsWith('.csv')) {
            mostrarToast('Por favor, selecione um arquivo CSV', 'error');
            input.value = '';
            return;
        }
        
        if (arquivo.size > 5 * 1024 * 1024) { // 5MB
            mostrarToast('O arquivo não pode ser maior que 5MB', 'error');
            input.value = '';
            return;
        }
        
        // Mostrar nome do arquivo
        document.getElementById('csvFileName').textContent = arquivo.name;
        document.getElementById('csvInfo').style.display = 'block';
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const input = document.getElementById('arquivoCSV');
        input.files = files;
        validarArquivoCSV(input);
    }
}

// ========================================================================
// FUNÇÕES DE EXPORTAÇÃO
// ========================================================================

async function downloadTemplateCSV() {
    try {
        window.location.href = '/RFID/api/inventarios/download-template';
        mostrarToast('Download do template iniciado', 'success');
    } catch (error) {
        console.error('Erro ao baixar template:', error);
        mostrarToast('Erro ao baixar template', 'error');
    }
}

function exportarItensInventario() {
    if (!inventarioAtual || !itensInventarioAtual) return;
    
    // Criar CSV
    let csv = 'EPC,Descricao,Status,Observacao\n';
    
    itensInventarioAtual.forEach(item => {
        csv += `"${item.EtiquetaRFID_hex}","${item.DescricaoEtiqueta || ''}","${item.Status}","${item.ObservacaoItem || ''}"\n`;
    });
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `inventario_${inventarioAtual.idInventarioRFID}_itens.csv`;
    link.click();
    
    mostrarToast('Exportação concluída', 'success');
}

// ========================================================================
// FUNÇÕES AUXILIARES
// ========================================================================

function obterFiltros() {
    const filtros = {};
    
    const status = document.getElementById('filtroStatus').value;
    if (status) filtros.status = status;
    
    const dataInicio = document.getElementById('filtroDataInicio').value;
    if (dataInicio) filtros.data_inicio = dataInicio;
    
    const dataFim = document.getElementById('filtroDataFim').value;
    if (dataFim) filtros.data_fim = dataFim;
    
    return filtros;
}

function aplicarFiltros() {
    paginaAtual = 1;
    carregarInventarios();
}

function atualizarDados() {
    // Atualizar cache de funcionários e depois os dados
    carregarFuncionarios(true).then(() => {
        carregarInventarios();
        carregarEstatisticas();
    });
}

function mostrarLoading(mostrar) {
    document.getElementById('loadingState').style.display = mostrar ? 'block' : 'none';
    document.getElementById('tabelaInventarios').style.display = mostrar ? 'none' : 'table';
}

function mostrarToast(mensagem, tipo = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    toast.innerHTML = `
        <i class="${icons[tipo]} toast-icon"></i>
        <div class="toast-content">
            <div class="toast-title">${tipo.charAt(0).toUpperCase() + tipo.slice(1)}</div>
            <div class="toast-message">${mensagem}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remover após 5 segundos
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
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