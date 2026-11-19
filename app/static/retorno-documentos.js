// Painel do mes do Retorno de documentos: a antiga aba da planilha, um
// bloco por supervisor, uma linha por colaborador, uma coluna por documento.
// Na opcao "Todos os meses" vem so o que esta em falta, de todos os meses de
// uma vez: uma linha por colaborador e mes (coluna "Mês" a mais).
Shell.montar('retorno-documentos', 'Retorno de Documentos');

const MESES_NOME = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

let dadosMes = null;

function proximoMes(ano, mes) {
  return mes === 12 ? [ano + 1, 1] : [ano, mes + 1];
}

// do inicio do acompanhamento ate o mes corrente (o mes corrente pode ser marcado adiantado)
function popularSelectMes(inicio, atual) {
  const select = document.getElementById('ret-filtro-mes');
  const hoje = new Date();
  const fim = [hoje.getFullYear(), hoje.getMonth() + 1];
  const opcoes = [];
  let [ano, mes] = [inicio.ano, inicio.mes];
  while (ano < fim[0] || (ano === fim[0] && mes <= fim[1])) {
    opcoes.push({ valor: `${ano}-${mes}`, label: `${MESES_NOME[mes - 1]}/${ano}` });
    [ano, mes] = proximoMes(ano, mes);
  }
  opcoes.reverse();
  select.innerHTML = '<option value="todos">Todos os meses (só o que está em falta)</option>' + opcoes
    .map((o) => {
      const recolhendo = o.valor === `${atual.ano}-${atual.mes}` ? ' · recolhendo agora' : '';
      return `<option value="${o.valor}">${o.label}${recolhendo}</option>`;
    })
    .join('');
}

function modoTodos() {
  return Boolean(dadosMes && dadosMes.todos_meses);
}

function popularSelectSupervisor(grupos) {
  const select = document.getElementById('ret-filtro-supervisor');
  const atual = select.value;
  select.innerHTML = '<option value="">Todos</option>' + grupos
    .map((g) => `<option value="${RetornoDoc.escapar(g.supervisor_nome)}">${RetornoDoc.escapar(g.supervisor_nome)}</option>`)
    .join('');
  if ([...select.options].some((o) => o.value === atual)) select.value = atual;
}

function atualizarKpis() {
  const r = dadosMes.resumo;
  const rotulos = document.querySelectorAll('#ret-kpis .kpi-card .label');
  const valores = document.querySelectorAll('#ret-kpis .kpi-card .value');
  const cartoes = modoTodos()
    ? [
      ['colaboradores com falta', r.colaboradores],
      ['meses em aberto', r.meses_com_falta],
      ['faltando parte (F)', r.faltando_parte],
      ['documentos em falta', r.documentos_em_falta],
    ]
    : [
      ['colaboradores no mês', r.colaboradores],
      ['completos', r.completos],
      ['com falta', r.com_falta],
      ['documentos em falta', r.documentos_em_falta],
    ];
  cartoes.forEach(([rotulo, valor], i) => {
    rotulos[i].textContent = rotulo;
    valores[i].textContent = valor;
  });
}

function recalcularResumo() {
  const linhas = dadosMes.grupos.flatMap((g) => g.colaboradores);
  if (modoTodos()) {
    dadosMes.resumo = {
      colaboradores: new Set(linhas.filter((l) => l.em_falta_mes > 0).map((l) => l.id)).size,
      meses_com_falta: linhas.filter((l) => l.em_falta_mes > 0).length,
      faltando_parte: linhas.reduce(
        (soma, l) => soma + Object.values(l.celulas).filter((c) => c.situacao === 'faltando').length, 0
      ),
      documentos_em_falta: linhas.reduce((soma, l) => soma + l.em_falta_mes, 0),
    };
    return;
  }
  dadosMes.resumo = {
    colaboradores: linhas.length,
    completos: linhas.filter((l) => l.em_falta_mes === 0).length,
    com_falta: linhas.filter((l) => l.em_falta_mes > 0).length,
    documentos_em_falta: linhas.reduce((soma, l) => soma + l.em_falta_mes, 0),
  };
}

// ano/mes da linha: no modo "todos os meses" cada linha e um mes; no painel do mes, o mes escolhido
function anoMesDaLinha(linha) {
  return modoTodos() ? [linha.ano, linha.mes] : [dadosMes.ano, dadosMes.mes];
}

