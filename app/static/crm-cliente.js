const parametrosUrl = new URLSearchParams(window.location.search);
const clienteId = parametrosUrl.get('id');

const auth = Shell.montar('crm', 'CRM · Ficha do cliente');

const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const ROTULO_TENDENCIA = { piorando: '↘ piorando', melhorando: '↗ melhorando', estavel: '→ estável' };
const ROTULO_TIPO_TIMELINE = {
  chamado: 'Chamados',
  visita: 'Visitas',
  pesquisa: 'Avaliações',
  equipe: 'Equipe',
  cobertura: 'Diárias',
};

let ficha = null;
let constantes = null;
let filtroTimeline = '';
let contatoEmEdicao = null;
let notaSelecionada = null;

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

function classeNota(nota) {
  if (nota >= 9) return 'promotor';
  if (nota >= 7) return 'neutro';
  return 'detrator';
}

function kpi(label, valor, sub = '') {
  return `
    <div class="kpi-card">
      <div>
        <div class="label">${label}</div>
        <div class="value">${valor}</div>
        ${sub ? `<div class="sub">${sub}</div>` : ''}
      </div>
    </div>
  `;
}

function cartao(id, titulo, icone, conteudo, acaoHtml = '') {
  return `
    <div class="dash-card" id="${id}" style="margin-bottom: 18px;">
      <div class="dash-card-header">
        <div class="dash-card-icon">${Shell.icone(icone)}</div>
        <h3>${titulo}</h3>
        ${acaoHtml}
      </div>
      ${conteudo}
    </div>
  `;
}

function infoItem(label, valor, largo = false) {
  return `<div class="info-item${largo ? ' info-item-largo' : ''}"><span class="info-label">${label}</span><span class="info-value">${valor}</span></div>`;
}

// ---------------------------------------------------------------------------
// Blocos da ficha
// ---------------------------------------------------------------------------

function blocoSaude() {
  const s = ficha.saude;
  if (!s) {
    return cartao('saude', 'Saúde do cliente', 'crm', '<div class="empty-state">Cliente inativo: a nota de saúde só é calculada para clientes ativos.</div>');
  }
  const circunferencia = 2 * Math.PI * 42;
  const preenchido = (s.score / 100) * circunferencia;
  const corVar = { saudavel: '--crm-saudavel', atencao: '--crm-atencao', risco: '--crm-risco' }[s.faixa];

  const motivos = s.motivos.length
    ? `<ul class="crm-motivos">${s.motivos.map((m) => `<li><span class="impacto">−${m.impacto}</span>${escaparHtml(m.texto)}</li>`).join('')}</ul>`
    : '<div style="font-size:13px;color:var(--crm-saudavel);">Nenhum sinal de problema nos registros do sistema.</div>';

  const conteudo = `
    <div class="crm-gauge">
      <svg viewBox="0 0 100 100" aria-label="Nota ${s.score} de 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface-2)" stroke-width="10"/>
        ${s.score > 0 ? `<circle cx="50" cy="50" r="42" fill="none" stroke="var(${corVar})" stroke-width="10" stroke-linecap="round"
          stroke-dasharray="${preenchido} ${circunferencia}" transform="rotate(-90 50 50)"/>` : ''}
        <text x="50" y="57" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="24" font-weight="600" fill="var(--text)">${s.score}</text>
      </svg>
      <div>
        <div class="faixa ${s.faixa}">${escaparHtml(s.faixa_label)}</div>
        <div class="crm-tendencia ${s.tendencia}" style="margin-top:4px;">${ROTULO_TENDENCIA[s.tendencia]}</div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">
          ${s.sinais.eventos_negativos_recentes} ocorrências nos últimos 45 dias · ${s.sinais.eventos_negativos_anteriores} nos 45 anteriores
        </div>
      </div>
    </div>
    <div class="section-title" style="margin-bottom:6px;">Por que essa nota</div>
    ${motivos}
    <div class="crm-proxima-acao"><b>Próxima ação sugerida</b>${escaparHtml(s.acao_sugerida)}</div>
  `;
  return cartao('saude', 'Saúde do cliente', 'crm', conteudo);
}

