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

const DIAS_PADRAO = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado'];
const DIAS_LABEL = {
  segunda: 'Segunda', terca: 'Terça', quarta: 'Quarta', quinta: 'Quinta',
  sexta: 'Sexta', sabado: 'Sábado', domingo: 'Domingo',
};

function celulaHorarioHtml(registro, campoNome) {
  if (!registro) return '<td><span class="horario-celula-vazia">—</span></td>';
  return `
    <td>
      <div class="horario-celula">
        <span class="nome">${registro[campoNome]}</span>
        <span class="hora">${registro.hora_inicio}-${registro.hora_fim}</span>
      </div>
    </td>
  `;
}

function montarGradeSemanal(horarios, campoNome) {
  if (horarios.length === 0) {
    return '<div class="empty-state">Nenhum horário cadastrado ainda.</div>';
  }

  const diasComDados = new Set(horarios.map((h) => h.dia_semana));
  const dias = [...DIAS_PADRAO];
  if (diasComDados.has('domingo')) dias.push('domingo');

  const porDiaTurno = {};
  horarios.forEach((h) => {
    porDiaTurno[`${h.dia_semana}_${h.turno}`] = h;
  });

  const headerCols = dias.map((d) => `<th>${DIAS_LABEL[d]}</th>`).join('');
  const linhaManha = dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_manha`], campoNome)).join('');
  const linhaTarde = dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_tarde`], campoNome)).join('');

  return `
    <table class="horario-grid">
      <thead><tr><th></th>${headerCols}</tr></thead>
      <tbody>
        <tr><td>Manhã</td>${linhaManha}</tr>
        <tr><td>Tarde</td>${linhaTarde}</tr>
      </tbody>
    </table>
  `;
}

async function carregarMapaServicos() {
  const container = document.getElementById('mapa-servicos');
  try {
    const horarios = await Shell.chamarApi(`/clientes-dados/${clienteId}/horarios`);
    if (horarios === null) return;
    container.innerHTML = montarGradeSemanal(horarios, 'colaborador_nome');
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o mapa de serviços agora.</div>';
  }
}

let clienteAtual = null;
let empresasCache = [];

function montarModalEditarCliente() {
  const html = `
    <div class="modal-overlay" id="editar-cliente-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Editar cliente</h3>
          <button class="modal-close" id="editar-cliente-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="editar-cliente-form">
          <div class="field">
            <label for="editar-cliente-empresa">Empresa</label>
            <select id="editar-cliente-empresa" required></select>
          </div>
          <div class="field">
            <label for="editar-cliente-nome">Nome</label>
            <input type="text" id="editar-cliente-nome" required>
          </div>
          <div class="field">
            <label for="editar-cliente-cnpj">CNPJ</label>
            <input type="text" id="editar-cliente-cnpj">
          </div>
          <div class="field">
            <label for="editar-cliente-municipio">Município</label>
            <input type="text" id="editar-cliente-municipio">
          </div>
          <div class="error-message" id="editar-cliente-modal-erro"></div>
          <button type="submit" class="btn-primary" id="editar-cliente-modal-enviar">Salvar alterações</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('editar-cliente-modal-fechar').addEventListener('click', () => {
    document.getElementById('editar-cliente-modal-overlay').hidden = true;
  });
  document.getElementById('editar-cliente-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'editar-cliente-modal-overlay') {
      document.getElementById('editar-cliente-modal-overlay').hidden = true;
    }
  });
  document.getElementById('editar-cliente-form').addEventListener('submit', salvarEdicaoCliente);
}

async function abrirModalEditarCliente() {
  document.getElementById('editar-cliente-modal-erro').classList.remove('visible');
  document.getElementById('editar-cliente-empresa').innerHTML = empresasCache
    .map((e) => `<option value="${e.id}" ${e.id === clienteAtual.empresa_id ? 'selected' : ''}>${e.nome}</option>`)
    .join('');
  document.getElementById('editar-cliente-nome').value = clienteAtual.nome;
  document.getElementById('editar-cliente-cnpj').value = clienteAtual.cnpj || '';
  document.getElementById('editar-cliente-municipio').value = clienteAtual.municipio || '';
  document.getElementById('editar-cliente-modal-overlay').hidden = false;
}

async function salvarEdicaoCliente(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-cliente-modal-erro');
  const botao = document.getElementById('editar-cliente-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    empresa_id: Number(document.getElementById('editar-cliente-empresa').value),
    nome: document.getElementById('editar-cliente-nome').value,
    cnpj: document.getElementById('editar-cliente-cnpj').value || null,
    municipio: document.getElementById('editar-cliente-municipio').value || null,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    clienteAtual = await Shell.chamarApi(`/clientes-dados/${clienteId}`, { method: 'PATCH', body: corpo });
    document.getElementById('editar-cliente-modal-overlay').hidden = true;
    renderizarHeaderCliente();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar alterações';
  }
}

function renderizarHeaderCliente() {
  document.getElementById('topbar-title').textContent = clienteAtual.nome;
  document.getElementById('cliente-header').innerHTML = `
    <span class="empresa-tag">${clienteAtual.empresa_nome}${clienteAtual.ativo ? '' : ' · INATIVO'}</span>
    <h2>${clienteAtual.nome}</h2>
    <span class="cnpj">${clienteAtual.cnpj || 'CNPJ não informado'}</span>
  `;
  const btnToggle = document.getElementById('btn-toggle-cliente');
  btnToggle.textContent = clienteAtual.ativo ? 'Remover cliente' : 'Reativar cliente';
}

async function alternarStatusCliente() {
  const acao = clienteAtual.ativo ? 'remover (desativar)' : 'reativar';
  if (!confirm(`Tem certeza que quer ${acao} este cliente?`)) return;

  try {
    clienteAtual = await Shell.chamarApi(`/clientes-dados/${clienteId}`, {
      method: 'PATCH',
      body: { ativo: !clienteAtual.ativo },
    });
    renderizarHeaderCliente();
  } catch (erro) {
    alert('Não foi possível concluir a ação agora.');
  }
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

    empresasCache = await Shell.chamarApi('/empresas');

    document.getElementById('topbar-title').textContent = cliente.nome;
    clienteAtual = cliente;
    renderizarHeaderCliente();

    montarModalEditarCliente();
    document.getElementById('btn-editar-cliente').addEventListener('click', abrirModalEditarCliente);
    document.getElementById('btn-toggle-cliente').addEventListener('click', alternarStatusCliente);

    const chamados = await Shell.chamarApi(`/chamados-dados?cliente_id=${clienteId}`);
    if (chamados === null) return;

    renderizarResumo(chamados);
    renderizarTimeline(chamados);
    carregarMapaServicos();
  } catch (erro) {
    document.getElementById('cliente-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
