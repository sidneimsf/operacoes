const auth = Shell.montar('visita-comercial', 'Visita Comercial');
const ehEscritorio = !!auth && auth.papel === 'escritorio';

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

function formatarDataBR(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function hojeIso() {
  const agora = new Date();
  agora.setMinutes(agora.getMinutes() - agora.getTimezoneOffset());
  return agora.toISOString().slice(0, 10);
}

let opcoesVisita = { origens: [], status: [], tipos_servico: [] };
let empresasCache = [];
let pessoasCache = [];
let supervisoresCache = [];
let podeConverterCliente = false;
let visitasCompletas = [];

function opcoesHtml(lista, valorVazio) {
  const vazio = valorVazio ? `<option value="">${valorVazio}</option>` : '';
  return vazio + lista.map((item) => `<option value="${item.chave}">${escaparHtml(item.label)}</option>`).join('');
}

// ---------------------------------------------------------------------------
// Resumo (funil) e filtros
// ---------------------------------------------------------------------------

function renderizarResumo() {
  const contar = (...status) => visitasCompletas.filter((v) => status.includes(v.status)).length;
  const emNegociacao = visitasCompletas.filter((v) => ['visitada', 'proposta_enviada'].includes(v.status));
  const valorEmNegociacao = emNegociacao.reduce((soma, v) => soma + (v.valor_estimado || 0), 0);
  const atrasadas = visitasCompletas.filter((v) => v.visita_atrasada).length;

  const card = (label, valor, destaque) => `
    <div class="kpi-card${destaque ? ' destaque' : ''}"><div><div class="label">${label}</div><div class="value">${valor}</div></div></div>
  `;
  document.getElementById('vc-resumo').innerHTML = [
    card(atrasadas ? `solicitadas (${atrasadas} atrasada${atrasadas > 1 ? 's' : ''})` : 'solicitadas', contar('solicitada'), atrasadas > 0),
    card('em negociação', emNegociacao.length),
    card('valor em negociação', formatarMoeda(valorEmNegociacao)),
    card('fechadas', contar('fechada')),
    card('perdidas', contar('perdida')),
  ].join('');
}

function preencherFiltros() {
  document.getElementById('vc-filtro-status').innerHTML = opcoesHtml(opcoesVisita.status, 'Todos');
  document.getElementById('vc-filtro-origem').innerHTML = opcoesHtml(opcoesVisita.origens, 'Todas');
  if (ehEscritorio) {
    document.getElementById('vc-filtro-responsavel').innerHTML =
      '<option value="">Todos</option>' +
      pessoasCache.map((p) => `<option value="${p.id}">${escaparHtml(p.nome)}</option>`).join('');
    document.getElementById('vc-campo-filtro-responsavel').hidden = false;
  }

  ['vc-filtro-busca', 'vc-filtro-status', 'vc-filtro-origem', 'vc-filtro-responsavel'].forEach((id) => {
    document.getElementById(id).addEventListener('input', aplicarFiltros);
  });
}

function aplicarFiltros() {
  const termo = document.getElementById('vc-filtro-busca').value.trim().toLowerCase();
  const statusFiltro = document.getElementById('vc-filtro-status').value;
  const origemFiltro = document.getElementById('vc-filtro-origem').value;
  const responsavelFiltro = document.getElementById('vc-filtro-responsavel').value;

  const filtradas = visitasCompletas.filter((v) => {
    if (statusFiltro && v.status !== statusFiltro) return false;
    if (origemFiltro && v.origem !== origemFiltro) return false;
    if (responsavelFiltro && v.responsavel_id !== Number(responsavelFiltro)) return false;
    if (termo) {
      const alvo = `${v.nome_local} ${v.cidade || ''} ${v.bairro || ''} ${v.contato_nome || ''}`.toLowerCase();
      if (!alvo.includes(termo)) return false;
    }
    return true;
  });
  renderizarVisitas(filtradas);
}

// ---------------------------------------------------------------------------
// Lista
// ---------------------------------------------------------------------------

async function carregarVisitas() {
  const container = document.getElementById('lista-visitas-comerciais');
  try {
    const visitas = await Shell.chamarApi('/visitas-comerciais-dados');
    if (visitas === null) return;
    visitasCompletas = visitas;
    renderizarResumo();
    aplicarFiltros();
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar as visitas agora.</div>';
  }
}

function sinalizacoesHtml(v) {
  const sinais = [];
  if (v.visita_atrasada) sinais.push('<span class="priority-badge urgentissimo">Visita atrasada</span>');
  if (v.retorno_vencido) sinais.push('<span class="priority-badge urgente">Retorno vencido</span>');
  if (v.status === 'solicitada' && v.responsavel_id === auth.id && v.criado_por_id !== auth.id) {
    sinais.push('<span class="priority-badge urgente">Pendente pra você</span>');
  }
  return sinais.length ? `<div class="vc-sinais">${sinais.join('')}</div>` : '';
}

function renderizarVisitas(visitas) {
  const container = document.getElementById('lista-visitas-comerciais');
  if (visitas.length === 0) {
    container.innerHTML = visitasCompletas.length === 0
      ? '<div class="empty-state">Nenhuma visita comercial cadastrada ainda.</div>'
      : '<div class="empty-state">Nenhuma visita encontrada com esses filtros.</div>';
    return;
  }

  const linhas = visitas
    .map((v) => {
      const local = [v.bairro, v.cidade].filter(Boolean).join(' · ');
      const contato = v.contato_nome
        ? `${escaparHtml(v.contato_nome)}${v.contato_cargo ? ` <span class="meta">(${escaparHtml(v.contato_cargo)})</span>` : ''}`
        : '—';
      const telefone = v.contato_telefone
        ? `<div><a href="${Shell.linkWhatsApp(v.contato_telefone)}" target="_blank" rel="noopener">${escaparHtml(v.contato_telefone)}</a></div>`
        : '';
      const datas = v.data_visita
        ? formatarDataBR(v.data_visita)
        : `<span class="meta">prevista ${formatarDataBR(v.data_prevista)}</span>`;
      const podeExcluir = ehEscritorio || v.criado_por_id === auth.id;
      const podeConverter = podeConverterCliente && !v.cliente_id && v.status !== 'perdida';
      return `
      <tr>
        <td>
          <strong>${escaparHtml(v.nome_local)}</strong>
          ${local ? `<div class="meta">${escaparHtml(local)}</div>` : ''}
          ${sinalizacoesHtml(v)}
        </td>
        <td>${escaparHtml(v.origem_label)}</td>
        <td><span class="vc-status ${v.status}">${escaparHtml(v.status_label)}</span></td>
        <td>${datas}</td>
        <td>${contato}${telefone}</td>
        <td>${escaparHtml(v.tipo_servico_label || '—')}${v.qtd_postos ? `<div class="meta">${v.qtd_postos} posto(s)</div>` : ''}</td>
        <td>${v.valor_estimado != null ? formatarMoeda(v.valor_estimado) : '—'}</td>
        <td>${escaparHtml(v.responsavel_nome)}${v.anexos.length ? `<div class="meta">📎 ${v.anexos.length} anexo(s)</div>` : ''}</td>
        <td class="celula-acoes-tabela">
          <button class="btn-ghost btn-editar-vc" data-id="${v.id}">Abrir</button>
          ${v.cliente_id ? `<a class="btn-ghost" href="/cliente-detalhe?id=${v.cliente_id}">Ver cliente</a>` : ''}
          ${podeConverter ? `<button class="btn-ghost btn-converter-vc" data-id="${v.id}" style="color: var(--success);">Converter em cliente</button>` : ''}
          ${podeExcluir ? `<button class="btn-ghost btn-excluir-vc" data-id="${v.id}" style="color: var(--danger);">Excluir</button>` : ''}
        </td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <div class="table-scroll-wrapper"><table class="table-list">
      <thead><tr><th>Local</th><th>Origem</th><th>Status</th><th>Visita</th><th>Contato</th><th>Serviço</th><th>Valor estimado</th><th>Responsável</th><th>Gerenciar</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table></div>
  `;

  const buscar = (id) => visitasCompletas.find((v) => v.id === Number(id));
  container.querySelectorAll('.btn-editar-vc').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalEditarVisita(buscar(botao.dataset.id)));
  });
  container.querySelectorAll('.btn-converter-vc').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalConverter(buscar(botao.dataset.id)));
  });
  container.querySelectorAll('.btn-excluir-vc').forEach((botao) => {
    botao.addEventListener('click', async () => {
      if (!confirm('Excluir essa visita comercial e todos os anexos dela?')) return;
      try {
        await Shell.chamarApi(`/visitas-comerciais-dados/${botao.dataset.id}`, { method: 'DELETE' });
        carregarVisitas();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível excluir agora.');
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Modal de cadastrar / editar visita
// ---------------------------------------------------------------------------

let visitaEmEdicao = null;

function montarModalVisita() {
  const campoResponsavel = ehEscritorio
    ? `
      <div class="field">
        <label for="vc-responsavel">Responsável pela visita</label>
        <select id="vc-responsavel"></select>
      </div>`
    : '';

  const html = `
    <div class="modal-overlay" id="vc-modal-overlay" hidden>
      <div class="modal vc-modal">
        <div class="modal-header">
          <h3 id="vc-modal-titulo">Nova visita comercial</h3>
          <button class="modal-close" id="vc-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="vc-form">
          <div class="vc-secao">Local</div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-origem">Origem</label>
              <select id="vc-origem" required></select>
            </div>
            ${campoResponsavel}
          </div>
          <div class="field">
            <label for="vc-nome-local">Nome do local</label>
            <input type="text" id="vc-nome-local" maxlength="200" required placeholder="Ex: Condomínio Residencial Jardins">
          </div>
          <div class="field">
            <label for="vc-empresa">Empresa do grupo que vai atender</label>
            <select id="vc-empresa"></select>
          </div>
          <div class="field">
            <label for="vc-endereco">Endereço</label>
            <input type="text" id="vc-endereco" maxlength="300">
          </div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-bairro">Bairro</label>
              <input type="text" id="vc-bairro" maxlength="100">
            </div>
            <div class="field">
              <label for="vc-cidade">Cidade</label>
              <input type="text" id="vc-cidade" maxlength="100">
            </div>
          </div>

          <div class="vc-secao">Contato no local</div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-contato-nome">Nome</label>
              <input type="text" id="vc-contato-nome" maxlength="150">
            </div>
            <div class="field">
              <label for="vc-contato-cargo">Cargo</label>
              <input type="text" id="vc-contato-cargo" maxlength="100" placeholder="Ex: Síndico, Gerente predial">
            </div>
            <div class="field">
              <label for="vc-contato-telefone">Telefone</label>
              <input type="tel" id="vc-contato-telefone" maxlength="50">
            </div>
            <div class="field">
              <label for="vc-contato-email">E-mail</label>
              <input type="email" id="vc-contato-email" maxlength="150">
            </div>
          </div>

          <div class="vc-secao">Visita</div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-data-prevista">Data prevista</label>
              <input type="date" id="vc-data-prevista">
            </div>
            <div class="field">
              <label for="vc-data-visita">Data em que foi visitado</label>
              <input type="date" id="vc-data-visita">
            </div>
          </div>

          <div class="vc-secao">Serviço</div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-tipo-servico">Tipo de serviço</label>
              <select id="vc-tipo-servico"></select>
            </div>
            <div class="field">
              <label for="vc-qtd-postos">Qtd. de postos / colaboradores</label>
              <input type="number" id="vc-qtd-postos" min="0" step="1">
            </div>
            <div class="field">
              <label for="vc-horarios">Horários</label>
              <input type="text" id="vc-horarios" maxlength="300" placeholder="Ex: seg a sex, 7h às 16h">
            </div>
            <div class="field">
              <label for="vc-valor">Valor estimado / orçado (R$ por mês)</label>
              <input type="number" id="vc-valor" min="0" step="0.01">
            </div>
          </div>
          <div class="field">
            <label for="vc-observacoes">Observações do local</label>
            <textarea id="vc-observacoes" rows="4" maxlength="2000" placeholder="O que foi visto e conversado, necessidades do cliente, concorrente atual..."></textarea>
          </div>

          <div class="vc-secao">Andamento</div>
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-status">Status</label>
              <select id="vc-status"></select>
            </div>
            <div class="field">
              <label for="vc-data-retorno">Data de retorno</label>
              <input type="date" id="vc-data-retorno">
            </div>
          </div>
          <div class="field">
            <label for="vc-proximo-passo">Próximo passo</label>
            <input type="text" id="vc-proximo-passo" maxlength="500" placeholder="Ex: Enviar proposta, ligar pro síndico após a assembleia...">
          </div>
          <div class="field" id="vc-campo-motivo-perda" hidden>
            <label for="vc-motivo-perda">Motivo da perda</label>
            <textarea id="vc-motivo-perda" rows="2" maxlength="500" placeholder="Ex: Preço, ficou com o concorrente, desistiu da terceirização..."></textarea>
          </div>

          <div class="vc-secao">Fotos e documentos</div>
          <div class="field" id="vc-campo-anexos-existentes" hidden>
            <div id="vc-lista-anexos"></div>
          </div>
          <div class="field">
            <label for="vc-arquivos">Adicionar fotos ou PDFs (até 10MB cada)</label>
            <input type="file" id="vc-arquivos" accept="image/jpeg,image/png,application/pdf" multiple>
          </div>

          <div class="error-message" id="vc-modal-erro"></div>
          <button type="submit" class="btn-primary" id="vc-modal-enviar">Salvar visita</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('vc-origem').innerHTML = opcoesHtml(opcoesVisita.origens);
  document.getElementById('vc-empresa').innerHTML =
    '<option value="">Ainda não definida</option>' +
    empresasCache.map((e) => `<option value="${e.id}">${escaparHtml(e.nome)}</option>`).join('');
  document.getElementById('vc-tipo-servico').innerHTML = opcoesHtml(opcoesVisita.tipos_servico, 'Não informado');
  if (ehEscritorio) {
    document.getElementById('vc-responsavel').innerHTML = pessoasCache
      .map((p) => `<option value="${p.id}">${escaparHtml(p.nome)}${p.papel === 'supervisor' ? '' : ' (escritório)'}</option>`)
      .join('');
  }

  document.getElementById('vc-modal-fechar').addEventListener('click', fecharModalVisita);
  document.getElementById('vc-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'vc-modal-overlay') fecharModalVisita();
  });
  document.getElementById('vc-status').addEventListener('change', atualizarCampoMotivoPerda);
  document.getElementById('vc-data-visita').addEventListener('change', sincronizarStatusComDataVisita);
  document.getElementById('vc-form').addEventListener('submit', salvarVisita);

  document.getElementById('vc-lista-anexos').addEventListener('click', async (evento) => {
    const link = evento.target.closest('.vc-link-anexo');
    if (link) {
      evento.preventDefault();
      verAnexo(link.dataset.anexoId);
      return;
    }
    const botaoRemover = evento.target.closest('.vc-remover-anexo');
    if (botaoRemover) {
      if (!confirm('Excluir esse anexo?')) return;
      try {
        await Shell.chamarApi(`/visitas-comerciais-dados/anexos/${botaoRemover.dataset.anexoId}`, { method: 'DELETE' });
        const atualizada = await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmEdicao.id}`);
        visitaEmEdicao = atualizada;
        renderizarAnexos(atualizada.anexos);
        carregarVisitas();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível excluir o anexo agora.');
      }
    }
  });
}

