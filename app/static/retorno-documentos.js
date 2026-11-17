// Painel do mes do Retorno de documentos: a antiga aba da planilha, um
// bloco por supervisor, uma linha por colaborador, uma coluna por documento.
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
  select.innerHTML = opcoes
    .map((o) => {
      const recolhendo = o.valor === `${atual.ano}-${atual.mes}` ? ' · recolhendo agora' : '';
      return `<option value="${o.valor}">${o.label}${recolhendo}</option>`;
    })
    .join('');
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
  const valores = document.querySelectorAll('#ret-kpis .kpi-card .value');
  valores[0].textContent = r.colaboradores;
  valores[1].textContent = r.completos;
  valores[2].textContent = r.com_falta;
  valores[3].textContent = r.documentos_em_falta;
}

function recalcularResumo() {
  const linhas = dadosMes.grupos.flatMap((g) => g.colaboradores);
  dadosMes.resumo = {
    colaboradores: linhas.length,
    completos: linhas.filter((l) => l.em_falta_mes === 0).length,
    com_falta: linhas.filter((l) => l.em_falta_mes > 0).length,
    documentos_em_falta: linhas.reduce((soma, l) => soma + l.em_falta_mes, 0),
  };
}

function linhaHtml(linha) {
  const { documentos, pode_marcar: podeMarcar, ano, mes } = dadosMes;
  const celulas = documentos
    .map((doc) => {
      const celula = linha.celulas[doc.chave];
      const etiqueta = RetornoDoc.etiquetaHtml(doc.label, celula, { colaborador: linha.id, documento: doc.chave }, podeMarcar);
      const obs = celula.observacao ? `<div class="ret-obs">${RetornoDoc.escapar(celula.observacao)}</div>` : '';
      return `<td class="ret-celula">${etiqueta}${obs}</td>`;
    })
    .join('');
  const temPendente = documentos.some((doc) => !linha.celulas[doc.chave].situacao);
  const acao = podeMarcar && temPendente
    ? `<button class="btn-ghost mov-btn-mini ret-btn-tudo" data-colaborador="${linha.id}">Tudo entregue</button>`
    : '';
  const outrosMeses = linha.em_falta_total - linha.em_falta_mes;
  const total = outrosMeses > 0
    ? `<span class="evento-tipo-badge falta" title="Em falta em outros meses">+${outrosMeses} outros meses</span>`
    : '';
  const status = linha.status !== 'ativo' ? ` <span class="badge-inativo">${linha.status === 'afastado' ? 'Afastado' : 'Desligado'}</span>` : '';
  return `
    <tr data-linha="${linha.id}">
      <td><a href="/colaborador-detalhe?id=${linha.id}">${RetornoDoc.escapar(linha.nome)}</a>${status}</td>
      ${celulas}
      <td>${total}</td>
      <td>${acao}</td>
    </tr>`;
}

function renderizar() {
  const container = document.getElementById('ret-conteudo');
  const filtroSupervisor = document.getElementById('ret-filtro-supervisor').value;
  const busca = document.getElementById('ret-filtro-busca').value.trim().toLowerCase();
  const soFalta = document.getElementById('ret-filtro-falta').checked;

  atualizarKpis();
  document.getElementById('ret-legenda').textContent = dadosMes.encerrada
    ? `${dadosMes.nome}: OK entregue · F faltando parte · X não se aplica · ! pendente (em falta) · clique para marcar`
    : `${dadosMes.nome} ainda está em andamento: o que estiver em branco não conta como falta até o mês acabar.`;

  const blocos = dadosMes.grupos
    .filter((g) => !filtroSupervisor || g.supervisor_nome === filtroSupervisor)
    .map((g) => {
      const linhas = g.colaboradores.filter(
        (l) => (!busca || l.nome.toLowerCase().includes(busca)) && (!soFalta || l.em_falta_total > 0)
      );
      if (linhas.length === 0) return '';
      const comFalta = g.colaboradores.filter((l) => l.em_falta_mes > 0).length;
      return `
        <div class="avisos-header" style="margin-top: 22px;">
          <span class="section-title" style="margin: 0;">${RetornoDoc.escapar(g.supervisor_nome)}</span>
          <span class="meta">${g.colaboradores.length} colaboradores${comFalta ? ` · <span class="badge-inativo">${comFalta} com falta</span>` : ' · tudo em dia'}</span>
        </div>
        <div class="table-scroll-wrapper"><table class="table-list ret-tabela">
          <thead><tr><th>Funcionário</th>${dadosMes.documentos.map((d) => `<th>${d.label}</th>`).join('')}<th></th><th></th></tr></thead>
          <tbody>${linhas.map(linhaHtml).join('')}</tbody>
        </table></div>`;
    })
    .join('');

  container.innerHTML = blocos || '<div class="empty-state">Nenhum colaborador com esses filtros.</div>';
}