function blocoIndicadores() {
  const i = ficha.indicadores;
  const pesoDiarias = i.peso_diarias_no_contrato_pct !== null
    ? `${i.peso_diarias_no_contrato_pct.toLocaleString('pt-BR')}% do valor anual do contrato`
    : `${i.diarias_12m} diárias pagas`;

  const maiorMes = Math.max(1, ...i.chamados_por_mes.map((m) => m.chamados));
  const colunas = i.chamados_por_mes.map((m) => `
    <div class="crm-coluna" title="${m.chamados} chamado(s), ${m.reclamacoes} reclamação(ões)">
      <span class="valor">${m.chamados}${m.reclamacoes ? ` <span style="color:var(--crm-risco);">/ ${m.reclamacoes}</span>` : ''}</span>
      <div class="barras">
        <div class="barra ${m.chamados ? '' : 'vazia'}" style="height:${Math.max(3, Math.round((m.chamados / maiorMes) * 100))}%"></div>
        <div class="barra secundaria ${m.reclamacoes ? '' : 'vazia'}" style="height:${Math.max(3, Math.round((m.reclamacoes / maiorMes) * 100))}%"></div>
      </div>
      <span class="rotulo">${rotuloMes(m.mes)}</span>
    </div>
  `).join('');

  return `
    <div>
      <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-bottom: 18px;">
        ${kpi('chamados em 12 meses', i.chamados_12m, `${i.chamados_em_aberto} em aberto agora`)}
        ${kpi('reclamações em 12 meses', i.reclamacoes_12m, i.chamados_12m ? `${Math.round((i.reclamacoes_12m * 100) / i.chamados_12m)}% dos chamados` : '')}
        ${kpi('tempo médio de resolução', i.tempo_medio_resolucao_horas !== null ? `${i.tempo_medio_resolucao_horas}h` : '—', 'chamados finalizados')}
        ${kpi('visitas em 12 meses', i.visitas_12m, ficha.saude && ficha.saude.sinais.ultima_visita ? `última em ${formatarDataBR(ficha.saude.sinais.ultima_visita)}` : 'nenhuma registrada')}
        ${kpi('custo com diárias (12m)', formatarMoeda(i.custo_diarias_12m), pesoDiarias)}
        ${kpi('NPS do cliente', formatarNps(ficha.nps_cliente), `${ficha.pesquisas.length} avaliação(ões) no histórico`)}
      </div>
      <div class="dash-card">
        <div class="dash-card-header">
          <div class="dash-card-icon">${Shell.icone('relatorios')}</div>
          <h3>Chamados por mês</h3>
          <span class="crm-legenda" style="margin-left:auto;"><span><i style="background:var(--accent)"></i>chamados</span><span><i class="risco"></i>reclamações</span></span>
        </div>
        <div class="crm-colunas">${colunas}</div>
      </div>
    </div>
  `;
}

function blocoContrato() {
  const k = ficha.contrato;
  const botao = `<button class="btn-ghost crm-dash-card-acao" id="btn-editar-contrato">${k ? 'Editar' : 'Cadastrar'}</button>`;
  if (!k) {
    return cartao('contrato', 'Contrato', 'documentos', `
      <div class="empty-state" style="padding-top:0;">Nenhum contrato cadastrado. Com o valor e as datas, o CRM passa a mostrar a receita em risco,
      avisar vencimentos e reajustes e comparar postos contratados com a equipe alocada.</div>
    `, botao);
  }
  const alertas = ficha.saude ? ficha.saude.alertas_contrato : [];
  const efetivos = ficha.saude ? ficha.saude.sinais.colaboradores_efetivos : ficha.equipe.length;
  const postos = k.postos_contratados
    ? `${efetivos} alocados de ${k.postos_contratados}${efetivos < k.postos_contratados ? ' <span style="color:var(--crm-risco);">(faltam ' + (k.postos_contratados - efetivos) + ')</span>' : ''}`
    : '—';
  const conteudo = `
    ${alertas.length ? `<div style="margin-bottom:8px;">${alertas.map((a) => `<span class="crm-alerta ${a.urgencia}">${escaparHtml(a.texto)}</span>`).join('')}</div>` : ''}
    <div class="info-grid" style="margin-top:0;padding-top:0;border-top:none;">
      ${infoItem('Valor mensal', k.valor_mensal ? formatarMoeda(k.valor_mensal) : '—')}
      ${infoItem('Valor anual', k.valor_mensal ? formatarMoeda(k.valor_mensal * 12) : '—')}
      ${infoItem('Início', formatarDataBR(k.data_inicio))}
      ${infoItem('Fim', formatarDataBR(k.data_fim) + (k.renovacao_automatica ? ' <span style="font-size:12px;color:var(--text-muted);">(renova sozinho)</span>' : ''))}
      ${infoItem('Próximo reajuste', formatarDataBR(k.data_reajuste))}
      ${infoItem('Índice', escaparHtml(k.indice_reajuste_label || '—'))}
      ${infoItem('Postos', postos, true)}
      ${k.observacoes ? infoItem('Observações', escaparHtml(k.observacoes), true) : ''}
    </div>
    <div style="font-size:12px;color:var(--text-muted);margin-top:12px;">Atualizado por ${escaparHtml(k.atualizado_por_nome || '—')} em ${formatarDataBR(k.atualizado_em)}</div>
  `;
  return cartao('contrato', 'Contrato', 'documentos', conteudo, botao);
}

