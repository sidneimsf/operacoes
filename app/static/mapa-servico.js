const auth = Shell.montar('mapa-servico', 'Mapa de Serviço · Histórico');

let colaboradoresCache = [];
let clientesCache = [];
let historicoAtual = [];

const CORES_AVATAR = ['#7d5f11', '#2f5b9e', '#8a3fa8', '#1f6b41', '#c13327', '#17354f'];

function corAvatar(nome) {
  let soma = 0;
  for (let i = 0; i < nome.length; i++) soma += nome.charCodeAt(i);
  return CORES_AVATAR[soma % CORES_AVATAR.length];
}

function iniciais(nome) {
  const partes = nome.trim().split(/\s+/);
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function avatarHtml(nome) {
  return `<div class="pessoa-avatar" style="background:${corAvatar(nome)}">${iniciais(nome)}</div>`;
}

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

const DIAS_SEMANA_FILTRO = [
  { chave: 'segunda', label: 'Seg' },
  { chave: 'terca', label: 'Ter' },
  { chave: 'quarta', label: 'Qua' },
  { chave: 'quinta', label: 'Qui' },
  { chave: 'sexta', label: 'Sex' },
  { chave: 'sabado', label: 'Sáb' },
  { chave: 'domingo', label: 'Dom' },
];

let diaSemanaFiltroVinculo = null;

function renderizarTabela(lista) {
  const container = document.getElementById('lista-historico');

  if (lista.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum vínculo encontrado com esses filtros.</div>';
    return;
  }

  const diasComVinculo = new Set(lista.map((h) => h.dia_semana));
  const mostrarFiltroDias = diasComVinculo.size > 1;

  const botoesDiaHtml = DIAS_SEMANA_FILTRO.map((d) => {
    const qtde = lista.filter((h) => h.dia_semana === d.chave).length;
    if (qtde === 0) return '';
    const ativo = diaSemanaFiltroVinculo === d.chave;
    return `<button type="button" class="btn-ghost filtro-dia-vinculo ${ativo ? 'ativo' : ''}" data-dia="${d.chave}">${d.label} (${qtde})</button>`;
  }).join('');

  const listaFiltrada = diaSemanaFiltroVinculo ? lista.filter((h) => h.dia_semana === diaSemanaFiltroVinculo) : lista;
  const maiorDuracao = Math.max(...listaFiltrada.map((h) => h.duracao_dias), 1);

  const cards = listaFiltrada
    .map((h) => {
      const pct = Math.max(4, Math.round((h.duracao_dias / maiorDuracao) * 100));
      return `
      <button type="button" class="vinculo-card" data-horario-id="${h.id}">
        <div class="vinculo-card-topo">
          ${avatarHtml(h.colaborador_nome)}
          <div class="vinculo-card-nomes">
            <div class="vinculo-colaborador">${h.colaborador_nome}</div>
            <div class="vinculo-cliente">${h.cliente_nome}</div>
          </div>
          <span class="vinculo-status ${h.ativo ? 'ativo' : 'encerrado'}">${h.ativo ? 'Ativo' : 'Encerrado'}</span>
        </div>
        <div class="vinculo-card-meta">${h.dia_semana_label} · ${h.turno} (${h.hora_inicio}-${h.hora_fim})</div>
        <div class="vinculo-tenure">
          <div class="vinculo-tenure-track"><div class="vinculo-tenure-fill" style="width:${pct}%"></div></div>
          <span class="vinculo-tenure-label">${h.duracao_texto}</span>
        </div>
        <div class="vinculo-card-datas">${formatarData(h.data_inicio)} → ${h.ativo ? 'atual' : formatarData(h.data_fim)}</div>
      </button>
    `;
    })
    .join('');

  const filtroDiasHtml = mostrarFiltroDias
    ? `
    <div class="filtro-dia-vinculo-linha">
      <button type="button" class="btn-ghost filtro-dia-vinculo ${diaSemanaFiltroVinculo === null ? 'ativo' : ''}" data-dia="">Todos os dias</button>
      ${botoesDiaHtml}
    </div>
  `
    : '';

  container.innerHTML = `
    ${filtroDiasHtml}
    ${listaFiltrada.length > 0 ? `<div class="vinculo-grid">${cards}</div>` : '<div class="empty-state">Nenhum vínculo nesse dia.</div>'}
  `;

  container.querySelectorAll('.filtro-dia-vinculo').forEach((botao) => {
    botao.addEventListener('click', () => {
      diaSemanaFiltroVinculo = botao.dataset.dia || null;
      renderizarTabela(lista);
    });
  });
}

async function carregarHistorico() {
  const container = document.getElementById('lista-historico');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  diaSemanaFiltroVinculo = null;

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
      <div class="meta" style="margin-bottom: 12px;">${registro.dia_semana_label} · ${registro.turno} (${registro.hora_inicio}-${registro.hora_fim})</div>
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
  const card = evento.target.closest('.vinculo-card');
  if (card) abrirModalEventos(card.dataset.horarioId);
});

iniciar();
