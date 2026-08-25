const auth = Shell.montar('colaboradores', 'Colaboradores');

const filtros = {
  empresa_id: '',
  supervisor_id: '',
  status_filtro: '',
  busca: '',
};

let temporizadorBusca = null;

function montarBarras(container, itens, chaveLabel) {
  container.innerHTML = '';
  if (itens.length === 0) {
    container.innerHTML = '<div class="empty-state">Sem dados ainda.</div>';
    return;
  }
  const maiorTotal = Math.max(...itens.map((i) => i.total), 1);
  itens.forEach((item) => {
    const largura = Math.round((item.total / maiorTotal) * 100);
    const linha = document.createElement('div');
    linha.className = 'breakdown-row';
    linha.innerHTML = `
      <span class="nome-empresa">${item[chaveLabel]}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${largura}%"></div></div>
      <span class="total">${item.total}</span>
    `;
    container.appendChild(linha);
  });
}

async function carregarResumo() {
  try {
    const resumo = await Shell.chamarApi('/colaboradores-dados/resumo');
    if (resumo === null) return;

    const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
    cards[0].textContent = resumo.total;
    cards[1].textContent = resumo.ativos;
    cards[2].textContent = resumo.afastados;
    cards[3].textContent = resumo.admitidos_mes;
    cards[4].textContent = resumo.em_atestado;
    cards[5].textContent = resumo.faltantes_hoje;

    montarBarras(document.getElementById('breakdown-empresa'), resumo.por_empresa, 'empresa');
    montarBarras(document.getElementById('breakdown-supervisor'), resumo.por_supervisor, 'supervisor');
  } catch (erro) {
    document.getElementById('breakdown-empresa').innerHTML =
      '<div class="empty-state">Não foi possível carregar os indicadores agora.</div>';
  }
}

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function montarQueryString() {
  const params = new URLSearchParams();
  if (filtros.empresa_id) params.set('empresa_id', filtros.empresa_id);
  if (filtros.supervisor_id) params.set('supervisor_id', filtros.supervisor_id);
  if (filtros.status_filtro) params.set('status_filtro', filtros.status_filtro);
  if (filtros.busca) params.set('busca', filtros.busca);
  return params.toString();
}

function renderizarTabela(colaboradores) {
  const container = document.getElementById('lista-colaboradores');

  if (colaboradores.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum colaborador encontrado com esses filtros.</div>';
    return;
  }

  const linhas = colaboradores
    .map(
      (c) => `
      <tr>
        <td>${c.registro || '—'}</td>
        <td><a href="/colaborador-detalhe?id=${c.id}">${c.nome}</a></td>
        <td>${c.cargo || '—'}</td>
        <td>${c.contato || '—'}</td>
        <td>${formatarData(c.data_admissao)}</td>
        <td>${c.empresa_nome}</td>
        <td>${c.supervisor_nome || 'Administrativo'}</td>
        <td>${labelStatus(c.status)}</td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Registro</th><th>Nome</th><th>Cargo</th><th>Contato</th><th>Admissão</th><th>Empresa</th><th>Supervisor</th><th>Status</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

function labelStatus(status) {
  if (status === 'ativo') return 'Ativo';
  if (status === 'afastado') return '<span class="badge-inativo">Afastado</span>';
  if (status === 'desligado') return '<span class="badge-inativo">Desligado</span>';
  return status;
}

async function carregarLista() {
  const container = document.getElementById('lista-colaboradores');
  container.innerHTML = '<div class="loading-state">Carregando colaboradores...</div>';
  try {
    const colaboradores = await Shell.chamarApi(`/colaboradores-dados?${montarQueryString()}`);
    if (colaboradores === null) return;
    renderizarTabela(colaboradores);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

let empresasCache = [];
let supervisoresCache = [];

function montarModalColaborador() {
  const html = `
    <div class="modal-overlay" id="colaborador-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo colaborador</h3>
          <button class="modal-close" id="colaborador-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="colaborador-form">
          <div class="field">
            <label for="colaborador-form-empresa">Empresa</label>
            <select id="colaborador-form-empresa" required></select>
          </div>
          <div class="field">
            <label for="colaborador-form-nome">Nome</label>
            <input type="text" id="colaborador-form-nome" required>
          </div>
          <div class="field">
            <label for="colaborador-form-registro">Registro (opcional)</label>
            <input type="text" id="colaborador-form-registro">
          </div>
          <div class="field">
            <label for="colaborador-form-cargo">Cargo (opcional)</label>
            <input type="text" id="colaborador-form-cargo">
          </div>
          <div class="field">
            <label for="colaborador-form-contato">Contato (opcional)</label>
            <input type="text" id="colaborador-form-contato">
          </div>
          <div class="field">
            <label for="colaborador-form-admissao">Data de admissão (opcional)</label>
            <input type="date" id="colaborador-form-admissao">
          </div>
          <div class="field">
            <label for="colaborador-form-supervisor">Supervisor (opcional)</label>
            <select id="colaborador-form-supervisor"><option value="">Administrativo / sem supervisor</option></select>
          </div>
          <div class="error-message" id="colaborador-modal-erro"></div>
          <button type="submit" class="btn-primary" id="colaborador-modal-enviar">Criar colaborador</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('colaborador-modal-fechar').addEventListener('click', fecharModalColaborador);
  document.getElementById('colaborador-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'colaborador-modal-overlay') fecharModalColaborador();
  });
  document.getElementById('colaborador-form').addEventListener('submit', enviarNovoColaborador);
}