function blocoContatos() {
  const botao = '<button class="btn-ghost crm-dash-card-acao" id="btn-novo-contato">+ Contato</button>';
  const cliente = ficha.cliente;
  let lista = ficha.contatos.map((c) => `
    <div class="crm-contato">
      <div class="dados">
        <div><b>${escaparHtml(c.nome)}</b>${c.principal ? '<span class="principal">★ principal</span>' : ''}</div>
        <div class="papel">${escaparHtml(c.papel_label)}${c.observacoes ? ` · ${escaparHtml(c.observacoes)}` : ''}</div>
        <div class="canais">
          ${c.telefone ? `<a href="${Shell.linkWhatsApp(c.telefone)}" target="_blank" rel="noopener">WhatsApp ${escaparHtml(c.telefone)}</a>` : ''}
          ${c.email ? `<a href="mailto:${escaparHtml(c.email)}">${escaparHtml(c.email)}</a>` : ''}
        </div>
      </div>
      <button class="btn-ghost" data-editar-contato="${c.id}" style="padding:4px 10px;font-size:12px;">Editar</button>
    </div>
  `).join('');

  if (!ficha.contatos.length) {
    lista = cliente.responsavel_nome
      ? `<div style="font-size:13px;color:var(--text-muted);">Nenhum contato no CRM ainda. No cadastro do cliente consta o responsável
         <b>${escaparHtml(cliente.responsavel_nome)}</b>${cliente.responsavel_telefone ? ` (${escaparHtml(cliente.responsavel_telefone)})` : ''}.
         <a href="#" id="btn-importar-responsavel">Adicionar como contato principal</a></div>`
      : '<div class="empty-state" style="padding-top:0;">Nenhum contato cadastrado. Registre síndico, administradora, zelador e financeiro.</div>';
  }
  return cartao('contatos', 'Contatos', 'colaboradores', lista, botao);
}

function blocoSatisfacao() {
  const botao = '<button class="btn-ghost crm-dash-card-acao" id="btn-nova-pesquisa">+ Avaliação</button>';
  const ultima = ficha.pesquisas[0];
  let resumo = '<div class="empty-state" style="padding-top:0;">Cliente ainda não foi avaliado. Pergunte: “De 0 a 10, o quanto você recomendaria nosso serviço?”</div>';
  if (ultima) {
    const dias = Math.floor((Date.now() - new Date(ultima.data_pesquisa).getTime()) / 86400000);
    resumo = `<div style="font-size:13px;color:var(--text-muted);margin-bottom:6px;">
      Última avaliação há ${dias} dias${dias > 180 ? ' — <b style="color:var(--crm-atencao);">desatualizada, vale perguntar de novo</b>' : ''}.
    </div>`;
  }
  const lista = ficha.pesquisas.map((p) => `
    <div class="crm-contato">
      <span class="crm-nota-pilula ${p.classificacao}">${p.nota}</span>
      <div class="dados">
        <div>${p.comentario ? `“${escaparHtml(p.comentario)}”` : '<span style="color:var(--text-muted);">Sem comentário</span>'}</div>
        <div class="papel">${formatarDataBR(p.data_pesquisa)} · ${escaparHtml(p.respondido_por || 'respondente não informado')} · registrado por ${escaparHtml(p.registrado_por_nome)}</div>
      </div>
      <button class="btn-ghost" data-excluir-pesquisa="${p.id}" style="padding:4px 10px;font-size:12px;">Excluir</button>
    </div>
  `).join('');
  return cartao('satisfacao', 'Satisfação', 'avisos', resumo + lista, botao);
}

