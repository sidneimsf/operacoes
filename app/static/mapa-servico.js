const auth = Shell.montar('mapa-servico', 'Mapa de Serviço · Histórico');

let colaboradoresCache = [];
let clientesCache = [];
let historicoAtual = [];

function popularIconesEstaticos() {
  document.querySelectorAll('[data-icone]').forEach((el) => {
    el.innerHTML = Shell.icone(el.dataset.icone);
  });
}

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

const DIAS_PADRAO = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado'];
const DIAS_LABEL = {
  segunda: 'Segunda', terca: 'Terça', quarta: 'Quarta', quinta: 'Quinta',
  sexta: 'Sexta', sabado: 'Sábado', domingo: 'Domingo',
};

// Mesmo formato da grade "Mapa de serviço da semana" do colaborador.
// Com um colaborador filtrado mostra o cliente; com um cliente filtrado
// mostra o colaborador; sem filtro mostra os dois.
function nomeNaCelula(registro) {
  const filtrouColaborador = document.getElementById('filtro-colaborador').value;
  const filtrouCliente = document.getElementById('filtro-cliente').value;
  if (filtrouColaborador && !filtrouCliente) return registro.cliente_nome;
  if (filtrouCliente && !filtrouColaborador) return registro.colaborador_nome;
  if (filtrouCliente && filtrouColaborador) return registro.cliente_nome;
  return `${registro.colaborador_nome}<span class="horario-celula-sub">${registro.cliente_nome}</span>`;
}

function celulaHorarioHtml(registros) {
  const lista = (registros || []).slice().sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  if (lista.length === 0) return '<td><span class="horario-celula-vazia">—</span></td>';
  const itensHtml = lista
    .map(
      (registro) => `
      <div class="horario-celula ${registro.ativo ? '' : 'encerrado'}" data-horario-id="${registro.id}" title="${registro.duracao_texto}">
        <span class="nome">${nomeNaCelula(registro)}</span>
        <span class="hora">${registro.hora_inicio}-${registro.hora_fim}${registro.ativo ? '' : ' · encerrado'}</span>
      </div>
    `
    )
    .join('');
  return `<td>${itensHtml}</td>`;
}

function renderizarTabela(lista) {
  const container = document.getElementById('lista-historico');

  if (lista.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum vínculo encontrado com esses filtros.</div>';
    return;
  }

  const dias = [...DIAS_PADRAO];
  if (lista.some((h) => h.dia_semana === 'domingo')) dias.push('domingo');

  const porDiaTurno = {};
  lista.forEach((h) => {
    const chave = `${h.dia_semana}_${h.turno}`;
    if (!porDiaTurno[chave]) porDiaTurno[chave] = [];
    porDiaTurno[chave].push(h);
  });

  const headerCols = dias.map((d) => `<th>${DIAS_LABEL[d]}</th>`).join('');
  const linha = (turno) => dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_${turno}`])).join('');

  container.innerHTML = `
    <table class="horario-grid">
      <thead><tr><th></th>${headerCols}</tr></thead>
      <tbody>
        <tr><td>Manhã</td>${linha('manha')}</tr>
        <tr><td>Tarde</td>${linha('tarde')}</tr>
        <tr><td>Noite</td>${linha('noite')}</tr>
      </tbody>
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
        <div class="timeline-item">
          <div class="data-col">${data}</div>
          <div class="conteudo">
            <div class="linha-topo">
              <span class="evento-tipo-badge ${e.tipo_evento}">${labelEvento[e.tipo_evento] || e.tipo_evento}</span>
            </div>
            ${e.motivo ? `<div class="descricao">${e.motivo}</div>` : ''}
            <div class="meta">Registrado por ${e.registrado_por}</div>
          </div>
        </div>
      `;
      })
      .join('');
    conteudo.innerHTML = `
      <div class="meta" style="margin-bottom: 12px;">${registro.dia_semana_label} · ${registro.turno} (${registro.hora_inicio}-${registro.hora_fim}) · ${formatarData(registro.data_inicio)} → ${registro.ativo ? 'atual' : formatarData(registro.data_fim)} · ${registro.duracao_texto}</div>
      ${linhas || '<div class="empty-state">Nenhum evento registrado.</div>'}
    `;
  } catch (erro) {
    conteudo.innerHTML = '<div class="empty-state">Não foi possível carregar os eventos agora.</div>';
  }
}

async function iniciar() {
  popularIconesEstaticos();
  colaboradoresCache = await Shell.chamarApi('/colaboradores-dados?incluir_posto_vago=true');
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
  const celula = evento.target.closest('.horario-celula');
  if (celula) abrirModalEventos(celula.dataset.horarioId);
});

iniciar();