function abrirModalColaborador() {
  document.getElementById('colaborador-form').reset();
  document.getElementById('colaborador-modal-erro').classList.remove('visible');
  document.getElementById('colaborador-form-empresa').innerHTML = empresasCache
    .map((e) => `<option value="${e.id}">${e.nome}</option>`)
    .join('');
  document.getElementById('colaborador-form-supervisor').innerHTML =
    '<option value="">Administrativo / sem supervisor</option>' +
    supervisoresCache.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');
  document.getElementById('colaborador-modal-overlay').hidden = false;
}

function fecharModalColaborador() {
  document.getElementById('colaborador-modal-overlay').hidden = true;
}

async function enviarNovoColaborador(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('colaborador-modal-erro');
  const botao = document.getElementById('colaborador-modal-enviar');
  erroBox.classList.remove('visible');

  const supervisorValor = document.getElementById('colaborador-form-supervisor').value;
  const corpo = {
    empresa_id: Number(document.getElementById('colaborador-form-empresa').value),
    nome: document.getElementById('colaborador-form-nome').value,
    registro: document.getElementById('colaborador-form-registro').value || null,
    cargo: document.getElementById('colaborador-form-cargo').value || null,
    contato: document.getElementById('colaborador-form-contato').value || null,
    data_admissao: document.getElementById('colaborador-form-admissao').value || null,
    supervisor_id: supervisorValor ? Number(supervisorValor) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';

  try {
    await Shell.chamarApi('/colaboradores-dados', { method: 'POST', body: corpo });
    fecharModalColaborador();
    carregarResumo();
    carregarLista();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar o colaborador agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar colaborador';
  }
}

async function iniciar() {
  const empresas = await Shell.chamarApi('/empresas');
  if (empresas === null) return;
  empresasCache = empresas;
  document.getElementById('filtro-empresa').innerHTML =
    '<option value="">Todas</option>' + empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

  const supervisores = await Shell.chamarApi('/supervisores');
  if (supervisores === null) return;
  supervisoresCache = supervisores;
  document.getElementById('filtro-supervisor').innerHTML =
    '<option value="">Todos</option>' + supervisores.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');

  document.getElementById('filtro-empresa').addEventListener('change', (evento) => {
    filtros.empresa_id = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-supervisor').addEventListener('change', (evento) => {
    filtros.supervisor_id = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-status').addEventListener('change', (evento) => {
    filtros.status_filtro = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-busca').addEventListener('input', (evento) => {
    clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(() => {
      filtros.busca = evento.target.value;
      carregarLista();
    }, 350);
  });

  carregarResumo();
  carregarLista();
}

montarModalColaborador();
document.getElementById('btn-novo-colaborador').addEventListener('click', abrirModalColaborador);
if (auth.papel !== 'escritorio') {
  document.getElementById('btn-novo-colaborador').hidden = true;
}

iniciar();