function blocoEquipe() {
  const s = ficha.saude;
  const vagos = s ? s.sinais.turnos_vagos : 0;
  const cabecalho = vagos
    ? `<div style="margin-bottom:8px;"><span class="crm-alerta alta">${vagos} turno(s) vago(s) na escala</span></div>`
    : '';
  const lista = ficha.equipe.length
    ? ficha.equipe.map((c) => `
        <div class="crm-contato">
          <div class="dados">
            <div><a href="/colaborador-detalhe?id=${c.colaborador_id}" style="text-decoration:none;"><b>${escaparHtml(c.nome)}</b></a>
              <span class="papel"> · ${escaparHtml(c.cargo || 'sem cargo')}</span></div>
            <div class="papel">${c.horarios.map(escaparHtml).join(' · ')}</div>
          </div>
          <span class="mono" style="font-size:12px;color:var(--text-muted);white-space:nowrap;" title="No posto desde ${formatarDataBR(c.desde)}">
            ${c.meses_no_posto >= 1 ? `${c.meses_no_posto} ${c.meses_no_posto === 1 ? 'mês' : 'meses'}` : 'novo'}
          </span>
        </div>
      `).join('')
    : '<div class="empty-state" style="padding-top:0;">Nenhum colaborador na escala deste cliente no Mapa de Serviço.</div>';
  const rodape = s && s.sinais.trocas_colaborador
    ? `<div style="font-size:12.5px;color:var(--text-muted);margin-top:10px;">${s.sinais.trocas_colaborador} colaborador(es) saíram deste posto nos últimos 90 dias.</div>`
    : '';
  return cartao('equipe', `Equipe alocada (${ficha.equipe.length})`, 'mapa-servico', cabecalho + lista + rodape);
}

function blocoChamadosPorTipo() {
  const tipos = ficha.indicadores.chamados_por_tipo;
  if (!tipos.length) return cartao('tipos', 'Chamados por tipo (12 meses)', 'ocorrencias', '<div class="empty-state" style="padding-top:0;">Nenhum chamado em 12 meses.</div>');
  const maior = Math.max(...tipos.map((t) => t.total), 1);
  const linhas = tipos.map((t) => `
    <div class="breakdown-row">
      <span class="nome-empresa">${escaparHtml(t.tipo)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.round((t.total / maior) * 100)}%"></div></div>
      <span class="total">${t.total}</span>
    </div>
  `).join('');
  return cartao('tipos', 'Chamados por tipo (12 meses)', 'ocorrencias', linhas);
}

function blocoLinhaDoTempo() {
  const itens = ficha.linha_do_tempo.filter((t) => !filtroTimeline || t.tipo === filtroTimeline);
  const contagem = {};
  ficha.linha_do_tempo.forEach((t) => { contagem[t.tipo] = (contagem[t.tipo] || 0) + 1; });

  const chips = [['', `Tudo (${ficha.linha_do_tempo.length})`], ...Object.keys(ROTULO_TIPO_TIMELINE)
    .filter((tipo) => contagem[tipo])
    .map((tipo) => [tipo, `${ROTULO_TIPO_TIMELINE[tipo]} (${contagem[tipo]})`])]
    .map(([tipo, label]) => `<button class="chip${filtroTimeline === tipo ? ' active' : ''}" data-filtro-timeline="${tipo}">${label}</button>`)
    .join('');

  const lista = itens.length
    ? itens.map((t) => `
        <div class="timeline-item sentimento-${t.sentimento}">
          <div class="data-col">${formatarDataBR(t.data)}</div>
          <div class="conteudo">
            <div class="linha-topo"><span class="tipo-label">${escaparHtml(t.titulo)}</span></div>
            ${t.descricao ? `<div class="descricao">${escaparHtml(t.descricao)}</div>` : ''}
            <div class="meta">${escaparHtml(t.meta)}</div>
          </div>
        </div>
      `).join('')
    : '<div class="empty-state">Nada registrado nos últimos 6 meses.</div>';

  return cartao('linha-do-tempo', 'Linha do tempo (últimos 6 meses)', 'ponto', `<div class="chips">${chips}</div>${lista}`);
}

