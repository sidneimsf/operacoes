const auth = Shell.montar('ocorrencias', 'Ocorrências');

let TIPOS = [];
let STATUS = [];
let empresas = [];

const filtros = {
  status: null,
  tipo: '',
  empresa_id: '',
  cliente_id: '',
  responsavel_id: '',
  data_inicio: '',
  data_fim: '',
};

function montarQueryString() {
  const params = new URLSearchParams();
  if (filtros.status) params.set('status_filtro', filtros.status);
  if (filtros.tipo) params.set('tipo', filtros.tipo);
  if (filtros.empresa_id) params.set('empresa_id', filtros.empresa_id);
  if (filtros.cliente_id) params.set('cliente_id', filtros.cliente_id);
  if (filtros.responsavel_id) params.set('responsavel_id', filtros.responsavel_id);
  if (filtros.data_inicio) params.set('data_inicio', filtros.data_inicio);
  if (filtros.data_fim) params.set('data_fim', filtros.data_fim);
  return params.toString();
}

function renderizarChipsStatus() {
  const container = document.getElementById('chips-status');
  container.innerHTML = '';

  const opcoes = [{ chave: null, label: 'Todos' }, ...STATUS];

  opcoes.forEach((opcao) => {
    const chip = document.createElement('button');
    chip.className = 'chip' + (filtros.status === opcao.chave ? ' active' : '');
    chip.textContent = opcao.label;
    chip.addEventListener('click', () => {
      filtros.status = opcao.chave;
      renderizarChipsStatus();
      carregarChamados();
    });
    container.appendChild(chip);
  });
}

async function popularClientesDaEmpresa(empresaId) {
  const selectCliente = document.getElementById('filtro-cliente');
  if (!empresaId) {
    selectCliente.innerHTML = '<option value="">Todos</option>';
    return;
  }
  const clientes = await Shell.chamarApi(`/clientes-dados?empresa_id=${empresaId}`);
  selectCliente.innerHTML =
    '<option value="">Todos</option>' +
    clientes.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
}

function formatarData(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function labelTipo(chave) {
  const encontrado = TIPOS.find((t) => t.chave === chave);
  return encontrado ? encontrado.label : chave;
}

async function trocarStatus(chamadoId, novoStatus) {
  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoId}`, {
      method: 'PATCH',
      body: { status: novoStatus },
    });
    carregarChamados();
  } catch (erro) {
    alert('Não foi possível atualizar o status agora.');
  }
}

function montarModalFinalizar() {
  const html = `
    <div class="modal-overlay" id="finalizar-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Finalizar chamado</h3>
          <button class="modal-close" id="finalizar-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="finalizar-form">
          <div class="field">
            <label for="finalizar-pendencia">Ficou alguma pendência?</label>
            <select id="finalizar-pendencia">
              <option value="nao">Não</option>
              <option value="sim">Sim</option>
            </select>
          </div>
          <div class="field" id="campo-pendencia-detalhe" hidden>
            <label for="finalizar-pendencia-detalhe">Qual pendência?</label>
            <textarea id="finalizar-pendencia-detalhe" rows="2"></textarea>
          </div>

          <div class="field">
            <label for="finalizar-documento">Foi necessário enviar algum documento?</label>
            <select id="finalizar-documento">
              <option value="nao">Não</option>
              <option value="sim">Sim</option>
            </select>
          </div>
          <div class="field" id="campo-documento-detalhe" hidden>
            <label for="finalizar-documento-detalhe">Qual documento?</label>
            <textarea id="finalizar-documento-detalhe" rows="2"></textarea>
          </div>

          <div class="field">
            <label for="finalizar-observacoes">Observações (opcional)</label>
            <textarea id="finalizar-observacoes" rows="2"></textarea>
          </div>

          <div class="error-message" id="finalizar-modal-erro"></div>
          <button type="submit" class="btn-primary" id="finalizar-modal-enviar">Finalizar chamado</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('finalizar-modal-fechar').addEventListener('click', () => fecharModalFinalizar(true));
  document.getElementById('finalizar-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'finalizar-modal-overlay') fecharModalFinalizar(true);
  });

  document.getElementById('finalizar-pendencia').addEventListener('change', (evento) => {
    document.getElementById('campo-pendencia-detalhe').hidden = evento.target.value !== 'sim';
  });
  document.getElementById('finalizar-documento').addEventListener('change', (evento) => {
    document.getElementById('campo-documento-detalhe').hidden = evento.target.value !== 'sim';
  });

  document.getElementById('finalizar-form').addEventListener('submit', enviarFinalizacao);
}

let chamadoEmFinalizacao = null;
let selectEmFinalizacao = null;

function abrirModalFinalizar(chamadoId, selectEl) {
  chamadoEmFinalizacao = chamadoId;
  selectEmFinalizacao = selectEl;

  document.getElementById('finalizar-form').reset();
  document.getElementById('campo-pendencia-detalhe').hidden = true;
  document.getElementById('campo-documento-detalhe').hidden = true;
  document.getElementById('finalizar-modal-erro').classList.remove('visible');
  document.getElementById('finalizar-modal-overlay').hidden = false;
}

