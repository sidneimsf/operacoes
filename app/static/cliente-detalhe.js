const parametrosUrl = new URLSearchParams(window.location.search);
const clienteId = parametrosUrl.get('id');

const auth = Shell.montar('clientes', 'Cliente');

let TIPOS = [];
let STATUS = [];
let PRIORIDADES = [];

function labelTipo(chave) {
  const encontrado = TIPOS.find((t) => t.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function labelPrioridade(chave) {
  const encontrado = PRIORIDADES.find((p) => p.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function labelStatus(chave) {
  const encontrado = STATUS.find((s) => s.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function formatarDataCurta(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function renderizarResumo(chamados) {
  const agora = new Date();
  const esteMes = chamados.filter((c) => {
    const data = new Date(c.criado_em);
    return data.getMonth() === agora.getMonth() && data.getFullYear() === agora.getFullYear();
  });
  const emAberto = chamados.filter((c) => c.status !== 'finalizado');

  document.getElementById('kpi-resumo').innerHTML = `
    <div class="kpi-card"><div class="label">atendimentos este mês</div><div class="value">${esteMes.length}</div></div>
    <div class="kpi-card"><div class="label">total no histórico</div><div class="value">${chamados.length}</div></div>
    <div class="kpi-card"><div class="label">em aberto agora</div><div class="value">${emAberto.length}</div></div>
  `;
}

function renderizarTimeline(chamados) {
  const container = document.getElementById('timeline');

  if (chamados.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum atendimento registrado para este cliente ainda.</div>';
    return;
  }

  container.innerHTML = chamados
    .map(
      (c) => `
      <div class="timeline-item">
        <div class="data-col">${formatarDataCurta(c.criado_em)}</div>
        <div class="conteudo">
          <div class="linha-topo">
            <span class="tipo-label">${labelTipo(c.tipo)}</span>
            <span class="priority-badge ${c.prioridade}">${labelPrioridade(c.prioridade)}</span>
            <span class="status-badge ${c.status}">${labelStatus(c.status)}</span>
          </div>
          <div class="descricao">${c.descricao}</div>
          <div class="meta">Atendido por ${c.responsavel_nome || 'não atribuído'} · aberto por ${c.aberto_por}</div>
        </div>
      </div>
    `
    )
    .join('');
}

async function iniciar() {
  if (!clienteId) {
    document.getElementById('cliente-header').innerHTML = '<div class="empty-state">Cliente não especificado.</div>';
    return;
  }

  try {
    const [cliente, tiposEStatus] = await Promise.all([
      Shell.chamarApi(`/clientes-dados/${clienteId}`),
      Shell.chamarApi('/chamados-tipos'),
    ]);
    if (cliente === null || tiposEStatus === null) return;

    TIPOS = tiposEStatus.tipos;
    STATUS = tiposEStatus.status;
    PRIORIDADES = tiposEStatus.prioridades;

    document.getElementById('topbar-title').textContent = cliente.nome;
    document.getElementById('cliente-header').innerHTML = `
      <span class="empresa-tag">${cliente.empresa_nome}</span>
      <h2>${cliente.nome}</h2>
      <span class="cnpj">${cliente.cnpj || 'CNPJ não informado'}</span>
    `;

    const chamados = await Shell.chamarApi(`/chamados-dados?cliente_id=${clienteId}`);
    if (chamados === null) return;

    renderizarResumo(chamados);
    renderizarTimeline(chamados);
  } catch (erro) {
    document.getElementById('cliente-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