// ---------------------------------------------------------------------------
// Montagem
// ---------------------------------------------------------------------------

function renderizarFicha() {
  const c = ficha.cliente;
  document.title = `${c.nome} · CRM · operações`;
  const endereco = [c.endereco, c.bairro, c.cidade || c.municipio].filter(Boolean).join(', ');
  const pendencias = ficha.saude ? ficha.saude.pendencias_cadastro : [];

  document.getElementById('ficha').innerHTML = `
    <div class="cliente-header">
      <div class="empresa-tag">${escaparHtml(c.empresa_nome)}${c.ativo ? '' : ' · INATIVO'}</div>
      <h2>${escaparHtml(c.nome)}</h2>
      <div class="cnpj">
        Supervisor: ${escaparHtml(c.supervisor_nome || 'não definido')}${endereco ? ` · ${escaparHtml(endereco)}` : ''}
        · <a href="/cliente-detalhe?id=${c.id}">cadastro e chamados</a>
      </div>
      ${pendencias.length ? `<div style="margin-top:10px;">${pendencias.map((p) => `<span class="crm-pendencia">${escaparHtml(p)}</span>`).join('')}</div>` : ''}
    </div>

    <div class="crm-ficha-topo">
      ${blocoSaude()}
      ${blocoIndicadores()}
    </div>

    <div class="dash-grid" style="margin-top:0;">
      ${blocoContrato()}
      ${blocoContatos()}
    </div>
    <div class="dash-grid" style="margin-top:0;">
      ${blocoSatisfacao()}
      ${blocoEquipe()}
    </div>
    ${blocoChamadosPorTipo()}
    ${blocoLinhaDoTempo()}
  `;
  ligarEventosFicha();
}

function ligarEventosFicha() {
  document.getElementById('btn-editar-contrato').addEventListener('click', abrirModalContrato);
  document.getElementById('btn-novo-contato').addEventListener('click', () => abrirModalContato(null));
  document.getElementById('btn-nova-pesquisa').addEventListener('click', abrirModalPesquisa);

  document.querySelectorAll('[data-editar-contato]').forEach((botao) => {
    botao.addEventListener('click', () => {
      abrirModalContato(ficha.contatos.find((c) => String(c.id) === botao.dataset.editarContato));
    });
  });

  document.querySelectorAll('[data-excluir-pesquisa]').forEach((botao) => {
    botao.addEventListener('click', async () => {
      if (!confirm('Excluir esta avaliação? Ela deixa de contar no NPS e na nota de saúde.')) return;
      try {
        await Shell.chamarApi(`/crm-dados/pesquisas/${botao.dataset.excluirPesquisa}`, { method: 'DELETE' });
        await carregarFicha();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível excluir a avaliação.');
      }
    });
  });

  const importar = document.getElementById('btn-importar-responsavel');
  if (importar) {
    importar.addEventListener('click', async (evento) => {
      evento.preventDefault();
      try {
        await Shell.chamarApi(`/crm-dados/clientes/${clienteId}/contatos`, {
          method: 'POST',
          body: {
            nome: ficha.cliente.responsavel_nome,
            telefone: ficha.cliente.responsavel_telefone,
            papel: 'outro',
            principal: true,
          },
        });
        await carregarFicha();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível adicionar o contato.');
      }
    });
  }

  ligarFiltrosTimeline();
}

function ligarFiltrosTimeline() {
  document.querySelectorAll('[data-filtro-timeline]').forEach((botao) => {
    botao.addEventListener('click', () => {
      filtroTimeline = botao.dataset.filtroTimeline;
      document.getElementById('linha-do-tempo').outerHTML = blocoLinhaDoTempo();
      ligarFiltrosTimeline();
    });
  });
}

