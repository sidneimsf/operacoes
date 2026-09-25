const auth = Shell.montar('crm', 'CRM');

const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const ROTULO_TENDENCIA = { piorando: '↘ piorando', melhorando: '↗ melhorando', estavel: '→ estável' };

const ABAS = ['visao-geral', 'resumo', 'saude', 'contratos', 'satisfacao'];
let abaAtual = 'visao-geral';
let carteira = null;
let satisfacao = null;
let constantes = null;
let filtroContratos = 'todos';

function escaparHtml(texto) {
  if (texto === null || texto === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(texto);
  return div.innerHTML;
}

function formatarMoeda(valor) {
  return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarDataBR(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

function rotuloMes(chave) {
  const [ano, mes] = chave.split('-');
  return `${MESES_CURTOS[Number(mes) - 1]}/${ano.slice(2)}`;
}

function formatarNps(nps) {
  if (nps === null || nps === undefined) return '—';
  return nps > 0 ? `+${nps}` : String(nps);
}

function pct(parte, total) {
  return total ? Math.round((parte * 100) / total) : 0;
}

function linkFicha(clienteId, ancora = '') {
  return `/crm-cliente?id=${clienteId}${ancora}`;
}

function badgeScore(linha) {
  return `<span class="crm-score ${linha.faixa}" title="${escaparHtml(linha.faixa_label)}">${linha.score}</span>`;
}

function kpi(label, valor, sub = '', classe = '') {
  return `
    <div class="kpi-card ${classe}">
      <div>
        <div class="label">${label}</div>
        <div class="value">${valor}</div>
        ${sub ? `<div class="sub">${sub}</div>` : ''}
      </div>
    </div>
  `;
}

function listaInsights(insights) {
  if (!insights.length) return '<div class="empty-state">Sem leituras para mostrar.</div>';
  return `<ul class="crm-insights">${insights.map((i) => `<li class="crm-insight ${i.nivel}">${escaparHtml(i.texto)}</li>`).join('')}</ul>`;
}

function cartao(titulo, icone, conteudo, contador = '') {
  return `
    <div class="dash-card" style="margin-bottom: 18px;">
      <div class="dash-card-header">
        <div class="dash-card-icon">${Shell.icone(icone)}</div>
        <h3>${titulo}</h3>
        ${contador ? `<span class="dash-card-count">${contador}</span>` : ''}
      </div>
      ${conteudo}
    </div>
  `;
}

function tabela(cabecalhos, linhasHtml, compacta = false) {
  return `
    <div class="table-scroll-wrapper">
      <table class="table-list"${compacta ? ' style="min-width:0;"' : ''}>
        <thead><tr>${cabecalhos.map((c) => `<th>${c}</th>`).join('')}</tr></thead>
        <tbody>${linhasHtml}</tbody>
      </table>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Carregamento
// ---------------------------------------------------------------------------

async function carregarCarteira(forcar = false) {
  if (carteira && !forcar) return carteira;
  carteira = await Shell.chamarApi('/crm-dados/carteira');
  const hora = new Date(carteira.gerado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  document.getElementById('crm-atualizado-em').textContent =
    `${carteira.indicadores.clientes} clientes ativos analisados · atualizado às ${hora}`;
  return carteira;
}

async function carregarConstantes() {
  if (!constantes) constantes = await Shell.chamarApi('/crm-constantes');
  return constantes;
}

async function renderizarAbaAtual(forcar = false) {
  const container = document.getElementById(`aba-${abaAtual}`);
  try {
    if (abaAtual === 'resumo') {
      await carregarResumoDia(forcar);
      return;
    }
    if (abaAtual === 'satisfacao') {
      if (!satisfacao || forcar) {
        container.innerHTML = '<div class="loading-state">Carregando avaliações...</div>';
        satisfacao = await Shell.chamarApi('/crm-dados/satisfacao');
      }
      await carregarCarteira(forcar);
      renderizarSatisfacao();
      return;
    }
    await carregarCarteira(forcar);
    await carregarConstantes();
    if (abaAtual === 'visao-geral') renderizarVisaoGeral();
    else if (abaAtual === 'saude') renderizarSaude();
    else if (abaAtual === 'contratos') renderizarContratos();
  } catch (erro) {
    container.innerHTML = `<div class="error-message visible">${escaparHtml(erro.detalhe || 'Não foi possível carregar o CRM agora.')}</div>`;
  }
}

function trocarAba(aba) {
  abaAtual = aba;
  document.querySelectorAll('.tab-relatorio').forEach((botao) => {
    botao.classList.toggle('ativa', botao.dataset.aba === aba);
  });
  ABAS.forEach((nome) => {
    document.getElementById(`aba-${nome}`).hidden = nome !== aba;
  });
  // o resumo do dia tem barra propria (data e PDF)
  document.getElementById('crm-toolbar').hidden = aba === 'resumo';
  history.replaceState(null, '', `#${aba}`);
  renderizarAbaAtual();
}

// ---------------------------------------------------------------------------
// Visao geral
// ---------------------------------------------------------------------------

function renderizarVisaoGeral() {
  const i = carteira.indicadores;
  const total = i.clientes || 1;

  const kpis = `
    <div class="kpi-grid">
      ${kpi('nota média da carteira', i.score_medio ?? '—', `${i.saudaveis} saudáveis · ${i.atencao} em atenção · ${i.em_risco} em risco`)}
      ${kpi('clientes em risco', i.em_risco, i.receita_em_risco ? `${formatarMoeda(i.receita_em_risco)}/mês em jogo` : 'nota abaixo de 50', i.em_risco ? 'kpi-risco' : 'kpi-saudavel')}
      ${kpi('receita mensal cadastrada', formatarMoeda(i.receita_mensal), `${i.clientes_com_valor} de ${i.clientes} clientes com valor de contrato`)}
      ${kpi('contratos vencendo em 90 dias', i.contratos_vencendo_90d, i.receita_vencendo_90d ? `${formatarMoeda(i.receita_vencendo_90d)}/mês a renovar` : 'renovação a negociar', i.contratos_vencendo_90d ? 'kpi-atencao' : '')}
      ${kpi('reajustes pendentes', i.reajustes_pendentes, 'atrasados ou em até 30 dias', i.reajustes_pendentes ? 'kpi-risco' : '')}
      ${kpi('NPS da carteira', formatarNps(i.nps), i.nps_base ? `${i.nps_base} clientes avaliados em 12 meses` : 'nenhuma avaliação ainda')}
    </div>
  `;

  const distribuicao = `
    <div class="crm-distribuicao">
      <div class="saudavel" style="width:${pct(i.saudaveis, total)}%"></div>
      <div class="atencao" style="width:${pct(i.atencao, total)}%"></div>
      <div class="risco" style="width:${pct(i.em_risco, total)}%"></div>
    </div>
    <div class="crm-legenda">
      <span><i class="saudavel"></i>Saudável (75+): <b>${i.saudaveis}</b> · ${pct(i.saudaveis, total)}%</span>
      <span><i class="atencao"></i>Atenção (50–74): <b>${i.atencao}</b> · ${pct(i.atencao, total)}%</span>
      <span><i class="risco"></i>Em risco (&lt;50): <b>${i.em_risco}</b> · ${pct(i.em_risco, total)}%</span>
      <span>Tendência 45 dias: <b class="crm-tendencia piorando">${i.piorando} piorando</b> · <b class="crm-tendencia melhorando">${i.melhorando} melhorando</b></span>
    </div>
  `;

  const prioridades = carteira.prioridades.length
    ? carteira.prioridades.map((p) => `
        <a class="crm-prioridade" href="${linkFicha(p.cliente_id)}">
          <span class="urgencia ${p.urgencia}"></span>
          <span class="titulo">${escaparHtml(p.cliente_nome)}<small>${escaparHtml(p.empresa_nome)}${p.supervisor_nome ? ` · ${escaparHtml(p.supervisor_nome)}` : ''}</small></span>
          <span>${p.valor_mensal ? `<span class="mono" style="font-size:12.5px;color:var(--text-muted);margin-right:8px;">${formatarMoeda(p.valor_mensal)}/mês</span>` : ''}<span class="crm-score ${p.score >= 75 ? 'saudavel' : p.score >= 50 ? 'atencao' : 'risco'}">${p.score}</span></span>
          <span class="detalhe">${escaparHtml(p.motivo)} → <b>${escaparHtml(p.acao)}</b></span>
        </a>
      `).join('')
    : '<div class="empty-state">Nenhum cliente em risco nem contrato pedindo ação. Carteira sob controle.</div>';

  const linhasEmpresa = carteira.por_empresa.map((g) => `
    <tr>
      <td>${escaparHtml(g.nome)}</td>
      <td>${g.clientes}</td>
      <td><span class="crm-score ${g.score_medio >= 75 ? 'saudavel' : g.score_medio >= 50 ? 'atencao' : 'risco'}">${g.score_medio}</span></td>
      <td>${g.em_risco ? `<b style="color:var(--crm-risco)">${g.em_risco}</b>` : '0'} / ${g.atencao}</td>
      <td>${g.receita_mensal ? formatarMoeda(g.receita_mensal) : '—'}</td>
    </tr>
  `).join('');

  const linhasSupervisor = carteira.por_supervisor.map((g) => `
    <tr>
      <td>${escaparHtml(g.nome)}</td>
      <td>${g.clientes}</td>
      <td><span class="crm-score ${g.score_medio >= 75 ? 'saudavel' : g.score_medio >= 50 ? 'atencao' : 'risco'}">${g.score_medio}</span></td>
      <td>${g.em_risco ? `<b style="color:var(--crm-risco)">${g.em_risco}</b>` : '0'} / ${g.atencao}</td>
      <td>${g.sem_visita_30d} <span style="color:var(--text-muted);font-size:12px;">(${pct(g.sem_visita_30d, g.clientes)}%)</span></td>
    </tr>
  `).join('');

  document.getElementById('aba-visao-geral').innerHTML = `
    ${kpis}
    ${cartao('Leitura da carteira', 'relatorios', listaInsights(carteira.insights))}
    ${cartao('Distribuição de saúde', 'crm', distribuicao)}
    ${cartao('Prioridades da semana', 'ocorrencias', prioridades,
      carteira.total_prioridades > carteira.prioridades.length ? `${carteira.prioridades.length} de ${carteira.total_prioridades}` : String(carteira.total_prioridades))}
    <div class="dash-grid" style="margin-top: 0;">
      ${cartao('Por empresa', 'empresas', tabela(['Empresa', 'Clientes', 'Nota média', 'Risco / atenção', 'Receita/mês'], linhasEmpresa, true))}
      ${cartao('Por supervisor', 'supervisao', tabela(['Supervisor', 'Clientes', 'Nota média', 'Risco / atenção', 'Sem visita 30d+'], linhasSupervisor, true))}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Saude da carteira (lista completa com filtros)
// ---------------------------------------------------------------------------

const filtrosSaude = { busca: '', empresa: '', supervisor: '', faixa: '', tendencia: '', ordem: 'nota' };

function opcoesUnicas(chaveId, chaveNome) {
  const mapa = new Map();
  carteira.clientes.forEach((c) => {
    if (c[chaveId] !== null) mapa.set(String(c[chaveId]), c[chaveNome]);
  });
  return [...mapa.entries()].sort((a, b) => a[1].localeCompare(b[1]));
}

function explicacaoNota() {
  const linhas = [
    ['Reclamações do cliente (chamados do tipo reclamação) nos últimos 90 dias', '−10 cada, até −30'],
    ['Dias sem visita de supervisão', '31–60 dias: −10 · +60 ou nunca: −20'],
    ['Turnos vagos na escala semanal (Mapa de Serviço)', '−8 cada, até −20'],
    ['Última avaliação de satisfação (12 meses)', '0–6: −20 · 7–8: −5'],
    ['Colaboradores que saíram do posto em 90 dias', '2: −5 · 3–4: −10 · 5+: −15'],
    ['Chamados abertos há mais de 7 dias', '−5 cada, até −15'],
    ['Faltas cobertas com diária em 90 dias', '3–5: −5 · 6+: −10'],
    ['Postos contratados sem colaborador (quando o contrato informa)', '−5 cada, até −15'],
  ];
  return `
    <details class="crm-como-funciona">
      <summary>Como a nota de saúde é calculada?</summary>
      <p style="color:var(--text-muted);margin:10px 0 0;">Todo cliente começa com 100 pontos e perde pontos por sinal de problema registrado no sistema.
      <b>75+ saudável</b>, <b>50–74 atenção</b>, <b>abaixo de 50 em risco</b>. A tendência compara reclamações, faltas e saídas de colaboradores
      dos últimos 45 dias com os 45 dias anteriores.</p>
      <table>${linhas.map(([sinal, peso]) => `<tr><td>${sinal}</td><td>${peso}</td></tr>`).join('')}</table>
    </details>
  `;
}

function renderizarSaude() {
  const container = document.getElementById('aba-saude');
  if (!container.dataset.montado) {
    container.dataset.montado = '1';
    const selectEmpresa = opcoesUnicas('empresa_id', 'empresa_nome').map(([id, nome]) => `<option value="${id}">${escaparHtml(nome)}</option>`).join('');
    const selectSupervisor = opcoesUnicas('supervisor_id', 'supervisor_nome').map(([id, nome]) => `<option value="${id}">${escaparHtml(nome)}</option>`).join('');
    container.innerHTML = `
      ${explicacaoNota()}
      <div class="filter-row">
        <div class="field"><label for="saude-busca">Buscar cliente</label><input type="text" id="saude-busca" placeholder="Nome do cliente..." style="padding:10px 12px;font-size:14px;"></div>
        <div class="field"><label for="saude-empresa">Empresa</label><select id="saude-empresa"><option value="">Todas</option>${selectEmpresa}</select></div>
        <div class="field"><label for="saude-supervisor">Supervisor</label><select id="saude-supervisor"><option value="">Todos</option><option value="sem">Sem supervisor</option>${selectSupervisor}</select></div>
        <div class="field"><label for="saude-faixa">Faixa</label><select id="saude-faixa"><option value="">Todas</option><option value="risco">Em risco</option><option value="atencao">Atenção</option><option value="saudavel">Saudável</option></select></div>
        <div class="field"><label for="saude-tendencia">Tendência</label><select id="saude-tendencia"><option value="">Todas</option><option value="piorando">Piorando</option><option value="melhorando">Melhorando</option><option value="estavel">Estável</option></select></div>
        <div class="field"><label for="saude-ordem">Ordenar por</label><select id="saude-ordem"><option value="nota">Pior nota primeiro</option><option value="receita">Maior receita primeiro</option><option value="visita">Mais tempo sem visita</option><option value="nome">Nome</option></select></div>
      </div>
      <div class="meta" id="saude-resumo-filtro" style="margin-bottom:10px;font-size:13px;color:var(--text-muted);"></div>
      <div id="saude-tabela"></div>
    `;
    const ligar = (id, chave, evento = 'change') => {
      document.getElementById(id).addEventListener(evento, (e) => {
        filtrosSaude[chave] = e.target.value;
        desenharTabelaSaude();
      });
    };
    // ao recarregar os dados a tela e remontada - mantem os filtros que ja estavam escolhidos
    document.getElementById('saude-busca').value = filtrosSaude.busca;
    ['empresa', 'supervisor', 'faixa', 'tendencia', 'ordem'].forEach((chave) => {
      document.getElementById(`saude-${chave}`).value = filtrosSaude[chave];
    });
    ligar('saude-busca', 'busca', 'input');
    ligar('saude-empresa', 'empresa');
    ligar('saude-supervisor', 'supervisor');
    ligar('saude-faixa', 'faixa');
    ligar('saude-tendencia', 'tendencia');
    ligar('saude-ordem', 'ordem');
    document.getElementById('saude-tabela').addEventListener('click', (evento) => {
      const linha = evento.target.closest('tr[data-id]');
      if (linha) window.location.href = linkFicha(linha.dataset.id);
    });
  }
  desenharTabelaSaude();
}

function desenharTabelaSaude() {
  const termo = filtrosSaude.busca.trim().toLowerCase();
  let lista = carteira.clientes.filter((c) => {
    if (termo && !c.cliente_nome.toLowerCase().includes(termo)) return false;
    if (filtrosSaude.empresa && String(c.empresa_id) !== filtrosSaude.empresa) return false;
    if (filtrosSaude.supervisor === 'sem' && c.supervisor_id !== null) return false;
    if (filtrosSaude.supervisor && filtrosSaude.supervisor !== 'sem' && String(c.supervisor_id) !== filtrosSaude.supervisor) return false;
    if (filtrosSaude.faixa && c.faixa !== filtrosSaude.faixa) return false;
    if (filtrosSaude.tendencia && c.tendencia !== filtrosSaude.tendencia) return false;
    return true;
  });

  const valorMensal = (c) => (c.contrato && c.contrato.valor_mensal) || 0;
  const diasVisita = (c) => (c.sinais.dias_sem_visita === null ? Infinity : c.sinais.dias_sem_visita);
  const ordenadores = {
    nota: (a, b) => a.score - b.score || valorMensal(b) - valorMensal(a),
    receita: (a, b) => valorMensal(b) - valorMensal(a) || a.score - b.score,
    visita: (a, b) => diasVisita(b) - diasVisita(a),
    nome: (a, b) => a.cliente_nome.localeCompare(b.cliente_nome),
  };
  lista = [...lista].sort(ordenadores[filtrosSaude.ordem]);

  const media = lista.length ? Math.round(lista.reduce((s, c) => s + c.score, 0) / lista.length) : 0;
  const risco = lista.filter((c) => c.faixa === 'risco').length;
  document.getElementById('saude-resumo-filtro').textContent = lista.length
    ? `${lista.length} clientes · nota média ${media} · ${risco} em risco`
    : '';

  if (!lista.length) {
    document.getElementById('saude-tabela').innerHTML = '<div class="empty-state">Nenhum cliente com esses filtros.</div>';
    return;
  }

  const linhas = lista.map((c) => {
    const motivos = c.motivos.slice(0, 3).map((m) => `<li><span class="impacto">−${m.impacto}</span>${escaparHtml(m.texto)}</li>`).join('');
    const visita = c.sinais.dias_sem_visita === null ? 'nunca' : `há ${c.sinais.dias_sem_visita}d`;
    return `
      <tr class="crm-linha-clicavel" data-id="${c.cliente_id}">
        <td><b>${escaparHtml(c.cliente_nome)}</b><div style="font-size:12px;color:var(--text-muted);">${escaparHtml(c.empresa_nome)}${c.contrato && c.contrato.valor_mensal ? ` · ${formatarMoeda(c.contrato.valor_mensal)}/mês` : ''}</div></td>
        <td>${badgeScore(c)}</td>
        <td><span class="crm-tendencia ${c.tendencia}">${ROTULO_TENDENCIA[c.tendencia]}</span></td>
        <td style="min-width:240px;">${motivos ? `<ul class="crm-motivos">${motivos}</ul>` : '<span style="color:var(--crm-saudavel);font-size:13px;">Nenhum sinal de problema</span>'}</td>
        <td style="min-width:200px;"><span class="crm-acao">${escaparHtml(c.acao_sugerida)}</span></td>
        <td>${escaparHtml(c.supervisor_nome || '—')}<div style="font-size:12px;color:var(--text-muted);">visita ${visita}</div></td>
      </tr>
    `;
  }).join('');

  document.getElementById('saude-tabela').innerHTML = tabela(
    ['Cliente', 'Nota', 'Tendência', 'Por que essa nota', 'Próxima ação', 'Supervisor'], linhas
  );
}

// ---------------------------------------------------------------------------
// Contratos
// ---------------------------------------------------------------------------

function renderizarContratos() {
  const clientes = carteira.clientes;
  const comContrato = clientes.filter((c) => c.contrato);
  const comValor = comContrato.filter((c) => c.contrato.valor_mensal);
  const receita = comValor.reduce((s, c) => s + c.contrato.valor_mensal, 0);
  const ticketMedio = comValor.length ? receita / comValor.length : 0;
  const postosContratados = comContrato.reduce((s, c) => s + (c.contrato.postos_contratados || 0), 0);

  const alertas = [];
  clientes.forEach((c) => c.alertas_contrato.forEach((a) => alertas.push({ cliente: c, alerta: a })));
  const ordemUrgencia = { alta: 0, media: 1, baixa: 2 };
  alertas.sort((x, y) => ordemUrgencia[x.alerta.urgencia] - ordemUrgencia[y.alerta.urgencia] || x.alerta.dias - y.alerta.dias);

  const kpis = `
    <div class="kpi-grid">
      ${kpi('contratos cadastrados', `${comContrato.length}<span style="font-size:15px;color:var(--text-muted);"> / ${clientes.length}</span>`, `${pct(comContrato.length, clientes.length)}% da carteira`)}
      ${kpi('receita mensal', formatarMoeda(receita), `${formatarMoeda(receita * 12)} por ano`)}
      ${kpi('ticket médio', formatarMoeda(ticketMedio), `média de ${comValor.length} contratos com valor`)}
      ${kpi('postos contratados', postosContratados || '—', 'soma dos contratos cadastrados')}
      ${kpi('pedindo ação', alertas.filter((a) => a.alerta.urgencia === 'alta').length, 'vencidos, vencendo em 30 dias ou reajuste', alertas.some((a) => a.alerta.urgencia === 'alta') ? 'kpi-risco' : '')}
    </div>
  `;

  const listaAlertas = alertas.length
    ? alertas.map(({ cliente, alerta }) => `
        <a class="crm-prioridade" href="${linkFicha(cliente.cliente_id, '#contrato')}">
          <span class="urgencia ${alerta.urgencia === 'alta' ? 'alta' : ''}"></span>
          <span class="titulo">${escaparHtml(cliente.cliente_nome)}<small>${escaparHtml(cliente.empresa_nome)}</small></span>
          <span>${cliente.contrato.valor_mensal ? `<span class="mono" style="font-size:12.5px;color:var(--text-muted);margin-right:8px;">${formatarMoeda(cliente.contrato.valor_mensal)}/mês</span>` : ''}${badgeScore(cliente)}</span>
          <span class="detalhe"><span class="crm-alerta ${alerta.urgencia}">${escaparHtml(alerta.texto)}</span>
            ${alerta.tipo === 'vigencia' && cliente.faixa !== 'saudavel' ? ` <b>Atenção: saúde ${cliente.faixa_label.toLowerCase()} — resolva os problemas antes de negociar.</b>` : ''}</span>
        </a>
      `).join('')
    : '<div class="empty-state">Nenhum vencimento ou reajuste nos próximos 90 dias.</div>';

  let lista = clientes;
  if (filtroContratos === 'alerta') lista = clientes.filter((c) => c.alertas_contrato.length);
  if (filtroContratos === 'sem') lista = clientes.filter((c) => !c.contrato);
  lista = [...lista].sort((a, b) => ((b.contrato && b.contrato.valor_mensal) || 0) - ((a.contrato && a.contrato.valor_mensal) || 0) || a.cliente_nome.localeCompare(b.cliente_nome));

  const linhas = lista.map((c) => {
    const k = c.contrato;
    if (!k) {
      return `
        <tr class="crm-linha-clicavel" data-id="${c.cliente_id}" data-ancora="#contrato">
          <td><b>${escaparHtml(c.cliente_nome)}</b><div style="font-size:12px;color:var(--text-muted);">${escaparHtml(c.empresa_nome)}</div></td>
          <td colspan="4"><span class="crm-pendencia">Sem contrato cadastrado</span> <a href="${linkFicha(c.cliente_id, '#contrato')}" style="font-size:13px;">cadastrar</a></td>
          <td>${badgeScore(c)}</td>
          <td></td>
        </tr>
      `;
    }
    const efetivos = c.sinais.colaboradores_efetivos;
    const postos = k.postos_contratados
      ? `${efetivos} / ${k.postos_contratados}${efetivos < k.postos_contratados ? ' <span style="color:var(--crm-risco);">▼</span>' : ''}`
      : '—';
    return `
      <tr class="crm-linha-clicavel" data-id="${c.cliente_id}" data-ancora="#contrato">
        <td><b>${escaparHtml(c.cliente_nome)}</b><div style="font-size:12px;color:var(--text-muted);">${escaparHtml(c.empresa_nome)}</div></td>
        <td>${k.valor_mensal ? formatarMoeda(k.valor_mensal) : '<span class="crm-pendencia">sem valor</span>'}</td>
        <td>${formatarDataBR(k.data_inicio)} → ${formatarDataBR(k.data_fim)}${k.renovacao_automatica ? '<div style="font-size:12px;color:var(--text-muted);">renovação automática</div>' : ''}</td>
        <td>${formatarDataBR(k.data_reajuste)}${k.indice_reajuste_label ? `<div style="font-size:12px;color:var(--text-muted);">${escaparHtml(k.indice_reajuste_label)}</div>` : ''}</td>
        <td>${postos}</td>
        <td>${badgeScore(c)}</td>
        <td>${c.alertas_contrato.map((a) => `<span class="crm-alerta ${a.urgencia}">${escaparHtml(a.texto)}</span>`).join('')}</td>
      </tr>
    `;
  }).join('');

  const chips = [['todos', 'Todos'], ['alerta', 'Com alerta'], ['sem', 'Sem contrato']]
    .map(([chave, label]) => `<button class="chip${filtroContratos === chave ? ' active' : ''}" data-filtro="${chave}">${label}</button>`)
    .join('');

  const container = document.getElementById('aba-contratos');
  container.innerHTML = `
    ${kpis}
    ${cartao('Vencimentos e reajustes', 'agendar', listaAlertas, String(alertas.length))}
    <div class="chips" id="contratos-filtro">${chips}</div>
    ${lista.length ? tabela(['Cliente', 'Valor mensal', 'Vigência', 'Próximo reajuste', 'Postos (alocados / contratados)', 'Saúde', 'Alertas'], linhas) : '<div class="empty-state">Nenhum cliente nesse filtro.</div>'}
  `;

  container.querySelector('#contratos-filtro').addEventListener('click', (evento) => {
    const botao = evento.target.closest('[data-filtro]');
    if (!botao) return;
    filtroContratos = botao.dataset.filtro;
    renderizarContratos();
  });
  container.querySelectorAll('tr[data-id]').forEach((linha) => {
    linha.addEventListener('click', (evento) => {
      if (evento.target.closest('a')) return;
      window.location.href = linkFicha(linha.dataset.id, linha.dataset.ancora || '');
    });
  });
}

// ---------------------------------------------------------------------------
// Satisfacao (NPS)
// ---------------------------------------------------------------------------

function renderizarSatisfacao() {
  const s = satisfacao;
  const avaliados = s.avaliados || 1;

  const kpis = `
    <div class="kpi-grid">
      ${kpi('NPS da carteira', formatarNps(s.nps), 'de −100 a +100 · acima de +50 é muito bom', s.nps === null ? '' : s.nps >= 50 ? 'kpi-saudavel' : s.nps >= 0 ? 'kpi-atencao' : 'kpi-risco')}
      ${kpi('clientes avaliados', `${s.avaliados}<span style="font-size:15px;color:var(--text-muted);"> / ${s.total_clientes}</span>`, `${pct(s.avaliados, s.total_clientes)}% da carteira em 12 meses`)}
      ${kpi('nota média', s.media_notas ?? '—', 'última nota de cada cliente')}
      ${kpi('detratores a tratar', s.detratores, 'nota 6 ou menos na última avaliação', s.detratores ? 'kpi-risco' : '')}
    </div>
  `;

  const composicao = s.avaliados
    ? `
      <div class="crm-distribuicao">
        <div class="promotor" style="width:${pct(s.promotores, avaliados)}%"></div>
        <div class="neutro" style="width:${pct(s.neutros, avaliados)}%"></div>
        <div class="detrator" style="width:${pct(s.detratores, avaliados)}%"></div>
      </div>
      <div class="crm-legenda">
        <span><i class="promotor"></i>Promotores (9–10): <b>${s.promotores}</b> · ${pct(s.promotores, avaliados)}%</span>
        <span><i class="neutro"></i>Neutros (7–8): <b>${s.neutros}</b> · ${pct(s.neutros, avaliados)}%</span>
        <span><i class="detrator"></i>Detratores (0–6): <b>${s.detratores}</b> · ${pct(s.detratores, avaliados)}%</span>
      </div>
    `
    : '<div class="empty-state">Registre avaliações na ficha de cada cliente para ver a composição.</div>';

  const colunas = s.evolucao_mensal.map((m) => {
    const altura = m.media !== null ? Math.max(4, Math.round((m.media / 10) * 100)) : 4;
    return `
      <div class="crm-coluna" title="${m.respostas} resposta(s)${m.nps !== null ? ` · NPS ${formatarNps(m.nps)}` : ''}">
        <span class="valor">${m.media !== null ? m.media.toLocaleString('pt-BR') : ''}</span>
        <div class="barras"><div class="barra ${m.media === null ? 'vazia' : ''}" style="height:${altura}%"></div></div>
        <span class="rotulo">${rotuloMes(m.mes)}</span>
        <span class="rotulo">${m.respostas ? `${m.respostas} resp.` : '—'}</span>
      </div>
    `;
  }).join('');

  const linhasEmpresa = s.por_empresa.map((g) => `
    <tr><td>${escaparHtml(g.empresa)}</td><td>${formatarNps(g.nps)}</td><td>${g.avaliados} / ${g.clientes} <span style="color:var(--text-muted);font-size:12px;">(${g.cobertura_pct}%)</span></td></tr>
  `).join('');

  const detratores = s.detratores_a_tratar.length
    ? s.detratores_a_tratar.map((p) => `
        <a class="crm-prioridade" href="${linkFicha(p.cliente_id, '#satisfacao')}">
          <span class="urgencia alta"></span>
          <span class="titulo">${escaparHtml(p.cliente_nome)}<small>${escaparHtml(p.empresa_nome)} · ${formatarDataBR(p.data_pesquisa)}</small></span>
          <span class="crm-nota-pilula detrator">${p.nota}</span>
          <span class="detalhe">${p.comentario ? `“${escaparHtml(p.comentario)}”` : 'Sem comentário registrado'}${p.respondido_por ? ` — ${escaparHtml(p.respondido_por)}` : ''}</span>
        </a>
      `).join('')
    : '<div class="empty-state">Nenhum detrator na última avaliação de cada cliente.</div>';

  // quem esta em risco e sem avaliacao vem primeiro: e onde a pesquisa mais ajuda
  const saudePorCliente = new Map(carteira.clientes.map((c) => [c.cliente_id, c]));
  const semPesquisa = [...s.sem_pesquisa].sort((a, b) => {
    const sa = saudePorCliente.get(a.cliente_id);
    const sb = saudePorCliente.get(b.cliente_id);
    return (sa ? sa.score : 100) - (sb ? sb.score : 100);
  });
  const linhasSemPesquisa = semPesquisa.slice(0, 30).map((c) => {
    const saude = saudePorCliente.get(c.cliente_id);
    return `
      <tr class="crm-linha-clicavel" data-id="${c.cliente_id}">
        <td><b>${escaparHtml(c.cliente_nome)}</b><div style="font-size:12px;color:var(--text-muted);">${escaparHtml(c.empresa_nome)}</div></td>
        <td>${saude ? badgeScore(saude) : '—'}</td>
        <td>${c.ultima_pesquisa ? formatarDataBR(c.ultima_pesquisa) : 'nunca'}</td>
        <td>${escaparHtml(c.supervisor_nome || '—')}</td>
      </tr>
    `;
  }).join('');

  const linhasRespostas = s.respostas_recentes.map((p) => `
    <tr class="crm-linha-clicavel" data-id="${p.cliente_id}">
      <td>${formatarDataBR(p.data_pesquisa)}</td>
      <td><b>${escaparHtml(p.cliente_nome)}</b></td>
      <td><span class="crm-nota-pilula ${p.classificacao}">${p.nota}</span></td>
      <td style="min-width:240px;">${escaparHtml(p.comentario || '—')}</td>
      <td>${escaparHtml(p.respondido_por || '—')}</td>
    </tr>
  `).join('');

  const container = document.getElementById('aba-satisfacao');
  container.innerHTML = `
    ${kpis}
    ${cartao('Leitura da satisfação', 'relatorios', listaInsights(s.insights))}
    ${cartao('Composição do NPS', 'crm', composicao)}
    ${cartao('Nota média por mês (últimos 12 meses)', 'agendar', `<div class="crm-colunas">${colunas}</div>`)}
    <div class="dash-grid" style="margin-top: 0;">
      ${cartao('Detratores a tratar', 'ocorrencias', detratores, String(s.detratores_a_tratar.length))}
      ${cartao('NPS por empresa', 'empresas', tabela(['Empresa', 'NPS', 'Avaliados'], linhasEmpresa, true))}
    </div>
    ${cartao('Sem avaliação há mais de 6 meses', 'supervisao',
      `<p style="font-size:13px;color:var(--text-muted);margin:0 0 8px;">Ordenado pela pior saúde: comece por esses. Clique para abrir a ficha e registrar a avaliação.</p>
       ${semPesquisa.length ? tabela(['Cliente', 'Saúde', 'Última avaliação', 'Supervisor'], linhasSemPesquisa) : '<div class="empty-state">Toda a carteira foi avaliada nos últimos 6 meses.</div>'}
       ${semPesquisa.length > 30 ? `<div class="meta" style="font-size:12.5px;color:var(--text-muted);margin-top:8px;">Mostrando 30 de ${semPesquisa.length}.</div>` : ''}`,
      String(semPesquisa.length))}
    ${cartao('Respostas recentes', 'avisos', s.respostas_recentes.length ? tabela(['Data', 'Cliente', 'Nota', 'Comentário', 'Respondido por'], linhasRespostas) : '<div class="empty-state">Nenhuma resposta nos últimos 12 meses.</div>')}
  `;

  container.querySelectorAll('tr[data-id]').forEach((linha) => {
    linha.addEventListener('click', () => { window.location.href = linkFicha(linha.dataset.id, '#satisfacao'); });
  });
}

// ---------------------------------------------------------------------------
// Resumo do dia
// ---------------------------------------------------------------------------

const ROTULO_NIVEL_BALAO = { alerta: 'Atenção imediata', atencao: 'Fique de olho', positivo: 'Ponto positivo', info: 'Contexto' };
const ROTULO_TIPO_DIA = { chamado: 'Chamados', visita: 'Visitas', custo: 'Custos', equipe: 'Equipe', estoque: 'Estoque', pesquisa: 'Avaliações' };

let resumoDataSelecionada = null;
let resumoDia = null;
let filtroTimelineDia = '';

function hojeLocal() {
  const agora = new Date();
  return new Date(agora.getTime() - agora.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function deslocarDia(iso, dias) {
  const [ano, mes, dia] = iso.split('-').map(Number);
  return new Date(Date.UTC(ano, mes - 1, dia + dias)).toISOString().slice(0, 10);
}

function formatarHorasFalta(horas) {
  const inteiras = Math.floor(horas);
  const minutos = Math.round((horas - inteiras) * 60);
  return minutos ? `${inteiras}h${String(minutos).padStart(2, '0')}` : `${inteiras}h`;
}

function deltaHtml(indicador, moeda = false) {
  if (!indicador || !indicador.direcao) return '';
  const media = moeda ? formatarMoeda(indicador.media) : String(indicador.media).replace('.', ',');
  const texto = { acima: `▲ acima da média (${media})`, abaixo: `▼ abaixo da média (${media})`, normal: `= normal (média ${media})` }[indicador.direcao];
  return `<span class="crm-delta ${indicador.direcao}" title="${escaparHtml(indicador.rotulo)}">${texto}</span>`;
}

function kpiResumo(label, valor, detalhe, alvo, classe = '') {
  return `
    <div class="kpi-card crm-kpi-clicavel ${classe}" data-alvo="${alvo}" title="Ver detalhes">
      <div>
        <div class="label">${label}</div>
        <div class="value">${valor}</div>
        ${detalhe ? `<div class="sub">${detalhe}</div>` : ''}
      </div>
    </div>
  `;
}

function chavePendencias() {
  return `crm-pendencias-feitas-${resumoDataSelecionada}`;
}

function lerPendenciasFeitas() {
  try {
    return new Set(JSON.parse(localStorage.getItem(chavePendencias()) || '[]'));
  } catch (erro) {
    return new Set();
  }
}

function gravarPendenciasFeitas(feitas) {
  try {
    localStorage.setItem(chavePendencias(), JSON.stringify([...feitas]));
  } catch (erro) {
    // sem armazenamento local (aba anonima etc.): a marcacao so vale ate recarregar
  }
}

async function carregarResumoDia() {
  const container = document.getElementById('aba-resumo');
  const hoje = hojeLocal();
  if (!resumoDataSelecionada) resumoDataSelecionada = hoje;

  if (!container.dataset.montado) {
    container.dataset.montado = '1';
    container.innerHTML = `
      <div class="crm-resumo-barra">
        <button class="btn-ghost" id="resumo-anterior" title="Dia anterior">◀</button>
        <input type="date" id="resumo-data" max="${hoje}">
        <button class="btn-ghost" id="resumo-proximo" title="Próximo dia">▶</button>
        <button class="btn-ghost" id="resumo-hoje">Hoje</button>
        <span class="espaco"></span>
        <button class="btn-ghost" id="resumo-atualizar">Atualizar</button>
        <button class="btn-primary" id="resumo-pdf" style="width:auto;margin:0;padding:9px 18px;">Baixar PDF</button>
      </div>
      <div id="resumo-corpo"></div>
    `;
    const irPara = (data) => {
      if (!data || data > hojeLocal()) return;
      resumoDataSelecionada = data;
      filtroTimelineDia = '';
      carregarResumoDia();
    };
    document.getElementById('resumo-anterior').addEventListener('click', () => irPara(deslocarDia(resumoDataSelecionada, -1)));
    document.getElementById('resumo-proximo').addEventListener('click', () => irPara(deslocarDia(resumoDataSelecionada, 1)));
    document.getElementById('resumo-hoje').addEventListener('click', () => irPara(hojeLocal()));
    document.getElementById('resumo-data').addEventListener('change', (e) => irPara(e.target.value));
    document.getElementById('resumo-atualizar').addEventListener('click', () => carregarResumoDia());
    document.getElementById('resumo-pdf').addEventListener('click', baixarPdfResumo);
  }

  document.getElementById('resumo-data').value = resumoDataSelecionada;
  document.getElementById('resumo-proximo').disabled = resumoDataSelecionada >= hoje;
  const corpo = document.getElementById('resumo-corpo');
  corpo.innerHTML = '<div class="loading-state">Cruzando os registros do dia...</div>';
  try {
    resumoDia = await Shell.chamarApi(`/crm-dados/resumo-dia?data=${resumoDataSelecionada}`);
    renderizarResumoDia();
  } catch (erro) {
    corpo.innerHTML = `<div class="error-message visible">${escaparHtml(erro.detalhe || 'Não foi possível montar o resumo do dia.')}</div>`;
  }
}

function renderizarResumoDia() {
  const r = resumoDia;
  const i = r.indicadores;
  const [ano, mes, dia] = r.data.split('-');

  const hero = `
    <div class="crm-resumo-hero ${r.status.chave}">
      <span class="crm-status-pill ${r.status.chave}">${escaparHtml(r.status.label)}</span>
      <div style="flex:1;min-width:240px;">
        <div class="data">${escaparHtml(r.dia_semana)}, ${dia}/${mes}/${ano}${r.eh_hoje ? ' · parcial, o dia ainda não terminou' : ''}</div>
        <div class="manchete">${escaparHtml(r.manchete)}</div>
      </div>
    </div>
  `;

  const horas = i.horas_falta.valor;
  const kpis = `
    <div class="kpi-grid">
      ${kpiResumo('chamados abertos', i.chamados_abertos.valor, deltaHtml(i.chamados_abertos), 'resumo-chamados')}
      ${kpiResumo('finalizados · backlog', `${i.chamados_finalizados.valor}<span style="font-size:15px;color:var(--text-muted);"> · ${i.backlog.valor}</span>`,
        `${i.backlog.urgentes} urgentes em aberto${i.tempo_medio_resolucao_horas !== null ? ` · média ${String(i.tempo_medio_resolucao_horas).replace('.', ',')}h` : ''}`, 'resumo-chamados', i.backlog.urgentes ? 'kpi-atencao' : '')}
      ${kpiResumo('reclamações', i.reclamacoes.valor, deltaHtml(i.reclamacoes), 'resumo-foco', i.reclamacoes.valor ? 'kpi-risco' : 'kpi-saudavel')}
      ${kpiResumo('faltas', i.faltas.valor, (horas ? `+ ${formatarHorasFalta(horas)} de falta parcial<br>` : '') + deltaHtml(i.faltas), 'resumo-ausencias', i.faltas.valor ? 'kpi-atencao' : '')}
      ${kpiResumo('atestados · férias', `${i.atestados.valor}<span style="font-size:15px;color:var(--text-muted);"> · ${i.ferias.valor}</span>`, 'colaboradores afastados no dia', 'resumo-ausencias')}
      ${kpiResumo('custos do dia', formatarMoeda(i.custo_total.valor), `${i.diarias.valor} diária(s): ${formatarMoeda(i.diarias.custo)}<br>${deltaHtml(i.custo_total, true)}`, 'resumo-custos')}
      ${kpiResumo('visitas de supervisão', i.visitas.valor, deltaHtml(i.visitas), 'resumo-supervisores')}
      ${kpiResumo('turnos vagos', i.turnos_vagos.valor, `amanhã: ${i.turnos_vagos.amanha}`, 'resumo-pendencias', i.turnos_vagos.amanha ? 'kpi-atencao' : '')}
    </div>
  `;

  const baloes = `<div class="crm-baloes">${r.insights.map((ins) => `
    <div class="crm-balao ${ins.nivel}"><span class="rotulo">${ROTULO_NIVEL_BALAO[ins.nivel]}</span>${escaparHtml(ins.texto)}</div>
  `).join('')}</div>`;

  const focos = r.pontos_atencao.length
    ? `<div class="crm-foco-grid">${r.pontos_atencao.map((p) => `
        <div class="crm-foco-card ${p.nivel}">
          <div class="topo">
            <div><div class="nome">${escaparHtml(p.cliente_nome)}</div><div class="sub">${escaparHtml(p.empresa_nome)}${p.supervisor_nome ? ` · ${escaparHtml(p.supervisor_nome)}` : ''}</div></div>
            ${p.score !== null ? `<span class="crm-score ${p.faixa}" title="Nota de saúde: ${escaparHtml(p.faixa_label)}">${p.score}</span>` : ''}
          </div>
          <div class="crm-ocorrencias">${p.itens.map((it) => `<span class="crm-ocorrencia ${it.categoria}">${escaparHtml(it.texto)}</span>`).join('')}</div>
          <div class="leitura">${escaparHtml(p.leitura)}</div>
          <div class="rodape">
            <span style="color:var(--text-muted);">${p.valor_mensal ? `${formatarMoeda(p.valor_mensal)}/mês` : ''}${p.custo ? ` · custo extra hoje ${formatarMoeda(p.custo)}` : ''}</span>
            <a href="${linkFicha(p.cliente_id)}">Abrir ficha →</a>
          </div>
        </div>
      `).join('')}</div>`
    : '<div class="empty-state">Nenhum cliente concentrou ocorrências neste dia.</div>';

  const feitas = lerPendenciasFeitas();
  const pendencias = r.pendencias_amanha.length
    ? r.pendencias_amanha.map((p, idx) => `
        <div class="crm-pendencia-item${feitas.has(p.texto) ? ' feita' : ''}">
          <input type="checkbox" id="pend-${idx}" data-texto="${escaparHtml(p.texto)}"${feitas.has(p.texto) ? ' checked' : ''}>
          <span class="ponto ${p.urgencia}"></span>
          <label for="pend-${idx}">${escaparHtml(p.texto)}${p.cliente_id ? `<a href="${linkFicha(p.cliente_id)}">ficha</a>` : ''}</label>
        </div>
      `).join('')
    : '<div class="empty-state">Nada pendente para o próximo dia.</div>';

  const ausencias = r.ausencias.length
    ? tabela(['Colaborador', 'Posto', 'Tipo', 'Cobertura', 'Observação'], r.ausencias.map((a) => `
        <tr>
          <td><a href="/colaborador-detalhe?id=${a.colaborador_id}">${escaparHtml(a.colaborador_nome)}</a></td>
          <td>${escaparHtml(a.cliente_nome || '—')}</td>
          <td>${escaparHtml(a.tipo)}${a.horas ? ` <b>(${formatarHorasFalta(a.horas)})</b>` : ''}</td>
          <td>${a.sem_cobertura ? '<span class="crm-alerta alta">sem cobertura registrada</span>' : escaparHtml(a.cobertura || '—')}</td>
          <td style="font-size:13px;color:var(--text-muted);">${escaparHtml(a.descricao || '')}</td>
        </tr>`).join(''), true)
    : '<div class="empty-state">Ninguém ausente neste dia.</div>';

  const c = r.custos;
  const custos = `
    ${c.diarias_detalhe.length ? tabela(['Cliente', 'Motivo', 'Quem cobriu', 'Valor', 'Lançado por'], c.diarias_detalhe.map((d) => `
      <tr><td>${escaparHtml(d.cliente_nome || '—')}</td><td>${escaparHtml(d.motivo)}</td><td>${escaparHtml(d.quem_cobriu || '—')}</td>
      <td>${formatarMoeda(d.valor)}</td><td>${escaparHtml(d.lancado_por)}</td></tr>`).join(''), true) : '<div class="empty-state" style="padding-top:0;">Nenhuma diária de cobertura.</div>'}
    ${c.por_tipo.length ? `<div style="margin-top:12px;">${c.por_tipo.map((t) => `<span class="crm-alerta">${escaparHtml(t.tipo)}: ${formatarMoeda(t.valor)}</span>`).join('')}</div>` : ''}
    <div style="font-size:12.5px;color:var(--text-muted);margin-top:10px;">Aguardando reembolso (todos os dias): <b>${formatarMoeda(c.pendentes_reembolso)}</b></div>
  `;

  const chamados = `
    ${r.chamados_abertos.length ? tabela(['Hora', 'Cliente', 'Tipo', 'Descrição', 'Aberto por'], r.chamados_abertos.map((ch) => `
      <tr><td class="mono">${ch.hora}</td><td><a href="${linkFicha(ch.cliente_id)}">${escaparHtml(ch.cliente_nome)}</a></td>
      <td>${escaparHtml(ch.tipo_label)}${ch.prioridade !== 'normal' ? ' <span class="crm-alerta alta">urgente</span>' : ''}</td>
      <td style="min-width:220px;font-size:13px;">${escaparHtml(ch.descricao)}</td><td>${escaparHtml(ch.aberto_por)}</td></tr>`).join('')) : '<div class="empty-state" style="padding-top:0;">Nenhum chamado aberto neste dia.</div>'}
    ${r.chamados_urgentes_em_aberto.length ? `
      <div class="section-title" style="margin:18px 0 8px;">Urgentes ainda em aberto</div>
      ${r.chamados_urgentes_em_aberto.map((ch) => `
        <div class="crm-pendencia-item"><span class="ponto alta"></span>
          <span><b>${escaparHtml(ch.cliente_nome)}</b> · ${escaparHtml(ch.tipo_label)} — ${escaparHtml(ch.descricao)}
          <span style="color:var(--text-muted);font-size:12.5px;"> (${ch.dias_em_aberto <= 0 ? 'aberto hoje' : `há ${ch.dias_em_aberto} dias`})</span></span>
        </div>`).join('')}` : ''}
  `;

  const supervisores = r.por_supervisor.length
    ? tabela(['Supervisor', 'Visitas', 'Abriu', 'Finalizou', 'Diárias', 'Custos', 'Clientes c/ ocorrência'], r.por_supervisor.map((s) => `
        <tr><td>${escaparHtml(s.nome)}</td>
        <td>${s.visitas ? s.visitas : '<span style="color:var(--crm-atencao);">0</span>'}</td>
        <td>${s.chamados_abertos}</td><td>${s.chamados_finalizados}</td><td>${s.diarias_lancadas}</td>
        <td>${formatarMoeda(s.custos_lancados)}</td>
        <td>${s.clientes_com_ocorrencia ? `<b style="color:var(--crm-risco);">${s.clientes_com_ocorrencia}</b>` : '0'}</td></tr>`).join(''), true)
    : '<div class="empty-state">Nenhum supervisor ativo.</div>';

  const e = r.equipe;
  const rodapeEquipe = [
    e.admitidos.length ? `Admissões: ${e.admitidos.map(escaparHtml).join(', ')}` : '',
    e.desligados.length ? `Desligamentos: ${e.desligados.map(escaparHtml).join(', ')}` : '',
    `${e.vagas_abertas} vaga(s) de emprego abertas`,
    r.estoque.saidas || r.estoque.entradas ? `Estoque: ${r.estoque.saidas} peça(s) entregues, ${r.estoque.entradas} recebidas` : '',
  ].filter(Boolean).join(' · ');

  document.getElementById('resumo-corpo').innerHTML = `
    ${hero}
    ${kpis}
    ${cartao('Leitura do dia', 'relatorios', baloes)}
    <div id="resumo-foco">${cartao('Onde olhar: clientes que concentraram ocorrências', 'ocorrencias', focos, String(r.pontos_atencao.length))}</div>
    <div id="resumo-pendencias">${cartao('Pendências para o próximo dia', 'agendar',
      `<p style="font-size:12.5px;color:var(--text-muted);margin:0 0 6px;">Marque o que já foi tratado (a marcação fica salva neste navegador).</p>${pendencias}`,
      String(r.pendencias_amanha.length))}</div>
    <div class="dash-grid" style="margin-top:0;">
      <div id="resumo-ausencias">${cartao('Ausências', 'colaboradores', ausencias, String(r.ausencias.length))}</div>
      <div id="resumo-custos">${cartao('Custos do dia', 'custos-diarios', custos, formatarMoeda(c.total))}</div>
    </div>
    <div id="resumo-chamados">${cartao('Chamados do dia', 'ocorrencias', chamados, String(r.chamados_abertos.length))}</div>
    <div id="resumo-supervisores">${cartao('Atividade por supervisor', 'supervisao',
      supervisores + `<div style="font-size:12.5px;color:var(--text-muted);margin-top:10px;">${rodapeEquipe}</div>`)}</div>
    <div id="resumo-timeline"></div>
    <div style="font-size:12px;color:var(--text-muted);text-align:right;">Gerado em ${escaparHtml(r.gerado_em)} · comparações com a ${escaparHtml(i.chamados_abertos.rotulo)}</div>
  `;
  desenharTimelineDia();

  const corpo = document.getElementById('resumo-corpo');
  corpo.querySelectorAll('.crm-kpi-clicavel').forEach((card) => {
    card.addEventListener('click', () => {
      const alvo = document.getElementById(card.dataset.alvo);
      if (alvo) alvo.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  corpo.querySelectorAll('.crm-pendencia-item input[type="checkbox"]').forEach((caixa) => {
    caixa.addEventListener('change', () => {
      const atuais = lerPendenciasFeitas();
      if (caixa.checked) atuais.add(caixa.dataset.texto);
      else atuais.delete(caixa.dataset.texto);
      gravarPendenciasFeitas(atuais);
      caixa.closest('.crm-pendencia-item').classList.toggle('feita', caixa.checked);
    });
  });
}

function desenharTimelineDia() {
  const eventos = resumoDia.linha_do_tempo;
  const contagem = {};
  eventos.forEach((ev) => { contagem[ev.tipo] = (contagem[ev.tipo] || 0) + 1; });
  const chips = [['', `Tudo (${eventos.length})`], ...Object.keys(ROTULO_TIPO_DIA).filter((t) => contagem[t]).map((t) => [t, `${ROTULO_TIPO_DIA[t]} (${contagem[t]})`])]
    .map(([tipo, label]) => `<button class="chip${filtroTimelineDia === tipo ? ' active' : ''}" data-filtro-dia="${tipo}">${label}</button>`)
    .join('');
  const visiveis = eventos.filter((ev) => !filtroTimelineDia || ev.tipo === filtroTimelineDia);
  const lista = visiveis.length
    ? `<div class="crm-timeline-dia">${visiveis.map((ev) => `
        <div class="crm-timeline-evento ${ev.sentimento}">
          <span class="hora">${ev.hora}</span>
          <span class="marco"></span>
          <div>
            <div class="titulo">${ev.cliente_id ? `<a href="${linkFicha(ev.cliente_id)}" style="color:inherit;text-decoration:none;">${escaparHtml(ev.titulo)}</a>` : escaparHtml(ev.titulo)}</div>
            ${ev.detalhe ? `<div class="detalhe">${escaparHtml(ev.detalhe)}</div>` : ''}
          </div>
        </div>`).join('')}</div>`
    : '<div class="empty-state">Nada registrado no sistema neste dia.</div>';

  const container = document.getElementById('resumo-timeline');
  container.innerHTML = cartao('Linha do tempo do dia', 'ponto', `<div class="chips">${chips}</div>${lista}`);
  container.querySelectorAll('[data-filtro-dia]').forEach((botao) => {
    botao.addEventListener('click', () => {
      filtroTimelineDia = botao.dataset.filtroDia;
      desenharTimelineDia();
    });
  });
}

async function baixarPdfResumo() {
  const botao = document.getElementById('resumo-pdf');
  botao.disabled = true;
  botao.textContent = 'Gerando PDF...';
  try {
    const autenticacao = Shell.autenticacao();
    const resposta = await fetch(`/crm-dados/resumo-dia/pdf?data=${resumoDataSelecionada}`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) throw new Error('Falha ao gerar o PDF');
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `resumo-operacao-${resumoDataSelecionada}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (erro) {
    alert('Não foi possível gerar o PDF agora.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Baixar PDF';
  }
}

// ---------------------------------------------------------------------------
// Exportar / atualizar
// ---------------------------------------------------------------------------

async function exportarExcel() {
  const botao = document.getElementById('btn-exportar-excel');
  botao.disabled = true;
  botao.textContent = 'Gerando...';
  try {
    const autenticacao = Shell.autenticacao();
    const resposta = await fetch('/crm-dados/carteira/excel', {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) throw new Error('Falha ao gerar o Excel');
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `crm-saude-carteira-${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (erro) {
    alert('Não foi possível gerar o Excel agora.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Exportar Excel';
  }
}

document.querySelectorAll('.tab-relatorio').forEach((botao) => {
  botao.addEventListener('click', () => trocarAba(botao.dataset.aba));
});
document.getElementById('btn-exportar-excel').addEventListener('click', exportarExcel);
document.getElementById('btn-atualizar').addEventListener('click', () => {
  document.getElementById('aba-saude').dataset.montado = '';
  renderizarAbaAtual(true);
});

const abaInicial = window.location.hash.replace('#', '');
trocarAba(ABAS.includes(abaInicial) ? abaInicial : 'visao-geral');