function fecharModalFinalizar(cancelou) {
  document.getElementById('finalizar-modal-overlay').hidden = true;
  if (cancelou && selectEmFinalizacao) {
    selectEmFinalizacao.value = selectEmFinalizacao.dataset.statusAnterior;
  }
  chamadoEmFinalizacao = null;
  selectEmFinalizacao = null;
}

async function enviarFinalizacao(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('finalizar-modal-erro');
  const botao = document.getElementById('finalizar-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    pendencia: document.getElementById('finalizar-pendencia').value === 'sim',
    pendencia_detalhe: document.getElementById('finalizar-pendencia-detalhe').value,
    documento_enviado: document.getElementById('finalizar-documento').value === 'sim',
    documento_detalhe: document.getElementById('finalizar-documento-detalhe').value,
    observacoes: document.getElementById('finalizar-observacoes').value,
  };

  botao.disabled = true;
  botao.textContent = 'Finalizando...';

  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoEmFinalizacao}/finalizar`, {
      method: 'POST',
      body: corpo,
    });
    document.getElementById('finalizar-modal-overlay').hidden = true;
    chamadoEmFinalizacao = null;
    selectEmFinalizacao = null;
    carregarChamados();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível finalizar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Finalizar chamado';
  }
}

function renderizarTabela(chamados) {
  const container = document.getElementById('lista-chamados');

  if (chamados.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum chamado encontrado com esses filtros.</div>';
    return;
  }

  const opcoesStatusHtml = (statusAtual) =>
    STATUS.map((s) => `<option value="${s.chave}" ${s.chave === statusAtual ? 'selected' : ''}>${s.label}</option>`).join('');

  const linhas = chamados
    .map(
      (c) => `
      <tr>
        <td>${formatarData(c.criado_em)}</td>
        <td>${c.cliente_nome}</td>
        <td>${labelTipo(c.tipo)}</td>
        <td class="chamado-descricao" title="${c.descricao}">${c.descricao}</td>
        <td>${c.responsavel_nome || '—'}</td>
        <td><span class="status-badge ${c.status}">${STATUS.find((s) => s.chave === c.status)?.label || c.status}</span></td>
        <td>
          <select class="status-select" data-id="${c.id}" data-status-anterior="${c.status}" ${c.status === 'finalizado' ? 'disabled' : ''}>
            ${opcoesStatusHtml(c.status)}
          </select>
        </td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Data</th><th>Cliente</th><th>Tipo</th><th>Descrição</th><th>Responsável</th><th>Status</th><th>Alterar</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;

  container.querySelectorAll('.status-select').forEach((select) => {
    select.addEventListener('change', (evento) => {
      const novoStatus = evento.target.value;
      if (novoStatus === 'finalizado') {
        abrirModalFinalizar(evento.target.dataset.id, evento.target);
      } else {
        trocarStatus(evento.target.dataset.id, novoStatus);
      }
    });
  });
}

async function carregarChamados() {
  const container = document.getElementById('lista-chamados');
  container.innerHTML = '<div class="loading-state">Carregando chamados...</div>';
  try {
    const chamados = await Shell.chamarApi(`/chamados-dados?${montarQueryString()}`);
    if (chamados === null) return;
    renderizarTabela(chamados);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os chamados agora.</div>';
  }
}

async function iniciar() {
  montarModalFinalizar();

  const parametrosUrl = new URLSearchParams(window.location.search);
  if (parametrosUrl.get('responsavel_id')) {
    filtros.responsavel_id = parametrosUrl.get('responsavel_id');
  }

  const tiposEStatus = await Shell.chamarApi('/chamados-tipos');
  if (tiposEStatus === null) return;
  TIPOS = tiposEStatus.tipos;
  STATUS = tiposEStatus.status;

  document.getElementById('filtro-tipo').innerHTML =
    '<option value="">Todos</option>' + TIPOS.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');

  empresas = await Shell.chamarApi('/empresas');
  if (empresas === null) return;
  document.getElementById('filtro-empresa').innerHTML =
    '<option value="">Todas</option>' + empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

  const supervisores = await Shell.chamarApi('/supervisores');
  if (supervisores === null) return;
  const selectResponsavel = document.getElementById('filtro-responsavel');
  selectResponsavel.innerHTML =
    '<option value="">Todos</option>' + supervisores.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');
  selectResponsavel.value = filtros.responsavel_id;

  renderizarChipsStatus();

  document.getElementById('filtro-empresa').addEventListener('change', async (evento) => {
    filtros.empresa_id = evento.target.value;
    filtros.cliente_id = '';
    await popularClientesDaEmpresa(evento.target.value);
    carregarChamados();
  });

  document.getElementById('filtro-cliente').addEventListener('change', (evento) => {
    filtros.cliente_id = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-tipo').addEventListener('change', (evento) => {
    filtros.tipo = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-responsavel').addEventListener('change', (evento) => {
    filtros.responsavel_id = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-data-inicio').addEventListener('change', (evento) => {
    filtros.data_inicio = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-data-fim').addEventListener('change', (evento) => {
    filtros.data_fim = evento.target.value;
    carregarChamados();
  });

  carregarChamados();
}

iniciar();
