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
        <td>${c.status === 'ativo' ? 'Ativo' : '<span class="badge-inativo">Afastado</span>'}</td>
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

async function iniciar() {
  const empresas = await Shell.chamarApi('/empresas');
  if (empresas === null) return;
  document.getElementById('filtro-empresa').innerHTML =
    '<option value="">Todas</option>' + empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

  const supervisores = await Shell.chamarApi('/supervisores');
  if (supervisores === null) return;
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

iniciar();
