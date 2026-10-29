const auth = Shell.montar('gerencia', 'Gerência');

let dados = null; // resposta de /gerencia-dados/movimentacao do mes escolhido
let empresaAtivaId = null;
let filtro = { busca: '', remessa: '', situacao: '' };
let linhaEmEdicao = null; // null = adicionando

const SITUACOES = [
  { chave: '', label: 'Todas' },
  { chave: 'sem_nota', label: 'Sem nº de nota' },
  { chave: 'boleto', label: 'Boleto pendente' },
  { chave: 'envio', label: 'Envio ao cliente pendente' },
  { chave: 'documentos', label: 'Documentos pendentes' },
];

function escaparHtml(texto) {
  if (texto === null || texto === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(texto);
  return div.innerHTML.replace(/"/g, '&quot;'); // tambem vai dentro de value="..."
}

function formatarMoeda(valor) {
  return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarPercentual(valor) {
  return valor === null || valor === undefined ? '' : String(valor).replace('.', ',');
}

function lerNumero(texto) {
  // aceita 1.885,50 / 1885,50 / 1885.50
  let limpo = String(texto || '').trim().replace(/\s|R\$/g, '');
  if (!limpo) return null;
  if (limpo.includes(',')) limpo = limpo.replace(/\./g, '').replace(',', '.');
  const numero = Number(limpo);
  return Number.isFinite(numero) ? numero : NaN;
}

function valorParaInput(valor) {
  return valor === null || valor === undefined ? '' : Number(valor).toFixed(2).replace('.', ',');
}

function nomeMes(mes) {
  return ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'][mes - 1];
}

function mesSelecionado() {
  const [ano, mes] = document.getElementById('mov-mes').value.split('-').map(Number);
  return { ano, mes };
}

function empresaAtiva() {
  return dados ? dados.empresas.find((e) => e.id === empresaAtivaId) : null;
}

function movAtiva() {
  const empresa = empresaAtiva();
  return empresa ? empresa.movimentacao : null;
}

function mostrarErro(idCaixa, erro, padrao) {
  const caixa = document.getElementById(idCaixa);
  caixa.textContent = (erro && erro.detalhe) || padrao;
  caixa.classList.add('visible');
}

// ---------- carregamento ----------

async function carregar() {
  const { ano, mes } = mesSelecionado();
  const conteudo = document.getElementById('mov-conteudo');
  conteudo.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    dados = await Shell.chamarApi(`/gerencia-dados/movimentacao?ano=${ano}&mes=${mes}`);
    if (!dados) return;
    if (!dados.empresas.some((e) => e.id === empresaAtivaId)) {
      empresaAtivaId = dados.empresas.length ? dados.empresas[0].id : null;
    }
    renderizarAbas();
    renderizarConteudo();
  } catch (erro) {
    document.getElementById('mov-abas').innerHTML = '';
    conteudo.innerHTML = erro.status === 403
      ? '<div class="empty-state">Esta área é exclusiva da gerência.</div>'
      : '<div class="empty-state">Não foi possível carregar a movimentação.</div>';
  }
}

function renderizarAbas() {
  document.getElementById('mov-abas').innerHTML = dados.empresas
    .map((e) => {
      const qtd = e.movimentacao ? e.movimentacao.totais.quantidade : null;
      const detalhe = qtd === null ? ' <span class="mov-aba-vazia">· sem lançamento</span>' : ` <span class="mov-aba-qtd">${qtd}</span>`;
      return `<button class="tab-relatorio${e.id === empresaAtivaId ? ' ativa' : ''}" data-empresa-id="${e.id}">${escaparHtml(e.nome)}${detalhe}</button>`;
    })
    .join('');
}

function renderizarConteudo() {
  const empresa = empresaAtiva();
  const conteudo = document.getElementById('mov-conteudo');
  if (!empresa) {
    conteudo.innerHTML = '<div class="empty-state">Nenhuma empresa cadastrada.</div>';
    return;
  }
  if (!empresa.movimentacao) {
    conteudo.innerHTML = htmlSemMovimentacao(empresa);
    return;
  }
  const mov = empresa.movimentacao;
  conteudo.innerHTML = `
    ${htmlAliquotas(mov)}
    <div class="kpi-grid" id="mov-kpis"></div>
    <div class="mov-pendencias" id="mov-pendencias"></div>
    ${htmlFiltros(mov)}
    <div class="table-scroll-wrapper" id="mov-tabela"></div>
  `;
  renderizarResumo();
  renderizarTabela();
}

function htmlSemMovimentacao(empresa) {
  const faltando = dados.empresas.filter((e) => !e.movimentacao);
  const botaoAnterior = empresa.anterior
    ? `<button class="btn-primary mov-btn-auto" data-acao="gerar" data-empresa-id="${empresa.id}">Gerar a partir de ${nomeMes(empresa.anterior.mes)}/${empresa.anterior.ano}</button>`
    : '';
  const botaoTodas = faltando.length > 1 && faltando.some((e) => e.anterior)
    ? `<button class="btn-ghost" data-acao="gerar-todas">Gerar para as ${faltando.length} empresas sem lançamento</button>`
    : '';
  return `
    <div class="dash-card mov-vazio">
      <p><strong>${escaparHtml(empresa.nome)}</strong> ainda não tem movimentação em ${nomeMes(dados.mes)}/${dados.ano}.</p>
      <p class="mov-dica">${empresa.anterior
        ? 'Gerando a partir do mês anterior, os clientes, valores fixos, vencimentos, observações fixas e alíquotas vêm copiados. Número da nota, status e descontos do mês ficam em branco.'
        : 'Não há mês anterior lançado. Você pode importar a planilha do Excel (botão "Importar planilha" acima) ou começar vazio e adicionar os clientes.'}</p>
      <div class="mov-botoes">
        ${botaoAnterior}
        ${botaoTodas}
        <button class="btn-ghost" data-acao="gerar-vazio" data-empresa-id="${empresa.id}">Começar vazio</button>
      </div>
    </div>
  `;
}

function htmlAliquotas(mov) {
  const bloqueado = mov.fechado ? 'disabled' : '';
  const campo = (id, label, valor) => `
    <div class="field">
      <label for="${id}">${label}</label>
      <input type="text" inputmode="decimal" id="${id}" value="${formatarPercentual(valor)}" ${bloqueado}>
    </div>`;
  return `
    <div class="dash-card mov-aliquotas">
      <div class="mov-aliquotas-campos">
        ${campo('mov-aliq-iss', 'ISS %', mov.aliquota_iss)}
        ${campo('mov-aliq-inss', 'INSS (CP) %', mov.aliquota_inss)}
        ${campo('mov-aliq-simples-limpeza', 'Simples limpeza %', mov.simples_limpeza)}
        ${campo('mov-aliq-simples-apoio', 'Simples apoio %', mov.simples_apoio)}
        ${mov.fechado ? '' : '<button class="btn-ghost" data-acao="salvar-aliquotas">Salvar alíquotas</button>'}
      </div>
      <div class="mov-aliquotas-status">
        <span class="status-badge ${mov.fechado ? 'mov-status-fechado' : 'mov-status-aberto'}">${mov.fechado ? 'Mês fechado' : 'Mês aberto'}</span>
        <button class="btn-ghost" data-acao="${mov.fechado ? 'reabrir' : 'fechar'}">${mov.fechado ? 'Reabrir mês' : 'Fechar mês'}</button>
        ${mov.fechado ? '' : '<button class="btn-ghost mov-btn-perigo" data-acao="excluir-mes">Excluir mês</button>'}
      </div>
      <div class="error-message" id="mov-aliquotas-erro"></div>
    </div>
  `;
}

function htmlFiltros(mov) {
  const remessas = [...new Set(mov.linhas.map((l) => l.remessa))].sort((a, b) => a - b);
  return `
    <div class="filter-row mov-filtros">
      <div class="field">
        <label for="mov-busca">Buscar</label>
        <input type="text" id="mov-busca" placeholder="Cliente, CNPJ, nº da nota..." value="${escaparHtml(filtro.busca)}">
      </div>
      <div class="field">
        <label for="mov-filtro-remessa">Remessa</label>
        <select id="mov-filtro-remessa">
          <option value="">Todas</option>
          ${remessas.map((r) => `<option value="${r}" ${String(r) === filtro.remessa ? 'selected' : ''}>${r}ª remessa</option>`).join('')}
        </select>
      </div>
      <div class="field">
        <label for="mov-filtro-situacao">Situação</label>
        <select id="mov-filtro-situacao">
          ${SITUACOES.map((s) => `<option value="${s.chave}" ${s.chave === filtro.situacao ? 'selected' : ''}>${s.label}</option>`).join('')}
        </select>
      </div>
      ${mov.fechado ? '' : `
        <div class="mov-botoes">
          <button class="btn-ghost" data-acao="numerar">Numerar notas</button>
          <button class="btn-primary mov-btn-auto" data-acao="adicionar">+ Adicionar cliente</button>
        </div>`}
    </div>
  `;
}

function renderizarResumo() {
  const mov = movAtiva();
  if (!mov) return;
  // totais recalculados no navegador para refletir edicoes rapidas sem recarregar
  const soma = (chave) => mov.linhas.reduce((s, l) => s + l[chave], 0);
  const linhas = mov.linhas;
  document.getElementById('mov-kpis').innerHTML = `
    <div class="kpi-card"><div><div class="label">valor das notas</div><div class="value">${formatarMoeda(soma('valor_nota'))}</div><div class="sub">${linhas.length} clientes</div></div></div>
    <div class="kpi-card"><div><div class="label">ISS retido</div><div class="value">${formatarMoeda(soma('valor_iss'))}</div><div class="sub">${formatarPercentual(mov.aliquota_iss)}%</div></div></div>
    <div class="kpi-card"><div><div class="label">INSS retido</div><div class="value">${formatarMoeda(soma('valor_inss'))}</div><div class="sub">${formatarPercentual(mov.aliquota_inss)}%</div></div></div>
    <div class="kpi-card"><div><div class="label">total em boletos</div><div class="value">${formatarMoeda(soma('valor_boleto'))}</div></div></div>
  `;
  const pend = [
    [linhas.filter((l) => l.numero_nota === null).length, 'sem nº de nota'],
    [linhas.filter((l) => !l.boleto_ok).length, 'boletos pendentes'],
    [linhas.filter((l) => !l.cliente_ok).length, 'envios ao cliente pendentes'],
    [linhas.filter((l) => l.exige_documentos && !l.documentos_ok).length, 'documentos pendentes'],
  ];
  const texto = pend.filter(([n]) => n > 0).map(([n, label]) => `<strong>${n}</strong> ${label}`).join(' · ');
  document.getElementById('mov-pendencias').innerHTML = texto ? `Pendências: ${texto}` : '<span class="mov-tudo-ok">Tudo emitido e enviado ✓</span>';
}

function linhaPassaNoFiltro(l) {
  if (filtro.remessa && String(l.remessa) !== filtro.remessa) return false;
  if (filtro.situacao === 'sem_nota' && l.numero_nota !== null) return false;
  if (filtro.situacao === 'boleto' && l.boleto_ok) return false;
  if (filtro.situacao === 'envio' && l.cliente_ok) return false;
  if (filtro.situacao === 'documentos' && !(l.exige_documentos && !l.documentos_ok)) return false;
  if (filtro.busca) {
    const termo = filtro.busca.toLowerCase();
    const alvo = [l.nome_cliente, l.cnpj, l.municipio, l.numero_nota, l.observacao, l.observacao_mes].join(' ').toLowerCase();
    if (!alvo.includes(termo)) return false;
  }
  return true;
}

function renderizarTabela() {
  const mov = movAtiva();
  const container = document.getElementById('mov-tabela');
  if (!mov.linhas.length) {
    container.innerHTML = '<div class="empty-state">Nenhum cliente neste mês ainda. Use "+ Adicionar cliente".</div>';
    return;
  }
  const visiveis = mov.linhas.filter(linhaPassaNoFiltro);
  if (!visiveis.length) {
    container.innerHTML = '<div class="empty-state">Nenhum cliente com esse filtro.</div>';
    return;
  }
  const bloqueado = mov.fechado ? 'disabled' : '';
  const tipos = Object.fromEntries(dados.tipos_servico.map((t) => [t.chave, t.label.split(' (')[0]]));

  let html = '';
  let remessaAtual = null;
  let subtotal = null;
  const fecharGrupo = () => {
    if (subtotal) {
      html += `<tr class="mov-subtotal"><td colspan="2">Subtotal ${remessaAtual}ª remessa (${subtotal.qtd})</td><td class="mov-num">${formatarMoeda(subtotal.nota)}</td><td class="mov-num">${formatarMoeda(subtotal.iss)}</td><td class="mov-num">${formatarMoeda(subtotal.inss)}</td><td class="mov-num">${formatarMoeda(subtotal.boleto)}</td><td colspan="6"></td></tr>`;
    }
  };
  visiveis.forEach((l) => {
    if (l.remessa !== remessaAtual) {
      fecharGrupo();
      remessaAtual = l.remessa;
      subtotal = { qtd: 0, nota: 0, iss: 0, inss: 0, boleto: 0 };
      html += `<tr class="mov-grupo"><td colspan="12">${l.remessa}ª remessa</td></tr>`;
    }
    subtotal.qtd += 1;
    subtotal.nota += l.valor_nota;
    subtotal.iss += l.valor_iss;
    subtotal.inss += l.valor_inss;
    subtotal.boleto += l.valor_boleto;
    const detalhes = [l.cnpj, l.municipio].filter(Boolean).join(' · ');
    const obs = [l.observacao, l.observacao_mes].filter(Boolean).join(' — ');
    const composicao = l.composicao.length > 1
      ? `<div class="mov-composicao-resumo">${l.composicao.map((i) => `${escaparHtml(i.descricao || 'item')} ${formatarMoeda(i.valor)}`).join(' + ')}</div>`
      : '';
    html += `
      <tr data-linha-id="${l.id}">
        <td>
          <a href="#" class="mov-link-editar" data-linha-id="${l.id}">${escaparHtml(l.nome_cliente)}</a>
          ${detalhes ? `<div class="mov-sub">${escaparHtml(detalhes)}</div>` : ''}
          ${composicao}
          ${obs ? `<div class="mov-obs" title="${escaparHtml(obs)}">${escaparHtml(obs)}</div>` : ''}
        </td>
        <td>${escaparHtml(tipos[l.tipo_servico] || l.tipo_servico)}</td>
        <td class="mov-num">${formatarMoeda(l.valor_nota)}</td>
        <td class="mov-num">${l.retem_iss ? formatarMoeda(l.valor_iss) : '—'}</td>
        <td class="mov-num">${l.retem_inss ? formatarMoeda(l.valor_inss) : '—'}</td>
        <td class="mov-num"><strong>${formatarMoeda(l.valor_boleto)}</strong></td>
        <td><input type="number" class="mov-inline mov-inline-nota" data-campo="numero_nota" value="${l.numero_nota ?? ''}" min="1" ${bloqueado} aria-label="Nº da nota"></td>
        <td><input type="text" class="mov-inline mov-inline-venc" data-campo="vencimento" value="${escaparHtml(l.vencimento ?? '')}" maxlength="20" ${bloqueado} aria-label="Vencimento"></td>
        <td class="mov-centro"><input type="checkbox" data-campo="boleto_ok" ${l.boleto_ok ? 'checked' : ''} ${bloqueado} aria-label="Boleto emitido"></td>
        <td class="mov-centro"><input type="checkbox" data-campo="cliente_ok" ${l.cliente_ok ? 'checked' : ''} ${bloqueado} aria-label="Enviado ao cliente"></td>
        <td class="mov-centro">${l.exige_documentos ? `<input type="checkbox" data-campo="documentos_ok" ${l.documentos_ok ? 'checked' : ''} ${bloqueado} aria-label="Documentos enviados">` : '<span class="mov-sub">—</span>'}</td>
        <td><button class="btn-ghost mov-btn-mini mov-link-editar" data-linha-id="${l.id}">${mov.fechado ? 'Ver' : 'Editar'}</button></td>
      </tr>`;
  });
  fecharGrupo();

  container.innerHTML = `
    <table class="table-list mov-tabela">
      <thead>
        <tr>
          <th>Cliente</th><th>Serviço</th><th class="mov-num">Valor nota</th><th class="mov-num">ISS</th><th class="mov-num">INSS</th><th class="mov-num">Boleto</th>
          <th>Nº NF</th><th>Venc.</th><th class="mov-centro">Boleto</th><th class="mov-centro">Enviado</th><th class="mov-centro">Docs</th><th></th>
        </tr>
      </thead>
      <tbody>${html}</tbody>
    </table>
  `;
}

// ---------- edicao rapida na tabela ----------

async function salvarCampoInline(input) {
  const linhaId = Number(input.closest('tr').dataset.linhaId);
  const campo = input.dataset.campo;
  let valor;
  if (input.type === 'checkbox') {
    valor = input.checked;
  } else if (campo === 'numero_nota') {
    valor = input.value === '' ? null : Number(input.value);
  } else {
    valor = input.value.trim() || null;
  }
  input.classList.remove('mov-inline-erro');
  try {
    const atualizada = await Shell.chamarApi(`/gerencia-dados/movimentacao/linhas/${linhaId}`, { method: 'PATCH', body: { [campo]: valor } });
    if (!atualizada) return;
    const mov = movAtiva();
    mov.linhas = mov.linhas.map((l) => (l.id === atualizada.id ? atualizada : l));
    input.classList.add('mov-inline-salvo');
    setTimeout(() => input.classList.remove('mov-inline-salvo'), 900);
    renderizarResumo();
  } catch (erro) {
    input.classList.add('mov-inline-erro');
    if (input.type === 'checkbox') input.checked = !input.checked;
    alert((erro && erro.detalhe) || 'Não foi possível salvar.');
  }
}

// ---------- acoes do mes ----------

async function gerar(empresaId, vazio) {
  const { ano, mes } = mesSelecionado();
  try {
    await Shell.chamarApi('/gerencia-dados/movimentacao/gerar', { method: 'POST', body: { ano, mes, empresa_id: empresaId, vazio } });
    await carregar();
  } catch (erro) {
    alert((erro && erro.detalhe) || 'Não foi possível gerar o mês.');
  }
}

async function atualizarMes(corpo, idErro) {
  const mov = movAtiva();
  try {
    const atualizado = await Shell.chamarApi(`/gerencia-dados/movimentacao/meses/${mov.id}`, { method: 'PATCH', body: corpo });
    if (!atualizado) return;
    empresaAtiva().movimentacao = atualizado;
    renderizarAbas();
    renderizarConteudo();
  } catch (erro) {
    if (idErro) mostrarErro(idErro, erro, 'Não foi possível salvar.');
    else alert((erro && erro.detalhe) || 'Não foi possível salvar.');
  }
}

function salvarAliquotas() {
  const campos = {
    aliquota_iss: lerNumero(document.getElementById('mov-aliq-iss').value),
    aliquota_inss: lerNumero(document.getElementById('mov-aliq-inss').value),
    simples_limpeza: lerNumero(document.getElementById('mov-aliq-simples-limpeza').value),
    simples_apoio: lerNumero(document.getElementById('mov-aliq-simples-apoio').value),
  };
  if (Object.values(campos).some((v) => Number.isNaN(v))) {
    mostrarErro('mov-aliquotas-erro', null, 'Alíquota inválida. Use números, ex: 4,62');
    return;
  }
  atualizarMes(campos, 'mov-aliquotas-erro');
}

async function excluirMes() {
  const empresa = empresaAtiva();
  if (!confirm(`Excluir toda a movimentação de ${empresa.nome} em ${nomeMes(dados.mes)}/${dados.ano}? Isso não pode ser desfeito.`)) return;
  try {
    await Shell.chamarApi(`/gerencia-dados/movimentacao/meses/${empresa.movimentacao.id}`, { method: 'DELETE' });
    await carregar();
  } catch (erro) {
    alert((erro && erro.detalhe) || 'Não foi possível excluir.');
  }
}

// ---------- modal de cliente ----------

function abrirModal(id) {
  document.getElementById(id).hidden = false;
}

function fecharModal(id) {
  document.getElementById(id).hidden = true;
}

function linhaComposicaoHtml(item, bloqueado) {
  return `
    <div class="mov-item-composicao">
      <input type="text" class="mov-item-desc" placeholder="Descrição" value="${escaparHtml(item.descricao || '')}" maxlength="100" ${bloqueado}>
      <input type="text" inputmode="decimal" class="mov-item-valor" placeholder="0,00" value="${valorParaInput(item.valor)}" ${bloqueado}>
      <label class="mov-check mov-item-fixo" title="Passa para o mês seguinte"><input type="checkbox" class="mov-item-fixo-check" ${item.fixo ? 'checked' : ''} ${bloqueado}> todo mês</label>
      <button type="button" class="btn-ghost mov-btn-mini mov-item-remover" aria-label="Remover item" ${bloqueado}>&times;</button>
    </div>`;
}

function lerComposicao() {
  return [...document.querySelectorAll('#mov-composicao .mov-item-composicao')].map((linha) => ({
    descricao: linha.querySelector('.mov-item-desc').value.trim(),
    valor: lerNumero(linha.querySelector('.mov-item-valor').value),
    fixo: linha.querySelector('.mov-item-fixo-check').checked,
  }));
}

function atualizarPrevia() {
  const mov = movAtiva();
  const itens = lerComposicao().filter((i) => i.valor !== null && !Number.isNaN(i.valor));
  const nota = Math.round(itens.reduce((s, i) => s + i.valor, 0) * 100) / 100;
  const iss = document.getElementById('mov-linha-retem-iss').checked ? Math.round(nota * mov.aliquota_iss) / 100 : 0;
  const inss = document.getElementById('mov-linha-retem-inss').checked ? Math.round(nota * mov.aliquota_inss) / 100 : 0;
  document.getElementById('mov-previa').innerHTML = `
    <span>Nota <strong>${formatarMoeda(nota)}</strong></span>
    <span>ISS ${formatarMoeda(iss)}</span>
    <span>INSS ${formatarMoeda(inss)}</span>
    <span>Boleto <strong>${formatarMoeda(nota - iss - inss)}</strong></span>`;
}

function aplicarPadraoTipo() {
  const tipo = dados.tipos_servico.find((t) => t.chave === document.getElementById('mov-linha-tipo').value);
  if (!tipo) return;
  document.getElementById('mov-linha-retem-iss').checked = tipo.retem_iss;
  document.getElementById('mov-linha-retem-inss').checked = tipo.retem_inss;
  atualizarPrevia();
}

function abrirModalLinha(linha) {
  const mov = movAtiva();
  const empresa = empresaAtiva();
  linhaEmEdicao = linha;
  const bloqueado = mov.fechado ? 'disabled' : '';
  document.getElementById('mov-linha-erro').classList.remove('visible');
  document.getElementById('mov-linha-titulo').textContent = linha ? linha.nome_cliente : `Adicionar cliente · ${empresa.nome}`;
  document.getElementById('mov-lista-clientes').innerHTML = empresa.clientes.map((c) => `<option value="${escaparHtml(c.nome)}"></option>`).join('');
  document.getElementById('mov-linha-remessa').innerHTML = Array.from({ length: dados.maximo_remessa }, (_, i) => `<option value="${i + 1}">${i + 1}ª remessa</option>`).join('');
  document.getElementById('mov-linha-tipo').innerHTML = dados.tipos_servico.map((t) => `<option value="${t.chave}">${escaparHtml(t.label)} (${t.ctn})</option>`).join('');

  const l = linha || {
    nome_cliente: '', cnpj: '', municipio: '', remessa: 1, tipo_servico: dados.tipos_servico[0].chave,
    retem_iss: dados.tipos_servico[0].retem_iss, retem_inss: dados.tipos_servico[0].retem_inss,
    composicao: [{ descricao: 'Valor mensal', valor: null, fixo: true }],
    numero_nota: null, vencimento: '', exige_documentos: false, observacao: '', observacao_mes: '',
  };
  document.getElementById('mov-linha-cliente').value = l.nome_cliente;
  document.getElementById('mov-linha-cnpj').value = l.cnpj || '';
  document.getElementById('mov-linha-municipio').value = l.municipio || '';
  document.getElementById('mov-linha-remessa').value = String(l.remessa);
  document.getElementById('mov-linha-tipo').value = l.tipo_servico;
  document.getElementById('mov-linha-retem-iss').checked = l.retem_iss;
  document.getElementById('mov-linha-retem-inss').checked = l.retem_inss;
  document.getElementById('mov-linha-nota').value = l.numero_nota ?? '';
  document.getElementById('mov-linha-vencimento').value = l.vencimento || '';
  document.getElementById('mov-linha-exige-docs').checked = l.exige_documentos;
  document.getElementById('mov-linha-obs').value = l.observacao || '';
  document.getElementById('mov-linha-obs-mes').value = l.observacao_mes || '';
  const itens = l.composicao.length ? l.composicao : [{ descricao: 'Valor mensal', valor: null, fixo: true }];
  document.getElementById('mov-composicao').innerHTML = itens.map((i) => linhaComposicaoHtml(i, bloqueado)).join('');

  document.querySelectorAll('#mov-linha-form input, #mov-linha-form select, #mov-linha-form textarea').forEach((el) => { el.disabled = mov.fechado; });
  document.getElementById('mov-btn-add-item').hidden = mov.fechado;
  document.getElementById('mov-linha-salvar').hidden = mov.fechado;
  document.getElementById('mov-linha-excluir').hidden = !linha || mov.fechado;
  atualizarPrevia();
  abrirModal('mov-modal-linha');
  if (!mov.fechado) document.getElementById('mov-linha-cliente').focus();
}

function preencherDoCadastro() {
  const nome = document.getElementById('mov-linha-cliente').value.trim().toLowerCase();
  const cliente = empresaAtiva().clientes.find((c) => c.nome.toLowerCase() === nome);
  if (!cliente) return;
  if (cliente.cnpj) document.getElementById('mov-linha-cnpj').value = cliente.cnpj;
  if (cliente.municipio) document.getElementById('mov-linha-municipio').value = cliente.municipio.toUpperCase();
}

async function salvarLinha(evento) {
  evento.preventDefault();
  const mov = movAtiva();
  const nome = document.getElementById('mov-linha-cliente').value.trim();
  const composicao = lerComposicao().filter((i) => i.descricao || i.valor !== null);
  if (!composicao.length || composicao.some((i) => i.valor === null || Number.isNaN(i.valor))) {
    mostrarErro('mov-linha-erro', null, 'Preencha os valores da nota com números (ex: 1.885,50).');
    return;
  }
  const cadastro = empresaAtiva().clientes.find((c) => c.nome.toLowerCase() === nome.toLowerCase());
  const notaTexto = document.getElementById('mov-linha-nota').value;
  const corpo = {
    cliente_id: cadastro ? cadastro.id : null,
    nome_cliente: nome,
    cnpj: document.getElementById('mov-linha-cnpj').value,
    municipio: document.getElementById('mov-linha-municipio').value,
    remessa: Number(document.getElementById('mov-linha-remessa').value),
    tipo_servico: document.getElementById('mov-linha-tipo').value,
    retem_iss: document.getElementById('mov-linha-retem-iss').checked,
    retem_inss: document.getElementById('mov-linha-retem-inss').checked,
    composicao,
    numero_nota: notaTexto === '' ? null : Number(notaTexto),
    vencimento: document.getElementById('mov-linha-vencimento').value,
    exige_documentos: document.getElementById('mov-linha-exige-docs').checked,
    observacao: document.getElementById('mov-linha-obs').value,
    observacao_mes: document.getElementById('mov-linha-obs-mes').value,
  };
  const botao = document.getElementById('mov-linha-salvar');
  botao.disabled = true;
  try {
    const caminho = linhaEmEdicao
      ? `/gerencia-dados/movimentacao/linhas/${linhaEmEdicao.id}`
      : `/gerencia-dados/movimentacao/meses/${mov.id}/linhas`;
    const salva = await Shell.chamarApi(caminho, { method: linhaEmEdicao ? 'PATCH' : 'POST', body: corpo });
    if (!salva) return;
    if (linhaEmEdicao) {
      mov.linhas = mov.linhas.map((l) => (l.id === salva.id ? salva : l));
    } else {
      mov.linhas.push(salva);
    }
    mov.linhas.sort((a, b) => a.remessa - b.remessa || a.ordem - b.ordem || a.id - b.id);
    fecharModal('mov-modal-linha');
    renderizarAbas();
    renderizarConteudo();
  } catch (erro) {
    mostrarErro('mov-linha-erro', erro, 'Não foi possível salvar.');
  } finally {
    botao.disabled = false;
  }
}

async function excluirLinha() {
  if (!linhaEmEdicao || !confirm(`Remover ${linhaEmEdicao.nome_cliente} da movimentação deste mês?`)) return;
  try {
    await Shell.chamarApi(`/gerencia-dados/movimentacao/linhas/${linhaEmEdicao.id}`, { method: 'DELETE' });
    const mov = movAtiva();
    mov.linhas = mov.linhas.filter((l) => l.id !== linhaEmEdicao.id);
    fecharModal('mov-modal-linha');
    renderizarAbas();
    renderizarConteudo();
  } catch (erro) {
    mostrarErro('mov-linha-erro', erro, 'Não foi possível remover.');
  }
}

// ---------- numerar notas ----------

function abrirModalNumerar() {
  const mov = movAtiva();
  const empresa = empresaAtiva();
  const remessas = [...new Set(mov.linhas.filter((l) => l.numero_nota === null).map((l) => l.remessa))].sort((a, b) => a - b);
  if (!remessas.length) {
    alert('Todos os clientes deste mês já têm número de nota.');
    return;
  }
  document.getElementById('mov-numerar-erro').classList.remove('visible');
  document.getElementById('mov-numerar-remessa').innerHTML = '<option value="">Todas as remessas</option>'
    + remessas.map((r) => `<option value="${r}">${r}ª remessa</option>`).join('');
  document.getElementById('mov-numerar-inicio').value = empresa.proximo_numero_nota ?? '';
  abrirModal('mov-modal-numerar');
}

async function numerarNotas(evento) {
  evento.preventDefault();
  const mov = movAtiva();
  const remessa = document.getElementById('mov-numerar-remessa').value;
  try {
    const atualizado = await Shell.chamarApi(`/gerencia-dados/movimentacao/meses/${mov.id}/numerar`, {
      method: 'POST',
      body: { numero_inicial: Number(document.getElementById('mov-numerar-inicio').value), remessa: remessa ? Number(remessa) : null },
    });
    if (!atualizado) return;
    fecharModal('mov-modal-numerar');
    await carregar();
  } catch (erro) {
    mostrarErro('mov-numerar-erro', erro, 'Não foi possível numerar.');
  }
}

// ---------- importar / baixar ----------

function abrirModalImportar() {
  const { ano, mes } = mesSelecionado();
  document.getElementById('mov-importar-erro').classList.remove('visible');
  document.getElementById('mov-importar-mes').textContent = `${nomeMes(mes)}/${ano}`;
  document.getElementById('mov-importar-form').reset();
  abrirModal('mov-modal-importar');
}

async function importarPlanilha(evento) {
  evento.preventDefault();
  const { ano, mes } = mesSelecionado();
  const arquivo = document.getElementById('mov-importar-arquivo').files[0];
  if (!arquivo) return;
  const formData = new FormData();
  formData.append('ano', ano);
  formData.append('mes', mes);
  formData.append('substituir', document.getElementById('mov-importar-substituir').checked);
  formData.append('arquivo', arquivo);
  const botao = document.getElementById('mov-importar-enviar');
  botao.disabled = true;
  botao.textContent = 'Importando...';
  try {
    const autenticacao = Shell.autenticacao();
    const resposta = await fetch('/gerencia-dados/movimentacao/importar', {
      method: 'POST',
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
      body: formData,
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    const corpo = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw Object.assign(new Error('falha'), { detalhe: corpo.detail });
    fecharModal('mov-modal-importar');
    const resumo = corpo.importadas.map((i) => `${i.empresa}: ${i.linhas} clientes`).join('\n');
    const ignoradas = corpo.ignoradas.length ? `\n\nAbas ignoradas (não são de uma empresa): ${corpo.ignoradas.join(', ')}` : '';
    alert(`Planilha importada.\n\n${resumo}${ignoradas}`);
    await carregar();
  } catch (erro) {
    mostrarErro('mov-importar-erro', erro, 'Não foi possível importar a planilha.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Importar';
  }
}

async function baixar(formato) {
  const { ano, mes } = mesSelecionado();
  const botao = document.getElementById(formato === 'pdf' ? 'mov-btn-pdf' : 'mov-btn-excel');
  const textoOriginal = botao.textContent;
  botao.disabled = true;
  botao.textContent = 'Gerando...';
  try {
    const autenticacao = Shell.autenticacao();
    const resposta = await fetch(`/gerencia-dados/movimentacao/${formato}?ano=${ano}&mes=${mes}`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      alert(corpo.detail || 'Não foi possível gerar o arquivo.');
      return;
    }
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `movimentacao-${ano}-${String(mes).padStart(2, '0')}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (erro) {
    alert('Não foi possível gerar o arquivo agora.');
  } finally {
    botao.disabled = false;
    botao.textContent = textoOriginal;
  }
}

// ---------- eventos ----------

function iniciar() {
  const hoje = new Date();
  document.getElementById('mov-mes').value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;
  document.getElementById('mov-mes').addEventListener('change', () => {
    if (document.getElementById('mov-mes').value) carregar();
  });
  document.getElementById('mov-btn-importar').addEventListener('click', abrirModalImportar);
  document.getElementById('mov-btn-excel').addEventListener('click', () => baixar('excel'));
  document.getElementById('mov-btn-pdf').addEventListener('click', () => baixar('pdf'));

  document.getElementById('mov-abas').addEventListener('click', (evento) => {
    const aba = evento.target.closest('[data-empresa-id]');
    if (!aba) return;
    empresaAtivaId = Number(aba.dataset.empresaId);
    filtro = { busca: '', remessa: '', situacao: '' };
    renderizarAbas();
    renderizarConteudo();
  });

  const conteudo = document.getElementById('mov-conteudo');
  conteudo.addEventListener('click', (evento) => {
    const editar = evento.target.closest('.mov-link-editar');
    if (editar) {
      evento.preventDefault();
      const linha = movAtiva().linhas.find((l) => l.id === Number(editar.dataset.linhaId));
      if (linha) abrirModalLinha(linha);
      return;
    }
    const botao = evento.target.closest('[data-acao]');
    if (!botao) return;
    const acao = botao.dataset.acao;
    const empresaId = botao.dataset.empresaId ? Number(botao.dataset.empresaId) : null;
    if (acao === 'gerar') gerar(empresaId, false);
    else if (acao === 'gerar-todas') gerar(null, false);
    else if (acao === 'gerar-vazio') gerar(empresaId, true);
    else if (acao === 'salvar-aliquotas') salvarAliquotas();
    else if (acao === 'fechar') atualizarMes({ fechado: true });
    else if (acao === 'reabrir') atualizarMes({ fechado: false });
    else if (acao === 'excluir-mes') excluirMes();
    else if (acao === 'adicionar') abrirModalLinha(null);
    else if (acao === 'numerar') abrirModalNumerar();
  });
  conteudo.addEventListener('change', (evento) => {
    const alvo = evento.target;
    if (alvo.dataset.campo && alvo.closest('tr[data-linha-id]')) {
      salvarCampoInline(alvo);
    } else if (alvo.id === 'mov-filtro-remessa') {
      filtro.remessa = alvo.value;
      renderizarTabela();
    } else if (alvo.id === 'mov-filtro-situacao') {
      filtro.situacao = alvo.value;
      renderizarTabela();
    }
  });
  conteudo.addEventListener('input', (evento) => {
    if (evento.target.id === 'mov-busca') {
      filtro.busca = evento.target.value;
      renderizarTabela();
    }
  });

  document.querySelectorAll('[data-fechar]').forEach((botao) => {
    botao.addEventListener('click', () => fecharModal(botao.dataset.fechar));
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (evento) => {
      if (evento.target === overlay) fecharModal(overlay.id);
    });
  });

  document.getElementById('mov-linha-form').addEventListener('submit', salvarLinha);
  document.getElementById('mov-linha-excluir').addEventListener('click', excluirLinha);
  document.getElementById('mov-linha-cliente').addEventListener('change', preencherDoCadastro);
  document.getElementById('mov-linha-tipo').addEventListener('change', aplicarPadraoTipo);
  document.getElementById('mov-linha-retem-iss').addEventListener('change', atualizarPrevia);
  document.getElementById('mov-linha-retem-inss').addEventListener('change', atualizarPrevia);
  document.getElementById('mov-btn-add-item').addEventListener('click', () => {
    document.getElementById('mov-composicao').insertAdjacentHTML('beforeend', linhaComposicaoHtml({ descricao: '', valor: null, fixo: false }, ''));
  });
  const composicao = document.getElementById('mov-composicao');
  composicao.addEventListener('input', atualizarPrevia);
  composicao.addEventListener('click', (evento) => {
    const remover = evento.target.closest('.mov-item-remover');
    if (!remover) return;
    if (composicao.querySelectorAll('.mov-item-composicao').length > 1) remover.closest('.mov-item-composicao').remove();
    atualizarPrevia();
  });

  document.getElementById('mov-numerar-form').addEventListener('submit', numerarNotas);
  document.getElementById('mov-importar-form').addEventListener('submit', importarPlanilha);

  carregar();
}

if (auth) iniciar();
