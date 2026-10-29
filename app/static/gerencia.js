const auth = Shell.montar('gerencia', 'Gerência');

let dados = null; // resposta de /gerencia-dados/movimentacao do mes aberto
let mesAberto = null; // { ano, mes }
let empresaAtivaId = null;
let filtro = { busca: '', remessa: '', situacao: '' };
let linhaEmEdicao = null; // null = adicionando pelo modal

const SITUACOES = [
  { chave: '', label: 'Todas' },
  { chave: 'sem_valor', label: 'Sem valor da nota' },
  { chave: 'nota', label: 'Nota não gerada' },
  { chave: 'boleto', label: 'Boleto não gerado' },
  { chave: 'envio', label: 'Não enviado ao cliente' },
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
  return valor === null || valor === undefined || valor === 0 ? '' : Number(valor).toFixed(2).replace('.', ',');
}

function nomeMes(mes) {
  return ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'][mes - 1];
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

// mesmas contas do backend (movimentacao.calcular_linha), pra mostrar na hora enquanto digita
function calcular(valorNota, retemIss, retemInss, mov) {
  const nota = Math.round((valorNota || 0) * 100) / 100;
  const iss = retemIss ? Math.round(nota * mov.aliquota_iss) / 100 : 0;
  const inss = retemInss ? Math.round(nota * mov.aliquota_inss) / 100 : 0;
  return { nota, iss, inss, boleto: Math.round((nota - iss - inss) * 100) / 100 };
}

// ---------- passo 1: escolher o mes ----------

function mostrarPassoMes() {
  document.getElementById('mov-area').hidden = true;
  document.getElementById('mov-passo-mes').hidden = false;
  document.getElementById('mov-passo-erro').classList.remove('visible');
  const campo = document.getElementById('mov-mes');
  if (mesAberto) {
    campo.value = `${mesAberto.ano}-${String(mesAberto.mes).padStart(2, '0')}`;
  } else if (!campo.value) {
    const hoje = new Date();
    campo.value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;
  }
  campo.focus();
}

async function abrirMes(ano, mes) {
  const botao = document.getElementById('mov-abrir-mes');
  botao.disabled = true;
  botao.textContent = 'Abrindo...';
  try {
    let resposta = await Shell.chamarApi(`/gerencia-dados/movimentacao?ano=${ano}&mes=${mes}`);
    if (!resposta) return;
    const faltando = resposta.empresas.filter((e) => !e.movimentacao);
    let aviso = '';
    if (faltando.length) {
      // cria o mes de quem ainda nao tem, ja com os clientes preenchidos
      await Shell.chamarApi('/gerencia-dados/movimentacao/gerar', { method: 'POST', body: { ano, mes } });
      resposta = await Shell.chamarApi(`/gerencia-dados/movimentacao?ano=${ano}&mes=${mes}`);
      if (!resposta) return;
      aviso = faltando
        .map((e) => (e.anterior
          ? `${escaparHtml(e.nome)}: clientes copiados de ${nomeMes(e.anterior.mes)}/${e.anterior.ano}`
          : `${escaparHtml(e.nome)}: clientes puxados do cadastro (confira os códigos de serviço)`))
        .join(' · ');
    }
    dados = resposta;
    mesAberto = { ano, mes };
    history.replaceState(null, '', `/gerencia?mes=${ano}-${String(mes).padStart(2, '0')}`);
    if (!dados.empresas.some((e) => e.id === empresaAtivaId)) {
      empresaAtivaId = dados.empresas.length ? dados.empresas[0].id : null;
    }
    document.getElementById('mov-passo-mes').hidden = true;
    document.getElementById('mov-area').hidden = false;
    document.getElementById('mov-titulo-mes').textContent = `${nomeMes(mes)}/${ano}`;
    const caixaAviso = document.getElementById('mov-aviso');
    caixaAviso.innerHTML = aviso ? `Mês criado. ${aviso}. Agora preencha os impostos do mês, os valores e os vencimentos.` : '';
    caixaAviso.hidden = !aviso;
    renderizarAbas();
    renderizarConteudo();
  } catch (erro) {
    mostrarPassoMes();
    if (erro.status === 403) mostrarErro('mov-passo-erro', null, 'Esta área é exclusiva da gerência.');
    else mostrarErro('mov-passo-erro', erro, 'Não foi possível abrir a movimentação deste mês.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Abrir movimentação';
  }
}

async function recarregar() {
  if (!mesAberto) return;
  const resposta = await Shell.chamarApi(`/gerencia-dados/movimentacao?ano=${mesAberto.ano}&mes=${mesAberto.mes}`);
  if (!resposta) return;
  dados = resposta;
  renderizarAbas();
  renderizarConteudo();
}

// ---------- passo 2: movimentacao ----------

function renderizarAbas() {
  document.getElementById('mov-abas').innerHTML = dados.empresas
    .map((e) => {
      const totais = e.movimentacao ? e.movimentacao.totais : null;
      const detalhe = totais ? ` <span class="mov-aba-qtd">${totais.quantidade}</span>` : ' <span class="mov-aba-vazia">· sem lançamento</span>';
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
    conteudo.innerHTML = `
      <div class="dash-card mov-vazio">
        <p><strong>${escaparHtml(empresa.nome)}</strong> não tem movimentação neste mês.</p>
        <div class="mov-botoes"><button class="btn-primary mov-btn-auto" data-acao="gerar" data-empresa-id="${empresa.id}">Criar com os clientes</button></div>
      </div>`;
    return;
  }
  const mov = empresa.movimentacao;
  conteudo.innerHTML = `
    ${htmlImpostos(mov)}
    <div class="kpi-grid" id="mov-kpis"></div>
    <div class="mov-pendencias" id="mov-pendencias"></div>
    ${htmlFiltros(mov)}
    <div class="table-scroll-wrapper" id="mov-tabela"></div>
    ${htmlFechamento(mov)}
  `;
  renderizarResumo();
  renderizarTabela();
}

function htmlImpostos(mov) {
  const bloqueado = mov.fechado ? 'disabled' : '';
  const campo = (id, label, valor, dica) => `
    <div class="field">
      <label for="${id}">${label}</label>
      <div class="mov-campo-pct"><input type="text" inputmode="decimal" id="${id}" class="mov-input-imposto" value="${formatarPercentual(valor)}" ${bloqueado}><span>%</span></div>
      <div class="mov-dica">${dica}</div>
    </div>`;
  const semIss = !mov.aliquota_iss;
  return `
    <div class="mov-impostos${semIss && !mov.fechado ? ' mov-impostos-pendente' : ''}">
      <div class="mov-impostos-topo">
        <div>
          <h3>Impostos do mês · ${escaparHtml(empresaAtiva().nome)}</h3>
          <div class="mov-dica">Valem para todos os clientes desta empresa em ${nomeMes(mov.mes)}/${mov.ano}. Ao salvar, ISS, INSS e boletos são recalculados.</div>
        </div>
        <span class="mov-impostos-estado" id="mov-impostos-estado">${semIss ? 'Preencha o ISS do mês' : 'Salvo'}</span>
      </div>
      <div class="mov-impostos-campos">
        ${campo('mov-aliq-iss', 'ISS', mov.aliquota_iss, 'retido na limpeza')}
        ${campo('mov-aliq-inss', 'INSS (CP)', mov.aliquota_inss, 'retenção previdenciária')}
        ${campo('mov-aliq-simples-limpeza', 'Simples · limpeza', mov.simples_limpeza, 'alíquota informativa')}
        ${campo('mov-aliq-simples-apoio', 'Simples · apoio', mov.simples_apoio, 'alíquota informativa')}
        ${mov.fechado ? '' : '<button class="btn-primary mov-btn-auto" data-acao="salvar-aliquotas" id="mov-salvar-impostos">Salvar impostos</button>'}
      </div>
      <div class="error-message" id="mov-aliquotas-erro"></div>
    </div>
  `;
}

function htmlFechamento(mov) {
  return `
    <div class="mov-fechamento">
      <span class="status-badge ${mov.fechado ? 'mov-status-fechado' : 'mov-status-aberto'}">${mov.fechado ? 'Mês fechado' : 'Mês aberto'}</span>
      <button class="btn-ghost" data-acao="${mov.fechado ? 'reabrir' : 'fechar'}">${mov.fechado ? 'Reabrir mês' : 'Fechar mês (trava edição)'}</button>
      ${mov.fechado ? '' : '<button class="btn-ghost mov-btn-perigo" data-acao="excluir-mes">Excluir mês desta empresa</button>'}
    </div>`;
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
      ${mov.fechado ? '' : '<div class="mov-botoes"><button class="btn-ghost" data-acao="numerar">Numerar notas</button></div>'}
    </div>
  `;
}

function renderizarResumo() {
  const mov = movAtiva();
  if (!mov) return;
  const soma = (chave) => mov.linhas.reduce((s, l) => s + l[chave], 0);
  const linhas = mov.linhas;
  document.getElementById('mov-kpis').innerHTML = `
    <div class="kpi-card"><div><div class="label">valor das notas</div><div class="value">${formatarMoeda(soma('valor_nota'))}</div><div class="sub">${linhas.length} clientes</div></div></div>
    <div class="kpi-card"><div><div class="label">ISS retido</div><div class="value">${formatarMoeda(soma('valor_iss'))}</div><div class="sub">${formatarPercentual(mov.aliquota_iss)}%</div></div></div>
    <div class="kpi-card"><div><div class="label">INSS retido</div><div class="value">${formatarMoeda(soma('valor_inss'))}</div><div class="sub">${formatarPercentual(mov.aliquota_inss)}%</div></div></div>
    <div class="kpi-card"><div><div class="label">total em boletos</div><div class="value">${formatarMoeda(soma('valor_boleto'))}</div></div></div>
  `;
  const pend = [
    [linhas.filter((l) => !l.valor_nota).length, 'sem valor'],
    [linhas.filter((l) => !l.nota_ok).length, 'notas não geradas'],
    [linhas.filter((l) => !l.boleto_ok).length, 'boletos não gerados'],
    [linhas.filter((l) => !l.cliente_ok).length, 'não enviados ao cliente'],
    [linhas.filter((l) => l.exige_documentos && !l.documentos_ok).length, 'documentos pendentes'],
  ];
  const texto = pend.filter(([n]) => n > 0).map(([n, label]) => `<strong>${n}</strong> ${label}`).join(' · ');
  document.getElementById('mov-pendencias').innerHTML = texto ? `Pendências: ${texto}` : '<span class="mov-tudo-ok">Tudo gerado e enviado ✓</span>';
}

function linhaPassaNoFiltro(l) {
  if (filtro.remessa && String(l.remessa) !== filtro.remessa) return false;
  if (filtro.situacao === 'sem_valor' && l.valor_nota) return false;
  if (filtro.situacao === 'nota' && l.nota_ok) return false;
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

function opcoesTipo(selecionado) {
  return dados.tipos_servico
    .map((t) => `<option value="${t.chave}" ${t.chave === selecionado ? 'selected' : ''}>${t.ctn} · ${escaparHtml(t.label.split(' (')[0])}</option>`)
    .join('');
}

function htmlCelulasCalculadas(l) {
  return `
    <td class="mov-num" data-calc="iss">${l.retem_iss ? formatarMoeda(l.valor_iss) : '—'}</td>
    <td class="mov-num" data-calc="inss">${l.retem_inss ? formatarMoeda(l.valor_inss) : '—'}</td>
    <td class="mov-num mov-boleto" data-calc="boleto">${formatarMoeda(l.valor_boleto)}</td>`;
}

function htmlLinha(l, bloqueado) {
  const detalhes = [l.cnpj, l.municipio].filter(Boolean).join(' · ');
  const obs = [l.observacao, l.observacao_mes].filter(Boolean).join(' — ');
  const varios = l.composicao.length > 1;
  const celulaValor = varios
    ? `<button class="btn-ghost mov-btn-mini mov-link-editar mov-valor-composto" data-linha-id="${l.id}" title="${escaparHtml(l.composicao.map((i) => `${i.descricao || 'item'} ${formatarMoeda(i.valor)}`).join(' + '))}">${formatarMoeda(l.valor_nota)} · ${l.composicao.length} itens</button>`
    : `<input type="text" inputmode="decimal" class="mov-inline mov-inline-valor${l.valor_nota ? '' : ' mov-inline-vazio'}" data-campo="valor" value="${valorParaInput(l.valor_nota)}" placeholder="0,00" ${bloqueado} aria-label="Valor da nota">`;
  const check = (campo, marcado, rotulo) => `<td class="mov-centro"><input type="checkbox" data-campo="${campo}" ${marcado ? 'checked' : ''} ${bloqueado} aria-label="${rotulo}"></td>`;
  return `
    <tr data-linha-id="${l.id}" class="${l.valor_nota ? '' : 'mov-linha-sem-valor'}">
      <td>
        <a href="#" class="mov-link-editar mov-nome" data-linha-id="${l.id}">${escaparHtml(l.nome_cliente)}</a>
        ${detalhes ? `<div class="mov-sub">${escaparHtml(detalhes)}</div>` : ''}
        ${obs ? `<div class="mov-obs" title="${escaparHtml(obs)}">${escaparHtml(obs)}</div>` : ''}
      </td>
      <td><select class="mov-inline mov-inline-tipo" data-campo="tipo_servico" ${bloqueado} aria-label="Serviço">${opcoesTipo(l.tipo_servico)}</select></td>
      <td>${celulaValor}</td>
      <td><input type="text" class="mov-inline mov-inline-venc" data-campo="vencimento" value="${escaparHtml(l.vencimento ?? '')}" maxlength="20" placeholder="dia" ${bloqueado} aria-label="Vencimento"></td>
      ${htmlCelulasCalculadas(l)}
      <td><input type="number" class="mov-inline mov-inline-nota" data-campo="numero_nota" value="${l.numero_nota ?? ''}" min="1" ${bloqueado} aria-label="Nº da nota"></td>
      ${check('nota_ok', l.nota_ok, 'Nota gerada')}
      ${check('boleto_ok', l.boleto_ok, 'Boleto gerado')}
      ${check('cliente_ok', l.cliente_ok, 'Enviado ao cliente')}
      <td class="mov-centro">${l.exige_documentos ? `<input type="checkbox" data-campo="documentos_ok" ${l.documentos_ok ? 'checked' : ''} ${bloqueado} aria-label="Documentos enviados">` : '<span class="mov-sub">—</span>'}</td>
      <td><button class="btn-ghost mov-btn-mini mov-link-editar" data-linha-id="${l.id}" title="Mais detalhes">${mesFechado() ? 'Ver' : '⋯'}</button></td>
    </tr>`;
}

function mesFechado() {
  const mov = movAtiva();
  return !!(mov && mov.fechado);
}

function htmlNovaLinha(mov) {
  const remessas = Array.from({ length: dados.maximo_remessa }, (_, i) => i + 1);
  const ultima = mov.linhas.length ? mov.linhas[mov.linhas.length - 1].remessa : 1;
  return `
    <tr class="mov-nova-linha">
      <td>
        <input type="text" class="mov-inline mov-novo-nome" id="mov-novo-nome" list="mov-lista-clientes-rapida" placeholder="+ Novo cliente (digite o nome)" autocomplete="off">
        <datalist id="mov-lista-clientes-rapida">${empresaAtiva().clientes.map((c) => `<option value="${escaparHtml(c.nome)}"></option>`).join('')}</datalist>
      </td>
      <td><select class="mov-inline mov-inline-tipo" id="mov-novo-tipo">${opcoesTipo(dados.tipos_servico[0].chave)}</select></td>
      <td><input type="text" inputmode="decimal" class="mov-inline mov-inline-valor" id="mov-novo-valor" placeholder="0,00"></td>
      <td><input type="text" class="mov-inline mov-inline-venc" id="mov-novo-venc" placeholder="dia" maxlength="20"></td>
      <td colspan="3" class="mov-num mov-sub" id="mov-novo-previa"></td>
      <td><select class="mov-inline" id="mov-novo-remessa" aria-label="Remessa">${remessas.map((r) => `<option value="${r}" ${r === ultima ? 'selected' : ''}>${r}ª rem.</option>`).join('')}</select></td>
      <td colspan="5"><button class="btn-primary mov-btn-auto mov-btn-mini" data-acao="adicionar-rapido">Adicionar</button> <a href="#" data-acao="adicionar">mais campos</a></td>
    </tr>
    <tr class="mov-nova-linha-erro"><td colspan="13"><div class="error-message" id="mov-novo-erro"></div></td></tr>`;
}

function renderizarTabela() {
  const mov = movAtiva();
  const container = document.getElementById('mov-tabela');
  const bloqueado = mov.fechado ? 'disabled' : '';
  const visiveis = mov.linhas.filter(linhaPassaNoFiltro);

  let html = '';
  let remessaAtual = null;
  let subtotal = null;
  const fecharGrupo = () => {
    if (subtotal) {
      html += `<tr class="mov-subtotal"><td colspan="2">Subtotal ${remessaAtual}ª remessa (${subtotal.qtd})</td><td class="mov-num">${formatarMoeda(subtotal.nota)}</td><td></td><td class="mov-num">${formatarMoeda(subtotal.iss)}</td><td class="mov-num">${formatarMoeda(subtotal.inss)}</td><td class="mov-num">${formatarMoeda(subtotal.boleto)}</td><td colspan="6"></td></tr>`;
    }
  };
  visiveis.forEach((l) => {
    if (l.remessa !== remessaAtual) {
      fecharGrupo();
      remessaAtual = l.remessa;
      subtotal = { qtd: 0, nota: 0, iss: 0, inss: 0, boleto: 0 };
      html += `<tr class="mov-grupo"><td colspan="13">${l.remessa}ª remessa</td></tr>`;
    }
    subtotal.qtd += 1;
    subtotal.nota += l.valor_nota;
    subtotal.iss += l.valor_iss;
    subtotal.inss += l.valor_inss;
    subtotal.boleto += l.valor_boleto;
    html += htmlLinha(l, bloqueado);
  });
  fecharGrupo();
  if (!visiveis.length) {
    html = `<tr><td colspan="13" class="empty-state">${mov.linhas.length ? 'Nenhum cliente com esse filtro.' : 'Nenhum cliente neste mês ainda.'}</td></tr>`;
  }

  container.innerHTML = `
    <table class="table-list mov-tabela">
      <thead>
        <tr>
          <th>Cliente</th><th>Serviço (CTN)</th><th class="mov-col-destaque">Valor da nota</th><th class="mov-col-destaque">Venc.</th>
          <th class="mov-num">ISS</th><th class="mov-num">INSS</th><th class="mov-num">Boleto</th>
          <th>Nº NF</th><th class="mov-centro">Nota<br>gerada</th><th class="mov-centro">Boleto<br>gerado</th><th class="mov-centro">Enviado<br>cliente</th><th class="mov-centro">Docs</th><th></th>
        </tr>
      </thead>
      <tbody>${html}</tbody>
      ${mov.fechado ? '' : `<tfoot>${htmlNovaLinha(mov)}</tfoot>`}
    </table>
  `;
}

// ---------- edicao direto na tabela ----------

function atualizarLinhaNaTela(linha) {
  const mov = movAtiva();
  mov.linhas = mov.linhas.map((l) => (l.id === linha.id ? linha : l));
  const tr = document.querySelector(`tr[data-linha-id="${linha.id}"]`);
  if (tr) {
    tr.querySelector('[data-calc="iss"]').textContent = linha.retem_iss ? formatarMoeda(linha.valor_iss) : '—';
    tr.querySelector('[data-calc="inss"]').textContent = linha.retem_inss ? formatarMoeda(linha.valor_inss) : '—';
    tr.querySelector('[data-calc="boleto"]').textContent = formatarMoeda(linha.valor_boleto);
    tr.classList.toggle('mov-linha-sem-valor', !linha.valor_nota);
    const checkNota = tr.querySelector('[data-campo="nota_ok"]');
    if (checkNota) checkNota.checked = linha.nota_ok;
  }
  renderizarResumo();
}

function previaValorDigitado(input) {
  // recalcula ISS/INSS/boleto da linha enquanto digita, antes de salvar
  const tr = input.closest('tr');
  const linha = movAtiva().linhas.find((l) => l.id === Number(tr.dataset.linhaId));
  const valor = lerNumero(input.value);
  if (!linha || Number.isNaN(valor)) return;
  const c = calcular(valor, linha.retem_iss, linha.retem_inss, movAtiva());
  tr.querySelector('[data-calc="iss"]').textContent = linha.retem_iss ? formatarMoeda(c.iss) : '—';
  tr.querySelector('[data-calc="inss"]').textContent = linha.retem_inss ? formatarMoeda(c.inss) : '—';
  tr.querySelector('[data-calc="boleto"]').textContent = formatarMoeda(c.boleto);
}

async function salvarCampoInline(input) {
  const linhaId = Number(input.closest('tr').dataset.linhaId);
  const linha = movAtiva().linhas.find((l) => l.id === linhaId);
  const campo = input.dataset.campo;
  let corpo;
  if (input.type === 'checkbox') {
    corpo = { [campo]: input.checked };
  } else if (campo === 'numero_nota') {
    corpo = { numero_nota: input.value === '' ? null : Number(input.value) };
  } else if (campo === 'valor') {
    const valor = lerNumero(input.value);
    if (Number.isNaN(valor)) {
      input.classList.add('mov-inline-erro');
      return;
    }
    const item = linha.composicao[0] || { descricao: 'Valor mensal', fixo: true };
    corpo = { composicao: [{ descricao: item.descricao || 'Valor mensal', valor: valor || 0, fixo: item.fixo !== false }] };
  } else if (campo === 'tipo_servico') {
    const tipo = dados.tipos_servico.find((t) => t.chave === input.value);
    corpo = { tipo_servico: tipo.chave, retem_iss: tipo.retem_iss, retem_inss: tipo.retem_inss };
  } else {
    corpo = { [campo]: input.value.trim() || null };
  }
  input.classList.remove('mov-inline-erro');
  try {
    const atualizada = await Shell.chamarApi(`/gerencia-dados/movimentacao/linhas/${linhaId}`, { method: 'PATCH', body: corpo });
    if (!atualizada) return;
    atualizarLinhaNaTela(atualizada);
    if (campo === 'valor') {
      input.value = valorParaInput(atualizada.valor_nota);
      input.classList.toggle('mov-inline-vazio', !atualizada.valor_nota);
    }
    input.classList.add('mov-inline-salvo');
    setTimeout(() => input.classList.remove('mov-inline-salvo'), 900);
  } catch (erro) {
    input.classList.add('mov-inline-erro');
    if (input.type === 'checkbox') input.checked = !input.checked;
    alert((erro && erro.detalhe) || 'Não foi possível salvar.');
  }
}

function previaNovaLinha() {
  const valor = lerNumero(document.getElementById('mov-novo-valor').value);
  const tipo = dados.tipos_servico.find((t) => t.chave === document.getElementById('mov-novo-tipo').value);
  const alvo = document.getElementById('mov-novo-previa');
  if (!valor || Number.isNaN(valor)) {
    alvo.textContent = '';
    return;
  }
  const c = calcular(valor, tipo.retem_iss, tipo.retem_inss, movAtiva());
  alvo.textContent = `ISS ${formatarMoeda(c.iss)} · INSS ${formatarMoeda(c.inss)} · boleto ${formatarMoeda(c.boleto)}`;
}

async function adicionarRapido() {
  const mov = movAtiva();
  const nome = document.getElementById('mov-novo-nome').value.trim();
  const valor = lerNumero(document.getElementById('mov-novo-valor').value);
  document.getElementById('mov-novo-erro').classList.remove('visible');
  if (!nome) {
    mostrarErro('mov-novo-erro', null, 'Digite o nome do cliente novo.');
    return;
  }
  if (Number.isNaN(valor)) {
    mostrarErro('mov-novo-erro', null, 'Valor inválido. Use números, ex: 1.885,50');
    return;
  }
  const tipo = dados.tipos_servico.find((t) => t.chave === document.getElementById('mov-novo-tipo').value);
  const cadastro = empresaAtiva().clientes.find((c) => c.nome.toLowerCase() === nome.toLowerCase());
  try {
    const nova = await Shell.chamarApi(`/gerencia-dados/movimentacao/meses/${mov.id}/linhas`, {
      method: 'POST',
      body: {
        cliente_id: cadastro ? cadastro.id : null,
        nome_cliente: nome,
        tipo_servico: tipo.chave,
        retem_iss: tipo.retem_iss,
        retem_inss: tipo.retem_inss,
        remessa: Number(document.getElementById('mov-novo-remessa').value),
        vencimento: document.getElementById('mov-novo-venc').value,
        composicao: [{ descricao: 'Valor mensal', valor: valor || 0, fixo: true }],
      },
    });
    if (!nova) return;
    mov.linhas.push(nova);
    mov.linhas.sort((a, b) => a.remessa - b.remessa || a.ordem - b.ordem || a.id - b.id);
    renderizarAbas();
    renderizarResumo();
    renderizarTabela();
    document.getElementById('mov-novo-nome').focus();
  } catch (erro) {
    mostrarErro('mov-novo-erro', erro, 'Não foi possível adicionar o cliente.');
  }
}

// ---------- acoes do mes ----------

async function gerar(empresaId) {
  try {
    await Shell.chamarApi('/gerencia-dados/movimentacao/gerar', { method: 'POST', body: { ano: mesAberto.ano, mes: mesAberto.mes, empresa_id: empresaId } });
    await recarregar();
  } catch (erro) {
    alert((erro && erro.detalhe) || 'Não foi possível criar o mês.');
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

function marcarImpostosAlterados() {
  const estado = document.getElementById('mov-impostos-estado');
  estado.textContent = 'Alterado · clique em Salvar impostos';
  estado.classList.add('mov-impostos-alterado');
}

async function excluirMes() {
  const empresa = empresaAtiva();
  if (!confirm(`Excluir toda a movimentação de ${empresa.nome} em ${nomeMes(mesAberto.mes)}/${mesAberto.ano}? Isso não pode ser desfeito.`)) return;
  try {
    await Shell.chamarApi(`/gerencia-dados/movimentacao/meses/${empresa.movimentacao.id}`, { method: 'DELETE' });
    await recarregar();
  } catch (erro) {
    alert((erro && erro.detalhe) || 'Não foi possível excluir.');
  }
}

// ---------- modal de cliente (todos os campos) ----------

function abrirModal(id) {
  document.getElementById(id).hidden = false;
}

function fecharModal(id) {
  document.getElementById(id).hidden = true;
}

function linhaComposicaoHtml(item) {
  return `
    <div class="mov-item-composicao">
      <input type="text" class="mov-item-desc" placeholder="Descrição" value="${escaparHtml(item.descricao || '')}" maxlength="100">
      <input type="text" inputmode="decimal" class="mov-item-valor" placeholder="0,00" value="${valorParaInput(item.valor)}">
      <label class="mov-check mov-item-fixo" title="Passa para o mês seguinte"><input type="checkbox" class="mov-item-fixo-check" ${item.fixo ? 'checked' : ''}> todo mês</label>
      <button type="button" class="btn-ghost mov-btn-mini mov-item-remover" aria-label="Remover item">&times;</button>
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
  const itens = lerComposicao().filter((i) => i.valor !== null && !Number.isNaN(i.valor));
  const c = calcular(
    itens.reduce((s, i) => s + i.valor, 0),
    document.getElementById('mov-linha-retem-iss').checked,
    document.getElementById('mov-linha-retem-inss').checked,
    movAtiva(),
  );
  document.getElementById('mov-previa').innerHTML = `
    <span>Nota <strong>${formatarMoeda(c.nota)}</strong></span>
    <span>ISS ${formatarMoeda(c.iss)}</span>
    <span>INSS ${formatarMoeda(c.inss)}</span>
    <span>Boleto <strong>${formatarMoeda(c.boleto)}</strong></span>`;
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
  document.getElementById('mov-composicao').innerHTML = itens.map(linhaComposicaoHtml).join('');

  document.querySelectorAll('#mov-linha-form input, #mov-linha-form select, #mov-linha-form textarea, #mov-linha-form .mov-item-remover').forEach((el) => { el.disabled = mov.fechado; });
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
    await recarregar();
  } catch (erro) {
    mostrarErro('mov-numerar-erro', erro, 'Não foi possível numerar.');
  }
}

// ---------- importar / baixar ----------

function abrirModalImportar() {
  document.getElementById('mov-importar-erro').classList.remove('visible');
  document.getElementById('mov-importar-mes').textContent = `${nomeMes(mesAberto.mes)}/${mesAberto.ano}`;
  document.getElementById('mov-importar-form').reset();
  // o mes ja foi criado ao abrir, entao importar normalmente e substituir
  document.getElementById('mov-importar-substituir').checked = true;
  abrirModal('mov-modal-importar');
}

async function importarPlanilha(evento) {
  evento.preventDefault();
  const arquivo = document.getElementById('mov-importar-arquivo').files[0];
  if (!arquivo) return;
  const formData = new FormData();
  formData.append('ano', mesAberto.ano);
  formData.append('mes', mesAberto.mes);
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
    await recarregar();
  } catch (erro) {
    mostrarErro('mov-importar-erro', erro, 'Não foi possível importar a planilha.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Importar';
  }
}

async function baixar(formato) {
  const { ano, mes } = mesAberto;
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
  document.getElementById('mov-escolher-form').addEventListener('submit', (evento) => {
    evento.preventDefault();
    const [ano, mes] = document.getElementById('mov-mes').value.split('-').map(Number);
    if (ano && mes) abrirMes(ano, mes);
  });
  document.getElementById('mov-trocar-mes').addEventListener('click', mostrarPassoMes);
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
    evento.preventDefault();
    const acao = botao.dataset.acao;
    if (acao === 'gerar') gerar(Number(botao.dataset.empresaId));
    else if (acao === 'salvar-aliquotas') salvarAliquotas();
    else if (acao === 'fechar') atualizarMes({ fechado: true });
    else if (acao === 'reabrir') atualizarMes({ fechado: false });
    else if (acao === 'excluir-mes') excluirMes();
    else if (acao === 'adicionar') abrirModalLinha(null);
    else if (acao === 'adicionar-rapido') adicionarRapido();
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
    } else if (alvo.id === 'mov-novo-tipo') {
      previaNovaLinha();
    }
  });
  conteudo.addEventListener('input', (evento) => {
    const alvo = evento.target;
    if (alvo.id === 'mov-busca') {
      filtro.busca = alvo.value;
      renderizarTabela();
    } else if (alvo.dataset.campo === 'valor') {
      previaValorDigitado(alvo);
    } else if (alvo.id === 'mov-novo-valor') {
      previaNovaLinha();
    } else if (alvo.classList.contains('mov-input-imposto')) {
      marcarImpostosAlterados();
    }
  });
  conteudo.addEventListener('keydown', (evento) => {
    // Enter na linha de cliente novo adiciona; Enter nos impostos salva
    if (evento.key !== 'Enter') return;
    if (evento.target.closest('.mov-nova-linha')) {
      evento.preventDefault();
      adicionarRapido();
    } else if (evento.target.classList.contains('mov-input-imposto')) {
      evento.preventDefault();
      salvarAliquotas();
    } else if (evento.target.classList.contains('mov-inline')) {
      evento.preventDefault();
      evento.target.blur();
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
    document.getElementById('mov-composicao').insertAdjacentHTML('beforeend', linhaComposicaoHtml({ descricao: '', valor: null, fixo: false }));
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

  // ?mes=2026-11 na URL reabre direto o mes (ex: depois de recarregar a pagina)
  const doLink = new URLSearchParams(location.search).get('mes');
  const [ano, mes] = (doLink || '').split('-').map(Number);
  if (ano && mes >= 1 && mes <= 12) abrirMes(ano, mes);
  else mostrarPassoMes();
}

if (auth) iniciar();