function preencherSelectStatus(statusAtual) {
  // "fechada" so acontece pelo botao "Converter em cliente"
  const lista = opcoesVisita.status.filter((s) => s.chave !== 'fechada' || statusAtual === 'fechada');
  const select = document.getElementById('vc-status');
  select.innerHTML = opcoesHtml(lista);
  select.value = statusAtual;
  select.disabled = statusAtual === 'fechada';
  atualizarCampoMotivoPerda();
}

function atualizarCampoMotivoPerda() {
  const perdida = document.getElementById('vc-status').value === 'perdida';
  document.getElementById('vc-campo-motivo-perda').hidden = !perdida;
  document.getElementById('vc-motivo-perda').required = perdida;
}

function sincronizarStatusComDataVisita() {
  const select = document.getElementById('vc-status');
  const temData = !!document.getElementById('vc-data-visita').value;
  if (temData && select.value === 'solicitada') select.value = 'visitada';
  if (!temData && select.value === 'visitada') select.value = 'solicitada';
  atualizarCampoMotivoPerda();
}

function renderizarAnexos(anexos) {
  const container = document.getElementById('vc-lista-anexos');
  document.getElementById('vc-campo-anexos-existentes').hidden = false;
  if (anexos.length === 0) {
    container.innerHTML = '<div class="meta">Nenhum anexo ainda.</div>';
    return;
  }
  container.innerHTML = anexos
    .map(
      (a) => `
      <div class="vc-anexo">
        <a href="#" class="vc-link-anexo" data-anexo-id="${a.id}">📎 ${escaparHtml(a.nome_original)}</a>
        <span class="meta">${escaparHtml(a.enviado_por_nome)} · ${formatarDataBR(a.criado_em)}</span>
        <button type="button" class="btn-ghost vc-remover-anexo" data-anexo-id="${a.id}">Excluir</button>
      </div>
    `
    )
    .join('');
}

