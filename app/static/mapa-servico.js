const auth = Shell.montar('mapa-servico', 'Mapa de Serviço · Histórico');

let colaboradoresCache = [];
let clientesCache = [];
let historicoAtual = [];

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function renderizarKpis(lista) {
  const ativos = lista.filter((h) => h.ativo).length;
  const encerrados = lista.filter((h) => !h.ativo).length;
  const media = lista.length > 0 ? Math.round(lista.reduce((s, h) => s + h.duracao_dias, 0) / lista.length) : 0;

  const cards = document.querySelectorAll('#kpi-grid-historico .kpi-card .value');
  cards[0].textContent = ativos;
  cards[1].textContent = encerrados;
  cards[2].textContent = media;
}

function renderizarTabela(lista) {
  const container = document.getElementById('lista-historico');

  if (lista.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum vínculo encontrado com esses filtros.</div>';
    return;
  }

  const linhas = lista
    .map((h) => {
      const situacao = h.ativo
        ? `<span class="aso-badge ok">Ativo</span>`
        : `<span class="aso-badge vencido">Encerrado</span>`;
      return `
      <tr class="linha-historico" data-horario-id="${h.id}" style="cursor: pointer;">
        <td>${h.colaborador_nome}</td>
        <td>${h.cliente_nome}</td>
        <td>${h.dia_semana_label} · ${h.turno} (${h.hora_inicio}-${h.hora_fim})</td>
        <td>${formatarData(h.data_inicio)}</td>
        <td>${h.ativo ? '—' : formatarData(h.data_fim)}</td>
        <td>${h.duracao_texto}</td>
        <td>${situacao}</td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Colaborador</th><th>Cliente</th><th>Dia / Turno</th><th>Início</th><th>Fim</th><th>Duração</th><th>Situação</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarHistorico() {
  const container = document.getElementById('lista-historico');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';

  const params = new URLSearchParams();
  const colaboradorId = document.getElementById('filtro-colaborador').value;
  const clienteId = document.getElementById('filtro-cliente').value;
  const statusVinculo = document.getElementById('filtro-status').value;
  if (colaboradorId) params.set('colaborador_id', colaboradorId);
  if (clienteId) params.set('cliente_id', clienteId);
  params.set('status_vinculo', statusVinculo);

  try {
    const historico = await Shell.chamarApi(`/mapa-servico-historico?${params.toString()}`);
    if (historico === null) return;
    historicoAtual = historico;
    renderizarKpis(historico);
    renderizarTabela(historico);
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

function montarModalEventos() {
  const html = `
    <div class="modal-overlay" id="eventos-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="eventos-modal-titulo">Histórico de mudanças</h3>
          <button class="modal-close" id="eventos-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <div id="eventos-modal-conteudo"><div class="loading-state">Carregando...</div></div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('eventos-modal-fechar').addEventListener('click', () => {
    document.getElementById('eventos-modal-overlay').hidden = true;
  });
  document.getElementById('eventos-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'eventos-modal-overlay') document.getElementById('eventos-modal-overlay').hidden = true;
  });
}

async function abrirModalEventos(horarioId) {
  const registro = historicoAtual.find((h) => h.id === Number(horarioId));
  document.getElementById('eventos-modal-titulo').textContent = `${registro.colaborador_nome} · ${registro.cliente_nome}`;
  document.getElementById('eventos-modal-overlay').hidden = false;
  const conteudo = document.getElementById('eventos-modal-conteudo');
  conteudo.innerHTML = '<div class="loading-state">Carregando...</div>';

  try {
    const eventos = await Shell.chamarApi(`/mapa-servico-historico/${horarioId}/eventos`);
    const labelEvento = { iniciado: 'Início do vínculo', encerrado: 'Fim do vínculo', editado: 'Horário ajustado' };
    const linhas = eventos
      .map((e) => {
        const data = new Date(e.criado_em).toLocaleString('pt-BR');
        return `
        <tr>
          <td>${labelEvento[e.tipo_evento] || e.tipo_evento}</td>
          <td>${data}</td>
          <td>${e.registrado_por}</td>
          <td>${e.motivo || '—'}</td>
        </tr>
      `;
      })
      .join('');
    conteudo.innerHTML = `
      <div class="meta" style="margin-bottom: 12px;">${registro.dia_semana_label} · ${registro.turno} (${registro.hora_inicio}-${registro.hora_fim})</div>
      <table class="table-list">
        <thead><tr><th>Evento</th><th>Quando</th><th>Registrado por</th><th>Motivo</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>
    `;
  } catch (erro) {
    conteudo.innerHTML = '<div class="empty-state">Não foi possível carregar os eventos agora.</div>';
  }
}

async function iniciar() {
  colaboradoresCache = await Shell.chamarApi('/colaboradores-dados');
  clientesCache = await Shell.chamarApi('/clientes-dados');
  if (colaboradoresCache === null || clientesCache === null) return;

  document.getElementById('filtro-colaborador').innerHTML =
    '<option value="">Todos</option>' + colaboradoresCache.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  document.getElementById('filtro-cliente').innerHTML =
    '<option value="">Todos</option>' + clientesCache.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');

  carregarHistorico();
}

montarModalEventos();
document.getElementById('filtro-colaborador').addEventListener('change', carregarHistorico);
document.getElementById('filtro-cliente').addEventListener('change', carregarHistorico);
document.getElementById('filtro-status').addEventListener('change', carregarHistorico);
document.getElementById('lista-historico').addEventListener('click', (evento) => {
  const linha = evento.target.closest('.linha-historico');
  if (linha) abrirModalEventos(linha.dataset.horarioId);
});

iniciar();