async function carregarFicha() {
  try {
    const [dados, consts] = await Promise.all([
      Shell.chamarApi(`/crm-dados/clientes/${clienteId}`),
      constantes ? Promise.resolve(constantes) : Shell.chamarApi('/crm-constantes'),
    ]);
    ficha = dados;
    constantes = consts;
    renderizarFicha();
  } catch (erro) {
    document.getElementById('ficha').innerHTML =
      `<div class="error-message visible">${escaparHtml(erro.detalhe || 'Não foi possível carregar a ficha do cliente.')}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Modais
// ---------------------------------------------------------------------------

function montarModais() {
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal-overlay" id="contrato-modal" hidden>
      <div class="modal">
        <div class="modal-header"><h3>Contrato</h3><button class="modal-close" data-fechar="contrato-modal" aria-label="Fechar">&times;</button></div>
        <form id="contrato-form">
          <div class="crm-duas-colunas">
            <div class="field"><label for="contrato-valor">Valor mensal (R$)</label><input type="number" id="contrato-valor" min="0" step="0.01" placeholder="0,00"></div>
            <div class="field"><label for="contrato-postos">Postos contratados</label><input type="number" id="contrato-postos" min="0" step="1" placeholder="Nº de pessoas"></div>
            <div class="field"><label for="contrato-inicio">Início</label><input type="date" id="contrato-inicio"></div>
            <div class="field"><label for="contrato-fim">Fim da vigência</label><input type="date" id="contrato-fim"></div>
            <div class="field"><label for="contrato-reajuste">Próximo reajuste</label><input type="date" id="contrato-reajuste"></div>
            <div class="field"><label for="contrato-indice">Índice de reajuste</label><select id="contrato-indice"></select></div>
          </div>
          <label class="crm-checkbox"><input type="checkbox" id="contrato-renovacao"> Renovação automática</label>
          <div class="field"><label for="contrato-observacoes">Observações</label><textarea id="contrato-observacoes" rows="3" placeholder="Cláusulas importantes, multa rescisória, histórico de negociação..."></textarea></div>
          <div class="error-message" id="contrato-erro"></div>
          <button type="submit" class="btn-primary" id="contrato-salvar">Salvar contrato</button>
        </form>
      </div>
    </div>

    <div class="modal-overlay" id="contato-modal" hidden>
      <div class="modal">
        <div class="modal-header"><h3 id="contato-titulo">Novo contato</h3><button class="modal-close" data-fechar="contato-modal" aria-label="Fechar">&times;</button></div>
        <form id="contato-form">
          <div class="field"><label for="contato-nome">Nome</label><input type="text" id="contato-nome" required></div>
          <div class="field"><label for="contato-papel">Papel</label><select id="contato-papel"></select></div>
          <div class="crm-duas-colunas">
            <div class="field"><label for="contato-telefone">Telefone / WhatsApp</label><input type="text" id="contato-telefone"></div>
            <div class="field"><label for="contato-email">E-mail</label><input type="email" id="contato-email"></div>
          </div>
          <label class="crm-checkbox"><input type="checkbox" id="contato-principal"> Contato principal</label>
          <div class="field"><label for="contato-observacoes">Observações</label><input type="text" id="contato-observacoes" placeholder="Ex: prefere contato à tarde"></div>
          <div class="error-message" id="contato-erro"></div>
          <button type="submit" class="btn-primary" id="contato-salvar">Salvar contato</button>
          <button type="button" class="btn-ghost" id="contato-excluir" style="width:100%;margin-top:10px;color:var(--danger);" hidden>Excluir contato</button>
        </form>
      </div>
    </div>

    <div class="modal-overlay" id="pesquisa-modal" hidden>
      <div class="modal">
        <div class="modal-header"><h3>Registrar avaliação</h3><button class="modal-close" data-fechar="pesquisa-modal" aria-label="Fechar">&times;</button></div>
        <form id="pesquisa-form">
          <div class="field">
            <label>De 0 a 10, o quanto o cliente recomendaria nosso serviço?</label>
            <div class="crm-nota-grade" id="pesquisa-notas">
              ${Array.from({ length: 11 }, (_, n) => `<button type="button" data-nota="${n}">${n}</button>`).join('')}
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-muted);margin-top:4px;"><span>nada provável</span><span>com certeza</span></div>
          </div>
          <div class="crm-duas-colunas">
            <div class="field"><label for="pesquisa-data">Data</label><input type="date" id="pesquisa-data" required></div>
            <div class="field"><label for="pesquisa-respondido">Quem respondeu</label><input type="text" id="pesquisa-respondido" list="pesquisa-contatos" placeholder="Ex: Síndica Maria"><datalist id="pesquisa-contatos"></datalist></div>
          </div>
          <div class="field"><label for="pesquisa-comentario">Comentário (o motivo da nota)</label><textarea id="pesquisa-comentario" rows="3" placeholder="O que o cliente elogiou ou criticou?"></textarea></div>
          <div class="error-message" id="pesquisa-erro"></div>
          <button type="submit" class="btn-primary" id="pesquisa-salvar">Salvar avaliação</button>
        </form>
      </div>
    </div>
  `);

  document.querySelectorAll('[data-fechar]').forEach((botao) => {
    botao.addEventListener('click', () => { document.getElementById(botao.dataset.fechar).hidden = true; });
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (evento) => { if (evento.target === overlay) overlay.hidden = true; });
  });

  document.getElementById('contrato-form').addEventListener('submit', salvarContrato);
  document.getElementById('contato-form').addEventListener('submit', salvarContato);
  document.getElementById('contato-excluir').addEventListener('click', excluirContato);
  document.getElementById('pesquisa-form').addEventListener('submit', salvarPesquisa);
  document.getElementById('pesquisa-notas').addEventListener('click', (evento) => {
    const botao = evento.target.closest('[data-nota]');
    if (!botao) return;
    notaSelecionada = Number(botao.dataset.nota);
    document.querySelectorAll('#pesquisa-notas button').forEach((b) => {
      b.className = Number(b.dataset.nota) === notaSelecionada ? `selecionada ${classeNota(notaSelecionada)}` : '';
    });
  });
}