async function carregar(ano, mes) {
  const container = document.getElementById('ret-conteudo');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const query = ano ? `?ano=${ano}&mes=${mes}` : '';
    const dados = await Shell.chamarApi(`/retorno-documentos-dados${query}`);
    if (dados === null) return;
    dadosMes = dados;
    if (!document.getElementById('ret-filtro-mes').options.length) {
      popularSelectMes(dados.inicio, dados.competencia_atual);
    }
    document.getElementById('ret-filtro-mes').value = `${dados.ano}-${dados.mes}`;
    document.getElementById('ret-btn-importar').hidden = !dados.pode_marcar || Shell.autenticacao().papel !== 'escritorio';
    popularSelectSupervisor(dados.grupos);
    renderizar();
  } catch (erro) {
    container.innerHTML = `<div class="empty-state">${RetornoDoc.escapar(erro.detalhe || 'Não foi possível carregar agora.')}</div>`;
  }
}

// troca a linha do colaborador pela que o servidor devolveu depois de marcar
function aplicarResposta(resposta) {
  const nova = resposta.linha;
  dadosMes.grupos.forEach((g) => {
    g.colaboradores = g.colaboradores.map((l) => (l.id === nova.id ? nova : l));
  });
  recalcularResumo();
  renderizar();
}

function acharLinha(colaboradorId) {
  for (const g of dadosMes.grupos) {
    const linha = g.colaboradores.find((l) => l.id === Number(colaboradorId));
    if (linha) return linha;
  }
  return null;
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
    carregar(dadosMes.ano, dadosMes.mes);
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
    const [ano, mes] = evento.target.value.split('-').map(Number);
    carregar(ano, mes);
  });
  ['ret-filtro-supervisor', 'ret-filtro-falta'].forEach((id) => {
    document.getElementById(id).addEventListener('change', renderizar);
  });
  document.getElementById('ret-filtro-busca').addEventListener('input', renderizar);

  document.getElementById('ret-conteudo').addEventListener('click', async (evento) => {
    const etiqueta = evento.target.closest('.ret-chip[data-documento]');
    if (etiqueta && !etiqueta.disabled) {
      const linha = acharLinha(etiqueta.dataset.colaborador);
      const doc = dadosMes.documentos.find((d) => d.chave === etiqueta.dataset.documento);
      RetornoDoc.abrir(
        {
          colaboradorId: linha.id, colaboradorNome: linha.nome, ano: dadosMes.ano, mes: dadosMes.mes,
          documento: doc.chave, documentoLabel: doc.label, celula: linha.celulas[doc.chave],
        },
        aplicarResposta
      );
      return;
    }
    const botaoTudo = evento.target.closest('.ret-btn-tudo');
    if (botaoTudo) {
      botaoTudo.disabled = true;
      try {
        const resposta = await RetornoDoc.marcarTodos(botaoTudo.dataset.colaborador, dadosMes.ano, dadosMes.mes);
        if (resposta) aplicarResposta(resposta);
      } catch (erro) {
        botaoTudo.disabled = false;
        alert(erro.detalhe || 'Não foi possível marcar agora.');
      }
    }
  });

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

  carregar();
}

iniciar();