function linhaHtml(linha) {
  const { documentos, pode_marcar: podeMarcar } = dadosMes;
  const todos = modoTodos();
  const [ano, mes] = anoMesDaLinha(linha);
  const celulas = documentos
    .map((doc) => {
      const celula = linha.celulas[doc.chave];
      if (!celula) return '<td class="ret-celula"><span class="ret-nao-tem">·</span></td>';
      const etiqueta = RetornoDoc.etiquetaHtml(
        celula.label || doc.label, celula, { colaborador: linha.id, ano, mes, documento: doc.chave }, podeMarcar
      );
      const obs = celula.observacao ? `<div class="ret-obs">${RetornoDoc.escapar(celula.observacao)}</div>` : '';
      return `<td class="ret-celula">${etiqueta}${obs}</td>`;
    })
    .join('');
  const temPendente = Object.values(linha.celulas).some((c) => !c.situacao);
  const acao = podeMarcar && temPendente
    ? `<button class="btn-ghost mov-btn-mini ret-btn-tudo" data-colaborador="${linha.id}" data-ano="${ano}" data-mes="${mes}">Tudo entregue</button>`
    : '';
  const outrosMeses = linha.em_falta_total - linha.em_falta_mes;
  const total = !todos && outrosMeses > 0
    ? `<span class="evento-tipo-badge falta" title="Em falta em outros meses">+${outrosMeses} outros meses</span>`
    : '';
  const status = linha.status !== 'ativo' ? ` <span class="badge-inativo">${linha.status === 'afastado' ? 'Afastado' : 'Desligado'}</span>` : '';
  const colunaMes = todos ? `<td>${RetornoDoc.escapar(linha.competencia)}</td>` : '';
  return `
    <tr data-linha="${linha.id}">
      <td><a href="/colaborador-detalhe?id=${linha.id}">${RetornoDoc.escapar(linha.nome)}</a>${status}</td>
      ${colunaMes}
      ${celulas}
      ${todos ? '' : `<td>${total}</td>`}
      <td>${acao}</td>
    </tr>`;
}

function renderizar() {
  const container = document.getElementById('ret-conteudo');
  const filtroSupervisor = document.getElementById('ret-filtro-supervisor').value;
  const busca = document.getElementById('ret-filtro-busca').value.trim().toLowerCase();
  const soFalta = document.getElementById('ret-filtro-falta').checked;

  const todos = modoTodos();
  atualizarKpis();
  let legenda;
  if (todos) {
    legenda = 'Todos os meses: só os meses com documento em falta, do mais antigo para o mais novo · OK entregue · F faltando parte · X não se aplica · ! pendente (em falta) · clique para marcar';
  } else if (dadosMes.encerrada) {
    legenda = `${dadosMes.nome}: OK entregue · F faltando parte · X não se aplica · ! pendente (em falta) · clique para marcar`;
  } else {
    legenda = `${dadosMes.nome} ainda está em andamento: o que estiver em branco não conta como falta até o mês acabar.`;
  }
  document.getElementById('ret-legenda').textContent = legenda;

  const blocos = dadosMes.grupos
    .filter((g) => !filtroSupervisor || g.supervisor_nome === filtroSupervisor)
    .map((g) => {
      const linhas = g.colaboradores.filter(
        (l) => (!busca || l.nome.toLowerCase().includes(busca))
          && (!soFalta || (todos ? l.em_falta_mes > 0 : l.em_falta_total > 0))
      );
      if (linhas.length === 0) return '';
      let resumoGrupo;
      if (todos) {
        const pessoas = new Set(g.colaboradores.map((l) => l.id)).size;
        const docs = g.colaboradores.reduce((soma, l) => soma + l.em_falta_mes, 0);
        resumoGrupo = `${pessoas} colaboradores · ${docs ? `<span class="badge-inativo">${docs} documentos em falta</span>` : 'tudo em dia'}`;
      } else {
        const comFalta = g.colaboradores.filter((l) => l.em_falta_mes > 0).length;
        resumoGrupo = `${g.colaboradores.length} colaboradores${comFalta ? ` · <span class="badge-inativo">${comFalta} com falta</span>` : ' · tudo em dia'}`;
      }
      const cabecalho = `<th>Funcionário</th>${todos ? '<th>Mês</th>' : ''}${dadosMes.documentos.map((d) => `<th>${d.label}</th>`).join('')}${todos ? '' : '<th></th>'}<th></th>`;
      return `
        <div class="avisos-header" style="margin-top: 22px;">
          <span class="section-title" style="margin: 0;">${RetornoDoc.escapar(g.supervisor_nome)}</span>
          <span class="meta">${resumoGrupo}</span>
        </div>
        <div class="table-scroll-wrapper"><table class="table-list ret-tabela">
          <thead><tr>${cabecalho}</tr></thead>
          <tbody>${linhas.map(linhaHtml).join('')}</tbody>
        </table></div>`;
    })
    .join('');

  const vazio = todos ? 'Nenhum documento em falta com esses filtros.' : 'Nenhum colaborador com esses filtros.';
  container.innerHTML = blocos || `<div class="empty-state">${vazio}</div>`;
}