function mostrarErro(id, erro, padrao) {
  const caixa = document.getElementById(id);
  caixa.textContent = erro.detalhe || padrao;
  caixa.classList.add('visible');
}

function abrirModalContrato() {
  const k = ficha.contrato || {};
  document.getElementById('contrato-indice').innerHTML = '<option value="">Não definido</option>' +
    constantes.indices_reajuste.map((i) => `<option value="${i.chave}">${i.label}</option>`).join('');
  document.getElementById('contrato-valor').value = k.valor_mensal ?? '';
  document.getElementById('contrato-postos').value = k.postos_contratados ?? '';
  document.getElementById('contrato-inicio').value = k.data_inicio || '';
  document.getElementById('contrato-fim').value = k.data_fim || '';
  document.getElementById('contrato-reajuste').value = k.data_reajuste || '';
  document.getElementById('contrato-indice').value = k.indice_reajuste || '';
  document.getElementById('contrato-renovacao').checked = !!k.renovacao_automatica;
  document.getElementById('contrato-observacoes').value = k.observacoes || '';
  document.getElementById('contrato-erro').classList.remove('visible');
  document.getElementById('contrato-modal').hidden = false;
}

async function salvarContrato(evento) {
  evento.preventDefault();
  const botao = document.getElementById('contrato-salvar');
  const numeroOuNulo = (id) => {
    const valor = document.getElementById(id).value;
    return valor === '' ? null : Number(valor);
  };
  const corpo = {
    valor_mensal: numeroOuNulo('contrato-valor'),
    postos_contratados: numeroOuNulo('contrato-postos'),
    data_inicio: document.getElementById('contrato-inicio').value || null,
    data_fim: document.getElementById('contrato-fim').value || null,
    data_reajuste: document.getElementById('contrato-reajuste').value || null,
    indice_reajuste: document.getElementById('contrato-indice').value || null,
    renovacao_automatica: document.getElementById('contrato-renovacao').checked,
    observacoes: document.getElementById('contrato-observacoes').value || null,
  };
  botao.disabled = true;
  try {
    await Shell.chamarApi(`/crm-dados/clientes/${clienteId}/contrato`, { method: 'PUT', body: corpo });
    document.getElementById('contrato-modal').hidden = true;
    await carregarFicha();
  } catch (erro) {
    mostrarErro('contrato-erro', erro, 'Não foi possível salvar o contrato.');
  } finally {
    botao.disabled = false;
  }
}