function abrirModalNovaVisita() {
  visitaEmEdicao = null;
  document.getElementById('vc-modal-titulo').textContent = ehEscritorio ? 'Nova visita / solicitação' : 'Nova visita comercial';
  document.getElementById('vc-form').reset();
  document.getElementById('vc-modal-erro').classList.remove('visible');
  document.getElementById('vc-campo-anexos-existentes').hidden = true;

  // escritorio normalmente solicita a visita de um orcamento aprovado;
  // supervisor normalmente registra uma prospeccao que acabou de fazer
  if (ehEscritorio) {
    document.getElementById('vc-origem').value = 'orcamento_aprovado';
    document.getElementById('vc-responsavel').value = auth.id;
    preencherSelectStatus('solicitada');
  } else {
    document.getElementById('vc-origem').value = 'prospeccao';
    document.getElementById('vc-data-visita').value = hojeIso();
    preencherSelectStatus('visitada');
  }

  document.getElementById('vc-modal-overlay').hidden = false;
}

function abrirModalEditarVisita(visita) {
  if (!visita) return;
  visitaEmEdicao = visita;
  document.getElementById('vc-modal-titulo').textContent = visita.nome_local;
  document.getElementById('vc-form').reset();
  document.getElementById('vc-modal-erro').classList.remove('visible');

  const valores = {
    'vc-origem': visita.origem,
    'vc-nome-local': visita.nome_local,
    'vc-empresa': visita.empresa_id ?? '',
    'vc-endereco': visita.endereco,
    'vc-bairro': visita.bairro,
    'vc-cidade': visita.cidade,
    'vc-contato-nome': visita.contato_nome,
    'vc-contato-cargo': visita.contato_cargo,
    'vc-contato-telefone': visita.contato_telefone,
    'vc-contato-email': visita.contato_email,
    'vc-data-prevista': visita.data_prevista,
    'vc-data-visita': visita.data_visita,
    'vc-tipo-servico': visita.tipo_servico ?? '',
    'vc-qtd-postos': visita.qtd_postos,
    'vc-horarios': visita.horarios,
    'vc-valor': visita.valor_estimado,
    'vc-observacoes': visita.observacoes,
    'vc-proximo-passo': visita.proximo_passo,
    'vc-data-retorno': visita.data_retorno,
    'vc-motivo-perda': visita.motivo_perda,
  };
  Object.entries(valores).forEach(([id, valor]) => {
    document.getElementById(id).value = valor ?? '';
  });
  if (ehEscritorio) document.getElementById('vc-responsavel').value = visita.responsavel_id;
  preencherSelectStatus(visita.status);
  renderizarAnexos(visita.anexos);

  document.getElementById('vc-modal-overlay').hidden = false;
}