async function carregarEmpresas() {
  try {
    const empresas = await Shell.chamarApi('/empresas');
    if (!empresas) return;
    document.getElementById('ret-filtro-empresa').innerHTML = '<option value="">Todas</option>' + empresas
      .map((e) => `<option value="${e.id}">${RetornoDoc.escapar(e.nome)}</option>`)
      .join('');
  } catch (_) {
    // sem a lista de empresas o painel continua funcionando, so sem esse filtro
  }
}

// competencia = 'todos', 'ano-mes' ou vazio (abre o mes sendo recolhido agora)
async function carregar(competencia) {
  const container = document.getElementById('ret-conteudo');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const params = new URLSearchParams();
    if (competencia === 'todos') {
      params.set('todos', 'true');
    } else if (competencia) {
      const [ano, mes] = competencia.split('-');
      params.set('ano', ano);
      params.set('mes', mes);
    }
    const empresa = document.getElementById('ret-filtro-empresa').value;
    if (empresa) params.set('empresa_id', empresa);
    const query = params.toString() ? `?${params}` : '';
    const dados = await Shell.chamarApi(`/retorno-documentos-dados${query}`);
    if (dados === null) return;
    dadosMes = dados;
    if (!document.getElementById('ret-filtro-mes').options.length) {
      popularSelectMes(dados.inicio, dados.competencia_atual);
    }
    document.getElementById('ret-filtro-mes').value = dados.todos_meses ? 'todos' : `${dados.ano}-${dados.mes}`;
    document.getElementById('ret-btn-importar').hidden = !dados.pode_marcar || Shell.autenticacao().papel !== 'escritorio';
    popularSelectSupervisor(dados.grupos);
    renderizar();
  } catch (erro) {
    container.innerHTML = `<div class="empty-state">${RetornoDoc.escapar(erro.detalhe || 'Não foi possível carregar agora.')}</div>`;
  }
}

// troca a linha do colaborador pela que o servidor devolveu depois de marcar
function aplicarResposta(resposta) {
  if (modoTodos()) {
    aplicarRespostaTodos(resposta);
  } else {
    const nova = resposta.linha;
    dadosMes.grupos.forEach((g) => {
      g.colaboradores = g.colaboradores.map((l) => (l.id === nova.id ? nova : l));
    });
  }
  recalcularResumo();
  renderizar();
}

// modo "todos os meses": refaz as linhas ja mostradas do colaborador com os
// meses que voltaram (a linha que ficou completa continua ate recarregar)
function aplicarRespostaTodos(resposta) {
  const id = resposta.linha.id;
  const porMes = new Map(resposta.meses.map((m) => [`${m.ano}-${m.mes}`, m]));
  const emFaltaTotal = resposta.meses.reduce((soma, m) => soma + m.em_falta, 0);
  dadosMes.grupos.forEach((g) => {
    g.colaboradores = g.colaboradores.map((l) => {
      if (l.id !== id) return l;
      const m = porMes.get(`${l.ano}-${l.mes}`);
      if (!m) return { ...l, em_falta_total: emFaltaTotal };
      const celulas = {};
      m.documentos.forEach((d) => {
        celulas[d.chave] = {
          label: d.label, situacao: d.situacao, observacao: d.observacao, em_falta: d.em_falta,
          atualizado_por: d.atualizado_por, atualizado_em: d.atualizado_em,
        };
      });
      return { ...l, celulas, encerrada: m.encerrada, em_falta_mes: m.em_falta, em_falta_total: emFaltaTotal };
    });
  });
}