function abrirModalContato(contato) {
  contatoEmEdicao = contato;
  document.getElementById('contato-titulo').textContent = contato ? 'Editar contato' : 'Novo contato';
  document.getElementById('contato-papel').innerHTML =
    constantes.papeis_contato.map((p) => `<option value="${p.chave}">${p.label}</option>`).join('');
  document.getElementById('contato-nome').value = contato ? contato.nome : '';
  document.getElementById('contato-papel').value = contato ? contato.papel : 'sindico';
  document.getElementById('contato-telefone').value = contato ? contato.telefone || '' : '';
  document.getElementById('contato-email').value = contato ? contato.email || '' : '';
  document.getElementById('contato-principal').checked = contato ? contato.principal : ficha.contatos.length === 0;
  document.getElementById('contato-observacoes').value = contato ? contato.observacoes || '' : '';
  document.getElementById('contato-excluir').hidden = !contato;
  document.getElementById('contato-erro').classList.remove('visible');
  document.getElementById('contato-modal').hidden = false;
}

async function salvarContato(evento) {
  evento.preventDefault();
  const botao = document.getElementById('contato-salvar');
  const corpo = {
    nome: document.getElementById('contato-nome').value,
    papel: document.getElementById('contato-papel').value,
    telefone: document.getElementById('contato-telefone').value || null,
    email: document.getElementById('contato-email').value || null,
    principal: document.getElementById('contato-principal').checked,
    observacoes: document.getElementById('contato-observacoes').value || null,
  };
  botao.disabled = true;
  try {
    if (contatoEmEdicao) {
      await Shell.chamarApi(`/crm-dados/contatos/${contatoEmEdicao.id}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi(`/crm-dados/clientes/${clienteId}/contatos`, { method: 'POST', body: corpo });
    }
    document.getElementById('contato-modal').hidden = true;
    await carregarFicha();
  } catch (erro) {
    mostrarErro('contato-erro', erro, 'Não foi possível salvar o contato.');
  } finally {
    botao.disabled = false;
  }
}

async function excluirContato() {
  if (!contatoEmEdicao || !confirm(`Excluir o contato ${contatoEmEdicao.nome}?`)) return;
  try {
    await Shell.chamarApi(`/crm-dados/contatos/${contatoEmEdicao.id}`, { method: 'DELETE' });
    document.getElementById('contato-modal').hidden = true;
    await carregarFicha();
  } catch (erro) {
    mostrarErro('contato-erro', erro, 'Não foi possível excluir o contato.');
  }
}

function abrirModalPesquisa() {
  notaSelecionada = null;
  document.getElementById('pesquisa-form').reset();
  document.querySelectorAll('#pesquisa-notas button').forEach((b) => { b.className = ''; });
  document.getElementById('pesquisa-data').value = new Date().toISOString().slice(0, 10);
  document.getElementById('pesquisa-contatos').innerHTML =
    ficha.contatos.map((c) => `<option value="${escaparHtml(c.nome)}">`).join('');
  document.getElementById('pesquisa-erro').classList.remove('visible');
  document.getElementById('pesquisa-modal').hidden = false;
}

async function salvarPesquisa(evento) {
  evento.preventDefault();
  if (notaSelecionada === null) {
    mostrarErro('pesquisa-erro', {}, 'Escolha a nota de 0 a 10.');
    return;
  }
  const botao = document.getElementById('pesquisa-salvar');
  botao.disabled = true;
  try {
    await Shell.chamarApi(`/crm-dados/clientes/${clienteId}/pesquisas`, {
      method: 'POST',
      body: {
        nota: notaSelecionada,
        data_pesquisa: document.getElementById('pesquisa-data').value,
        respondido_por: document.getElementById('pesquisa-respondido').value || null,
        comentario: document.getElementById('pesquisa-comentario').value || null,
      },
    });
    document.getElementById('pesquisa-modal').hidden = true;
    await carregarFicha();
  } catch (erro) {
    mostrarErro('pesquisa-erro', erro, 'Não foi possível salvar a avaliação.');
  } finally {
    botao.disabled = false;
  }
}

// ---------------------------------------------------------------------------

if (!clienteId) {
  document.getElementById('ficha').innerHTML = '<div class="error-message visible">Cliente não informado.</div>';
} else {
  montarModais();
  carregarFicha().then(() => {
    const alvo = window.location.hash && document.getElementById(window.location.hash.slice(1));
    if (alvo) alvo.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}