function fecharModalVisita() {
  document.getElementById('vc-modal-overlay').hidden = true;
}

function textoOuNulo(id) {
  return document.getElementById(id).value.trim() || null;
}

function numeroOuNulo(id) {
  const valor = document.getElementById(id).value;
  return valor === '' ? null : Number(valor);
}

async function enviarArquivos(visitaId, arquivos) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return null;
  const formData = new FormData();
  Array.from(arquivos).forEach((arquivo) => formData.append('arquivos', arquivo));

  const resposta = await fetch(`/visitas-comerciais-dados/${visitaId}/anexos`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    body: formData,
  });
  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error('Falha ao enviar anexos');
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }
  return resposta.json();
}

async function salvarVisita(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('vc-modal-erro');
  const botao = document.getElementById('vc-modal-enviar');
  erroBox.classList.remove('visible');

  const statusSelect = document.getElementById('vc-status');
  const corpo = {
    origem: document.getElementById('vc-origem').value,
    nome_local: document.getElementById('vc-nome-local').value.trim(),
    empresa_id: numeroOuNulo('vc-empresa'),
    endereco: textoOuNulo('vc-endereco'),
    bairro: textoOuNulo('vc-bairro'),
    cidade: textoOuNulo('vc-cidade'),
    contato_nome: textoOuNulo('vc-contato-nome'),
    contato_cargo: textoOuNulo('vc-contato-cargo'),
    contato_telefone: textoOuNulo('vc-contato-telefone'),
    contato_email: textoOuNulo('vc-contato-email'),
    data_prevista: textoOuNulo('vc-data-prevista'),
    data_visita: textoOuNulo('vc-data-visita'),
    tipo_servico: textoOuNulo('vc-tipo-servico'),
    qtd_postos: numeroOuNulo('vc-qtd-postos'),
    horarios: textoOuNulo('vc-horarios'),
    valor_estimado: numeroOuNulo('vc-valor'),
    observacoes: textoOuNulo('vc-observacoes'),
    proximo_passo: textoOuNulo('vc-proximo-passo'),
    data_retorno: textoOuNulo('vc-data-retorno'),
    motivo_perda: textoOuNulo('vc-motivo-perda'),
  };
  if (!statusSelect.disabled) corpo.status = statusSelect.value;
  const responsavelEscolhido = ehEscritorio ? document.getElementById('vc-responsavel').value : '';
  if (responsavelEscolhido) corpo.responsavel_id = Number(responsavelEscolhido);

  const arquivos = document.getElementById('vc-arquivos').files;

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  let salva = null;
  try {
    salva = visitaEmEdicao
      ? await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmEdicao.id}`, { method: 'PATCH', body: corpo })
      : await Shell.chamarApi('/visitas-comerciais-dados', { method: 'POST', body: corpo });
    if (salva === null) return;
    if (arquivos.length > 0) await enviarArquivos(salva.id, arquivos);
    fecharModalVisita();
    carregarVisitas();
  } catch (erro) {
    if (salva) {
      // a visita foi salva, so os anexos falharam - deixa o modal aberto ja em modo edicao
      abrirModalEditarVisita(salva);
      carregarVisitas();
      erroBox.textContent = `Visita salva, mas os anexos não foram enviados: ${erro.detalhe || 'tente de novo.'}`;
    } else {
      erroBox.textContent = erro.detalhe || 'Não foi possível salvar a visita agora.';
    }
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar visita';
  }
}

async function verAnexo(anexoId) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return;
  try {
    const resposta = await fetch(`/visitas-comerciais-dados/anexos/${anexoId}`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) throw new Error('Falha ao baixar');
    const blob = await resposta.blob();
    window.open(URL.createObjectURL(blob), '_blank');
  } catch (erro) {
    alert('Não foi possível abrir esse anexo agora.');
  }
}

// ---------------------------------------------------------------------------
// Converter em cliente
// ---------------------------------------------------------------------------

let visitaEmConversao = null;

function montarModalConverter() {
  const html = `
    <div class="modal-overlay" id="vc-converter-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Converter em cliente</h3>
          <button class="modal-close" id="vc-converter-fechar" aria-label="Fechar">&times;</button>
        </div>
        <p class="meta" style="margin-top: 0;">Cria o cliente com o endereço e o contato levantados na visita, e marca a visita como fechada.</p>
        <form id="vc-converter-form">
          <div class="field">
            <label for="vc-converter-nome">Nome do cliente</label>
            <input type="text" id="vc-converter-nome" maxlength="200" required>
          </div>
          <div class="field">
            <label for="vc-converter-empresa">Empresa</label>
            <select id="vc-converter-empresa" required></select>
          </div>
          <div class="field">
            <label for="vc-converter-supervisor">Supervisor do cliente</label>
            <select id="vc-converter-supervisor"></select>
          </div>
          <div class="error-message" id="vc-converter-erro"></div>
          <button type="submit" class="btn-primary" id="vc-converter-enviar">Criar cliente</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('vc-converter-empresa').innerHTML =
    '<option value="">Escolha a empresa</option>' +
    empresasCache.map((e) => `<option value="${e.id}">${escaparHtml(e.nome)}</option>`).join('');

  const fechar = () => { document.getElementById('vc-converter-overlay').hidden = true; };
  document.getElementById('vc-converter-fechar').addEventListener('click', fechar);
  document.getElementById('vc-converter-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'vc-converter-overlay') fechar();
  });

  document.getElementById('vc-converter-form').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const erroBox = document.getElementById('vc-converter-erro');
    const botao = document.getElementById('vc-converter-enviar');
    erroBox.classList.remove('visible');
    const supervisorId = document.getElementById('vc-converter-supervisor').value;
    botao.disabled = true;
    botao.textContent = 'Criando...';
    try {
      const visita = await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmConversao.id}/converter-cliente`, {
        method: 'POST',
        body: {
          nome: document.getElementById('vc-converter-nome').value.trim(),
          empresa_id: Number(document.getElementById('vc-converter-empresa').value),
          supervisor_id: supervisorId ? Number(supervisorId) : null,
        },
      });
      if (visita === null) return;
      fechar();
      carregarVisitas();
      if (confirm(`Cliente "${visita.cliente_nome}" criado. Abrir a ficha do cliente agora?`)) {
        window.location.href = `/cliente-detalhe?id=${visita.cliente_id}`;
      }
    } catch (erro) {
      erroBox.textContent = erro.detalhe || 'Não foi possível criar o cliente agora.';
      erroBox.classList.add('visible');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Criar cliente';
    }
  });
}

async function abrirModalConverter(visita) {
  if (!visita) return;
  visitaEmConversao = visita;
  document.getElementById('vc-converter-erro').classList.remove('visible');

  if (supervisoresCache.length === 0) {
    try {
      supervisoresCache = (await Shell.chamarApi('/supervisores')) || [];
    } catch (erro) {
      supervisoresCache = [];
    }
  }
  const selectSupervisor = document.getElementById('vc-converter-supervisor');
  selectSupervisor.innerHTML =
    '<option value="">Sem supervisor</option>' +
    supervisoresCache.map((s) => `<option value="${s.id}">${escaparHtml(s.nome)}</option>`).join('');
  selectSupervisor.value = supervisoresCache.some((s) => s.id === visita.responsavel_id) ? visita.responsavel_id : '';

  document.getElementById('vc-converter-nome').value = visita.nome_local;
  document.getElementById('vc-converter-empresa').value = visita.empresa_id ?? '';
  document.getElementById('vc-converter-overlay').hidden = false;
}

// ---------------------------------------------------------------------------
// Inicializacao
// ---------------------------------------------------------------------------

async function iniciar() {
  if (!auth) return;
  const container = document.getElementById('lista-visitas-comerciais');
  try {
    const [opcoes, empresas, permissoes, pessoas] = await Promise.all([
      Shell.chamarApi('/visitas-comerciais-opcoes'),
      Shell.chamarApi('/empresas'),
      Shell.chamarApi('/minhas-permissoes'),
      ehEscritorio ? Shell.chamarApi('/pessoas') : Promise.resolve([]),
    ]);
    if (opcoes === null) return;
    opcoesVisita = opcoes;
    empresasCache = empresas || [];
    podeConverterCliente = !!(permissoes && permissoes.criar_cliente);
    pessoasCache = pessoas || [];
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar a tela agora.</div>';
    return;
  }

  preencherFiltros();
  montarModalVisita();
  montarModalConverter();
  document.getElementById('btn-nova-visita-comercial').addEventListener('click', abrirModalNovaVisita);
  carregarVisitas();
}

iniciar();