function acharLinha(colaboradorId, ano, mes) {
  for (const g of dadosMes.grupos) {
    const linha = g.colaboradores.find(
      (l) => l.id === Number(colaboradorId) && (!modoTodos() || (l.ano === Number(ano) && l.mes === Number(mes)))
    );
    if (linha) return linha;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Relatorio em Excel / PDF (respeita o mes e o filtro de supervisor)
// ---------------------------------------------------------------------------

async function baixarRelatorio(formato, botao) {
  const auth = Shell.autenticacao();
  if (!auth || !dadosMes) return;
  const supervisor = document.getElementById('ret-filtro-supervisor').value;
  const empresa = document.getElementById('ret-filtro-empresa').value;
  const params = new URLSearchParams(modoTodos() ? { todos: 'true' } : { ano: dadosMes.ano, mes: dadosMes.mes });
  if (empresa) params.set('empresa_id', empresa);
  if (supervisor) params.set('supervisor', supervisor);
  const textoOriginal = botao.textContent;
  botao.disabled = true;
  botao.textContent = 'Gerando...';
  try {
    const resposta = await fetch(`/retorno-documentos-dados/${formato}?${params}`, {
      headers: { Authorization: `Bearer ${auth.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      alert(corpo.detail || 'Não foi possível gerar o relatório agora.');
      return;
    }
    const nome = (resposta.headers.get('Content-Disposition') || '').match(/filename="([^"]+)"/);
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = nome ? nome[1] : `retorno-documentos.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (erro) {
    alert('Não foi possível gerar o relatório agora.');
  } finally {
    botao.disabled = false;
    botao.textContent = textoOriginal;
  }
}

// ---------------------------------------------------------------------------
// Importar a planilha antiga
// ---------------------------------------------------------------------------

let conferenciaImportacao = null;

async function enviarPlanilha(aplicar) {
  const auth = Shell.autenticacao();
  if (!auth) return null;
  const formData = new FormData();
  formData.append('arquivo', document.getElementById('ret-importar-arquivo').files[0]);
  formData.append('aplicar', aplicar ? 'true' : 'false');
  if (aplicar) {
    const vinculos = {};
    document.querySelectorAll('.ret-vinculo:checked').forEach((caixa) => {
      vinculos[caixa.dataset.nome] = Number(caixa.value);
    });
    formData.append('vinculos', JSON.stringify(vinculos));
  }
  const resposta = await fetch('/retorno-documentos-dados/importar', {
    method: 'POST',
    headers: { Authorization: `Bearer ${auth.access_token}` },
    body: formData,
  });
  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error('Falha ao importar a planilha');
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON
    }
    throw erro;
  }
  return resposta.json();
}

function renderizarConferencia(c) {
  const naoCasados = c.nao_casados
    .map((n) => {
      const sugestao = n.sugestao
        ? `<label><input type="checkbox" class="ret-vinculo" data-nome="${RetornoDoc.escapar(n.nome)}" value="${n.sugestao.id}"${n.sugestao.semelhanca >= 0.9 ? ' checked' : ''} style="width: auto; margin-right: 6px;">${RetornoDoc.escapar(n.sugestao.nome)}${n.sugestao.status === 'desligado' ? ' (desligado)' : ''}</label>`
        : '<span class="importar-detalhe">sem sugestão: fica de fora</span>';
      return `
        <tr${n.sugestao ? ' class="importar-parecido"' : ''}>
          <td>${RetornoDoc.escapar(n.nome)}<div class="importar-detalhe">${RetornoDoc.escapar(n.motivo)} · ${n.abas.length} ${n.abas.length > 1 ? 'meses' : 'mês'}</div></td>
          <td>${sugestao}</td>
        </tr>`;
    })
    .join('');
  document.getElementById('ret-importar-conferencia').innerHTML = `
    <div class="importar-resumo">
      <strong>${c.meses.length} meses</strong> (${RetornoDoc.escapar(c.meses[0])} a ${RetornoDoc.escapar(c.meses[c.meses.length - 1])}) ·
      ${c.nomes_planilha} nomes na planilha · <strong>${c.casados}</strong> encontrados no cadastro ·
      <strong>${c.marcacoes_novas}</strong> marcações vão entrar
      ${c.marcacoes_ja_existentes ? ` · ${c.marcacoes_ja_existentes} já estavam marcadas (ficam como estão)` : ''}
    </div>
    ${c.nao_casados.length ? `
      <p class="importar-ajuda">${c.nao_casados.length} nomes não foram encontrados pelo nome exato. Marque a sugestão quando for a mesma pessoa. O que ficar desmarcado não é importado.</p>
      <div class="importar-tabela"><table>
        <thead><tr><th>Nome na planilha</th><th>Usar o colaborador</th></tr></thead>
        <tbody>${naoCasados}</tbody>
      </table></div>` : ''}
  `;
  document.getElementById('ret-importar-enviar').textContent = 'Importar';
}

function abrirImportar() {
  conferenciaImportacao = null;
  document.getElementById('ret-importar-form').reset();
  document.getElementById('ret-importar-conferencia').innerHTML = '';
  document.getElementById('ret-importar-erro').classList.remove('visible');
  document.getElementById('ret-importar-enviar').textContent = 'Conferir planilha';
  document.getElementById('ret-importar-overlay').hidden = false;
}

async function enviarImportar(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('ret-importar-erro');
  const botao = document.getElementById('ret-importar-enviar');
  erroBox.classList.remove('visible');
  botao.disabled = true;
  const textoOriginal = botao.textContent;
  botao.textContent = conferenciaImportacao ? 'Importando...' : 'Conferindo...';
  try {
    if (!conferenciaImportacao) {
      const conferencia = await enviarPlanilha(false);
      if (conferencia === null) return;
      conferenciaImportacao = conferencia;
      renderizarConferencia(conferencia);
      return;
    }
    const resultado = await enviarPlanilha(true);
    if (resultado === null) return;
    document.getElementById('ret-importar-overlay').hidden = true;
    alert(`${resultado.marcacoes_gravadas} marcações importadas.`);
    carregar(document.getElementById('ret-filtro-mes').value);
  } catch (erro) {
    botao.textContent = textoOriginal;
    erroBox.textContent = erro.detalhe || 'Não foi possível ler a planilha agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
  }
}

function iniciar() {
  document.getElementById('ret-filtro-mes').addEventListener('change', (evento) => {
    carregar(evento.target.value);
  });
  document.getElementById('ret-filtro-empresa').addEventListener('change', () => {
    carregar(document.getElementById('ret-filtro-mes').value);
  });
  ['ret-filtro-supervisor', 'ret-filtro-falta'].forEach((id) => {
    document.getElementById(id).addEventListener('change', renderizar);
  });
  document.getElementById('ret-filtro-busca').addEventListener('input', renderizar);

  document.getElementById('ret-conteudo').addEventListener('click', async (evento) => {
    const etiqueta = evento.target.closest('.ret-chip[data-documento]');
    if (etiqueta && !etiqueta.disabled) {
      const { colaborador, ano, mes, documento } = etiqueta.dataset;
      const linha = acharLinha(colaborador, ano, mes);
      const doc = dadosMes.documentos.find((d) => d.chave === documento);
      const celula = linha.celulas[doc.chave];
      const nomeMes = modoTodos() ? ` · ${linha.competencia}` : '';
      RetornoDoc.abrir(
        {
          colaboradorId: linha.id, colaboradorNome: `${linha.nome}${nomeMes}`, ano: Number(ano), mes: Number(mes),
          documento: doc.chave, documentoLabel: celula.label || doc.label, celula,
        },
        aplicarResposta
      );
      return;
    }
    const botaoTudo = evento.target.closest('.ret-btn-tudo');
    if (botaoTudo) {
      botaoTudo.disabled = true;
      try {
        const resposta = await RetornoDoc.marcarTodos(botaoTudo.dataset.colaborador, botaoTudo.dataset.ano, botaoTudo.dataset.mes);
        if (resposta) aplicarResposta(resposta);
      } catch (erro) {
        botaoTudo.disabled = false;
        alert(erro.detalhe || 'Não foi possível marcar agora.');
      }
    }
  });

  document.getElementById('ret-btn-excel').addEventListener('click', (evento) => baixarRelatorio('excel', evento.currentTarget));
  document.getElementById('ret-btn-pdf').addEventListener('click', (evento) => baixarRelatorio('pdf', evento.currentTarget));

  const overlay = document.getElementById('ret-importar-overlay');
  document.getElementById('ret-btn-importar').addEventListener('click', abrirImportar);
  document.getElementById('ret-importar-fechar').addEventListener('click', () => { overlay.hidden = true; });
  overlay.addEventListener('click', (evento) => {
    if (evento.target === overlay) overlay.hidden = true;
  });
  document.getElementById('ret-importar-form').addEventListener('submit', enviarImportar);
  // trocou o arquivo: volta pra conferencia
  document.getElementById('ret-importar-arquivo').addEventListener('change', () => {
    conferenciaImportacao = null;
    document.getElementById('ret-importar-conferencia').innerHTML = '';
    document.getElementById('ret-importar-enviar').textContent = 'Conferir planilha';
  });

  carregarEmpresas();
  carregar();
}

iniciar();
