const auth = Shell.montar('ocorrencias', 'Ocorrências');

let TIPOS = [];
let STATUS = [];
let PRIORIDADES = [];
let empresas = [];

const filtros = {
  status: null,
  tipo: '',
  prioridade: '',
  empresa_id: '',
  cliente_id: '',
  responsavel_id: '',
  data_inicio: '',
  data_fim: '',
};

function montarQueryString() {
  const params = new URLSearchParams();
  if (filtros.status) params.set('status_filtro', filtros.status);
  if (filtros.tipo) params.set('tipo', filtros.tipo);
  if (filtros.prioridade) params.set('prioridade', filtros.prioridade);
  if (filtros.empresa_id) params.set('empresa_id', filtros.empresa_id);
  if (filtros.cliente_id) params.set('cliente_id', filtros.cliente_id);
  if (filtros.responsavel_id) params.set('responsavel_id', filtros.responsavel_id);
  if (filtros.data_inicio) params.set('data_inicio', filtros.data_inicio);
  if (filtros.data_fim) params.set('data_fim', filtros.data_fim);
  return params.toString();
}

function renderizarChipsStatus() {
  const container = document.getElementById('chips-status');
  container.innerHTML = '';

  const opcoes = [{ chave: null, label: 'Todos' }, ...STATUS];

  opcoes.forEach((opcao) => {
    const chip = document.createElement('button');
    chip.className = 'chip' + (filtros.status === opcao.chave ? ' active' : '');
    chip.textContent = opcao.label;
    chip.addEventListener('click', () => {
      filtros.status = opcao.chave;
      renderizarChipsStatus();
      carregarChamados();
    });
    container.appendChild(chip);
  });
}

async function popularClientesDaEmpresa(empresaId) {
  const selectCliente = document.getElementById('filtro-cliente');
  if (!empresaId) {
    selectCliente.innerHTML = '<option value="">Todos</option>';
    return;
  }
  const clientes = await Shell.chamarApi(`/clientes-dados?empresa_id=${empresaId}`);
  selectCliente.innerHTML =
    '<option value="">Todos</option>' +
    clientes.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
}

const LIMITE_DESCRICAO_CURTA = 70;

function celulaDescricaoHtml(chamadoId, descricao) {
  const textoSeguro = (descricao || '').replace(/"/g, '&quot;');
  if (descricao.length <= LIMITE_DESCRICAO_CURTA) {
    return `<span>${descricao}</span>`;
  }
  const resumo = descricao.slice(0, LIMITE_DESCRICAO_CURTA).trim() + '…';
  return `
    <span class="descricao-texto" data-completo="${textoSeguro}" data-resumo="${resumo.replace(/"/g, '&quot;')}" data-expandido="false">${resumo}</span>
    <button type="button" class="btn-ver-mais-descricao" data-id="${chamadoId}">Ver mais</button>
  `;
}

function formatarData(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatarDataHora(isoString) {
  const data = new Date(isoString);
  const dataFormatada = data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  const horaFormatada = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${dataFormatada} ${horaFormatada}`;
}

function labelTipo(chave) {
  const encontrado = TIPOS.find((t) => t.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function labelPrioridade(chave) {
  const encontrado = PRIORIDADES.find((p) => p.chave === chave);
  return encontrado ? encontrado.label : chave;
}

async function trocarStatus(chamadoId, novoStatus) {
  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoId}`, {
      method: 'PATCH',
      body: { status: novoStatus },
    });
    carregarChamados();
  } catch (erro) {
    alert('Não foi possível atualizar o status agora.');
  }
}

function montarModalFinalizar() {
  const html = `
    <div class="modal-overlay" id="finalizar-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Finalizar chamado</h3>
          <button class="modal-close" id="finalizar-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="finalizar-form">
          <div class="field">
            <label for="finalizar-pendencia">Ficou alguma pendência?</label>
            <select id="finalizar-pendencia">
              <option value="nao">Não</option>
              <option value="sim">Sim</option>
            </select>
          </div>
          <div class="field" id="campo-pendencia-detalhe" hidden>
            <label for="finalizar-pendencia-detalhe">Qual pendência?</label>
            <textarea id="finalizar-pendencia-detalhe" rows="2"></textarea>
          </div>

          <div class="field">
            <label for="finalizar-documento">Foi necessário enviar algum documento?</label>
            <select id="finalizar-documento">
              <option value="nao">Não</option>
              <option value="sim">Sim</option>
            </select>
          </div>
          <div class="field" id="campo-documento-detalhe" hidden>
            <label for="finalizar-documento-detalhe">Qual documento?</label>
            <textarea id="finalizar-documento-detalhe" rows="2"></textarea>
          </div>

          <div class="field">
            <label for="finalizar-observacoes">Observações (opcional)</label>
            <textarea id="finalizar-observacoes" rows="2"></textarea>
          </div>

          <div class="error-message" id="finalizar-modal-erro"></div>
          <button type="submit" class="btn-primary" id="finalizar-modal-enviar">Finalizar chamado</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('finalizar-modal-fechar').addEventListener('click', () => fecharModalFinalizar(true));
  document.getElementById('finalizar-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'finalizar-modal-overlay') fecharModalFinalizar(true);
  });

  document.getElementById('finalizar-pendencia').addEventListener('change', (evento) => {
    document.getElementById('campo-pendencia-detalhe').hidden = evento.target.value !== 'sim';
  });
  document.getElementById('finalizar-documento').addEventListener('change', (evento) => {
    document.getElementById('campo-documento-detalhe').hidden = evento.target.value !== 'sim';
  });

  document.getElementById('finalizar-form').addEventListener('submit', enviarFinalizacao);
}

let chamadoEmFinalizacao = null;
let selectEmFinalizacao = null;

function abrirModalFinalizar(chamadoId, selectEl) {
  chamadoEmFinalizacao = chamadoId;
  selectEmFinalizacao = selectEl;

  document.getElementById('finalizar-form').reset();
  document.getElementById('campo-pendencia-detalhe').hidden = true;
  document.getElementById('campo-documento-detalhe').hidden = true;
  document.getElementById('finalizar-modal-erro').classList.remove('visible');
  document.getElementById('finalizar-modal-overlay').hidden = false;
}

function fecharModalFinalizar(cancelou) {
  document.getElementById('finalizar-modal-overlay').hidden = true;
  if (cancelou && selectEmFinalizacao) {
    selectEmFinalizacao.value = selectEmFinalizacao.dataset.statusAnterior;
  }
  chamadoEmFinalizacao = null;
  selectEmFinalizacao = null;
}

async function enviarFinalizacao(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('finalizar-modal-erro');
  const botao = document.getElementById('finalizar-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    pendencia: document.getElementById('finalizar-pendencia').value === 'sim',
    pendencia_detalhe: document.getElementById('finalizar-pendencia-detalhe').value,
    documento_enviado: document.getElementById('finalizar-documento').value === 'sim',
    documento_detalhe: document.getElementById('finalizar-documento-detalhe').value,
    observacoes: document.getElementById('finalizar-observacoes').value,
  };

  botao.disabled = true;
  botao.textContent = 'Finalizando...';

  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoEmFinalizacao}/finalizar`, {
      method: 'POST',
      body: corpo,
    });
    document.getElementById('finalizar-modal-overlay').hidden = true;
    chamadoEmFinalizacao = null;
    selectEmFinalizacao = null;
    carregarChamados();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível finalizar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Finalizar chamado';
  }
}

function renderizarTabela(chamados) {
  const container = document.getElementById('lista-chamados');

  if (chamados.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum chamado encontrado com esses filtros.</div>';
    return;
  }

  const opcoesStatusHtml = (statusAtual) =>
    STATUS.map((s) => `<option value="${s.chave}" ${s.chave === statusAtual ? 'selected' : ''}>${s.label}</option>`).join('');

  const linhas = chamados
    .map(
      (c) => `
      <tr>
        <td>${formatarData(c.criado_em)}</td>
        <td>
          <a href="/cliente-detalhe?id=${c.cliente_id}">${c.cliente_nome}</a>
          ${c.colaborador_nome ? `<div class="meta" style="font-size: 11px;">→ ${c.colaborador_nome}</div>` : ''}
        </td>
        <td>${labelTipo(c.tipo)}</td>
        <td><span class="priority-badge ${c.prioridade}">${labelPrioridade(c.prioridade)}</span></td>
        <td class="chamado-descricao">${celulaDescricaoHtml(c.id, c.descricao)}</td>
        <td>${c.responsavel_nome || '—'}</td>
        <td>
          <select class="status-select status-select-${c.status}" data-id="${c.id}" data-status-anterior="${c.status}" ${c.status === 'finalizado' ? 'disabled' : ''}>
            ${opcoesStatusHtml(c.status)}
          </select>
          ${c.status === 'finalizado' && c.finalizado_em ? `<div class="meta" style="margin-top: 4px; font-size: 11px;">finalizado em ${formatarDataHora(c.finalizado_em)}</div>` : ''}
        </td>
        <td>
          <div class="grupo-acoes-tabela">
            <button class="btn-ghost btn-acao-corretiva" data-id="${c.id}" data-acao="${(c.acao_corretiva || '').replace(/"/g, '&quot;')}">
              ${c.acao_corretiva ? '✓ Ver ação' : '+ Ação corretiva'}
            </button>
            ${auth.id === c.aberto_por_id ? `<button class="btn-ghost btn-editar-chamado" data-id="${c.id}">Editar</button>` : ''}
            ${auth.papel === 'escritorio' ? `<button class="btn-ghost btn-excluir-chamado" data-id="${c.id}" style="color: var(--danger);">Excluir</button>` : ''}
          </div>
        </td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Data</th><th>Cliente</th><th>Tipo</th><th>Prioridade</th><th>Descrição</th><th>Responsável</th><th>Status</th><th>Ações</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;

  container.querySelectorAll('.btn-acao-corretiva').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalAcaoCorretiva(botao.dataset.id, botao.dataset.acao));
  });

  container.querySelectorAll('.btn-ver-mais-descricao').forEach((botao) => {
    botao.addEventListener('click', (evento) => {
      evento.stopPropagation();
      const spanTexto = botao.previousElementSibling;
      const expandido = spanTexto.dataset.expandido === 'true';
      if (expandido) {
        spanTexto.textContent = spanTexto.dataset.resumo;
        spanTexto.dataset.expandido = 'false';
        botao.textContent = 'Ver mais';
      } else {
        // colapsa qualquer outra descricao que esteja expandida antes de abrir essa
        document.querySelectorAll('.descricao-texto[data-expandido="true"]').forEach((outroSpan) => {
          outroSpan.textContent = outroSpan.dataset.resumo;
          outroSpan.dataset.expandido = 'false';
          const outroBotao = outroSpan.nextElementSibling;
          if (outroBotao) outroBotao.textContent = 'Ver mais';
        });
        spanTexto.textContent = spanTexto.dataset.completo;
        spanTexto.dataset.expandido = 'true';
        botao.textContent = 'Ver menos';
      }
    });
  });

  container.querySelectorAll('.btn-editar-chamado').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalEditarChamado(botao.dataset.id));
  });

  container.querySelectorAll('.btn-excluir-chamado').forEach((botao) => {
    botao.addEventListener('click', () => excluirChamado(botao.dataset.id));
  });

  container.querySelectorAll('.status-select').forEach((select) => {
    select.addEventListener('change', (evento) => {
      const novoStatus = evento.target.value;
      if (novoStatus === 'finalizado') {
        abrirModalFinalizar(evento.target.dataset.id, evento.target);
      } else {
        trocarStatus(evento.target.dataset.id, novoStatus);
      }
    });
  });
}

let chamadosAtuais = [];

async function carregarChamados() {
  const container = document.getElementById('lista-chamados');
  container.innerHTML = '<div class="loading-state">Carregando chamados...</div>';
  try {
    const chamados = await Shell.chamarApi(`/chamados-dados?${montarQueryString()}`);
    if (chamados === null) return;
    chamadosAtuais = chamados;
    renderizarTabela(chamados);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os chamados agora.</div>';
  }
}

async function iniciar() {
  montarModalFinalizar();

  const parametrosUrl = new URLSearchParams(window.location.search);
  if (parametrosUrl.get('responsavel_id')) {
    filtros.responsavel_id = parametrosUrl.get('responsavel_id');
  }

  const tiposEStatus = await Shell.chamarApi('/chamados-tipos');
  if (tiposEStatus === null) return;
  TIPOS = tiposEStatus.tipos;
  STATUS = tiposEStatus.status;
  PRIORIDADES = tiposEStatus.prioridades;

  document.getElementById('filtro-tipo').innerHTML =
    '<option value="">Todos</option>' + TIPOS.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');

  document.getElementById('filtro-prioridade').innerHTML =
    '<option value="">Todas</option>' + PRIORIDADES.map((p) => `<option value="${p.chave}">${p.label}</option>`).join('');

  empresas = await Shell.chamarApi('/empresas');
  if (empresas === null) return;
  document.getElementById('filtro-empresa').innerHTML =
    '<option value="">Todas</option>' + empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

  const supervisores = await Shell.chamarApi('/supervisores');
  if (supervisores === null) return;
  const selectResponsavel = document.getElementById('filtro-responsavel');
  selectResponsavel.innerHTML =
    '<option value="">Todos</option>' + supervisores.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');
  selectResponsavel.value = filtros.responsavel_id;

  renderizarChipsStatus();

  document.getElementById('filtro-empresa').addEventListener('change', async (evento) => {
    filtros.empresa_id = evento.target.value;
    filtros.cliente_id = '';
    await popularClientesDaEmpresa(evento.target.value);
    carregarChamados();
  });

  document.getElementById('filtro-cliente').addEventListener('change', (evento) => {
    filtros.cliente_id = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-tipo').addEventListener('change', (evento) => {
    filtros.tipo = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-prioridade').addEventListener('change', (evento) => {
    filtros.prioridade = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-responsavel').addEventListener('change', (evento) => {
    filtros.responsavel_id = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-data-inicio').addEventListener('change', (evento) => {
    filtros.data_inicio = evento.target.value;
    carregarChamados();
  });

  document.getElementById('filtro-data-fim').addEventListener('change', (evento) => {
    filtros.data_fim = evento.target.value;
    carregarChamados();
  });

  carregarChamados();
}

let clientesEditarChamadoCache = [];
let colaboradoresEditarChamadoCache = [];

function montarModalEditarChamado() {
  const html = `
    <div class="modal-overlay" id="editar-chamado-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Editar chamado</h3>
          <button class="modal-close" id="editar-chamado-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="editar-chamado-form">
          <div class="field">
            <label for="editar-chamado-cliente-busca">Cliente</label>
            <div class="busca-select">
              <input type="text" id="editar-chamado-cliente-busca" placeholder="Digite pra buscar..." autocomplete="off">
              <input type="hidden" id="editar-chamado-cliente-id">
              <div class="busca-select-resultados" id="editar-chamado-cliente-resultados" hidden></div>
            </div>
          </div>
          <div class="field">
            <label for="editar-chamado-colaborador-busca">Colaborador (opcional)</label>
            <div class="busca-select">
              <input type="text" id="editar-chamado-colaborador-busca" placeholder="Digite pra buscar, ou deixe em branco..." autocomplete="off">
              <input type="hidden" id="editar-chamado-colaborador-id">
              <div class="busca-select-resultados" id="editar-chamado-colaborador-resultados" hidden></div>
            </div>
          </div>
          <div class="field">
            <label for="editar-chamado-tipo">Tipo de chamado</label>
            <select id="editar-chamado-tipo"></select>
          </div>
          <div class="field">
            <label for="editar-chamado-prioridade">Prioridade</label>
            <select id="editar-chamado-prioridade"></select>
          </div>
          <div class="field">
            <label for="editar-chamado-descricao">Descrição</label>
            <textarea id="editar-chamado-descricao" rows="4"></textarea>
          </div>
          <div class="error-message" id="editar-chamado-modal-erro"></div>
          <button type="submit" class="btn-primary" id="editar-chamado-modal-enviar">Salvar correção</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('editar-chamado-modal-fechar').addEventListener('click', () => {
    document.getElementById('editar-chamado-modal-overlay').hidden = true;
  });
  document.getElementById('editar-chamado-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'editar-chamado-modal-overlay') document.getElementById('editar-chamado-modal-overlay').hidden = true;
  });

  ligarBuscaEditarChamado('editar-chamado-cliente', () => clientesEditarChamadoCache);
  ligarBuscaEditarChamado('editar-chamado-colaborador', () => colaboradoresEditarChamadoCache);

  document.getElementById('editar-chamado-form').addEventListener('submit', salvarEdicaoChamado);
}

function ligarBuscaEditarChamado(prefixo, obterLista) {
  const input = document.getElementById(`${prefixo}-busca`);
  const idInput = document.getElementById(`${prefixo}-id`);
  const resultadosBox = document.getElementById(`${prefixo}-resultados`);
  const container = input.closest('.busca-select');

  function renderizar(termo) {
    const lista = obterLista();
    const termoNormalizado = termo.trim().toLowerCase();
    const filtrados = termoNormalizado ? lista.filter((c) => c.nome.toLowerCase().includes(termoNormalizado)) : lista;
    resultadosBox.innerHTML =
      filtrados.length === 0
        ? '<div class="busca-select-vazio">Nada encontrado.</div>'
        : filtrados.slice(0, 50).map((c) => `<div class="busca-select-item" data-id="${c.id}" data-nome="${c.nome}">${c.nome}</div>`).join('');
    resultadosBox.hidden = false;
  }

  input.addEventListener('input', () => {
    idInput.value = '';
    renderizar(input.value);
  });
  input.addEventListener('focus', () => renderizar(input.value));
  resultadosBox.addEventListener('click', (evento) => {
    const item = evento.target.closest('.busca-select-item');
    if (!item) return;
    idInput.value = item.dataset.id;
    input.value = item.dataset.nome;
    resultadosBox.hidden = true;
  });
  document.addEventListener('click', (evento) => {
    if (!container.contains(evento.target)) resultadosBox.hidden = true;
  });
}

async function abrirModalEditarChamado(chamadoId) {
  const chamado = chamadosAtuais.find((c) => c.id === Number(chamadoId));
  if (!chamado) return;
  chamadoIdEmEdicaoBasico = chamadoId;

  if (clientesEditarChamadoCache.length === 0) {
    clientesEditarChamadoCache = await Shell.chamarApi('/clientes-dados');
  }
  if (colaboradoresEditarChamadoCache.length === 0) {
    colaboradoresEditarChamadoCache = await Shell.chamarApi('/colaboradores-dados');
  }

  document.getElementById('editar-chamado-modal-erro').classList.remove('visible');
  document.getElementById('editar-chamado-cliente-busca').value = chamado.cliente_nome;
  document.getElementById('editar-chamado-cliente-id').value = chamado.cliente_id;
  document.getElementById('editar-chamado-colaborador-busca').value = chamado.colaborador_nome || '';
  document.getElementById('editar-chamado-colaborador-id').value = chamado.colaborador_id || '';
  document.getElementById('editar-chamado-tipo').innerHTML = TIPOS.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');
  document.getElementById('editar-chamado-tipo').value = chamado.tipo;
  document.getElementById('editar-chamado-prioridade').innerHTML = PRIORIDADES.map((p) => `<option value="${p.chave}">${p.label}</option>`).join('');
  document.getElementById('editar-chamado-prioridade').value = chamado.prioridade;
  document.getElementById('editar-chamado-descricao').value = chamado.descricao;

  document.getElementById('editar-chamado-modal-overlay').hidden = false;
}

let chamadoIdEmEdicaoBasico = null;

async function salvarEdicaoChamado(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-chamado-modal-erro');
  const botao = document.getElementById('editar-chamado-modal-enviar');
  erroBox.classList.remove('visible');

  const clienteIdValor = document.getElementById('editar-chamado-cliente-id').value;
  if (!clienteIdValor) {
    erroBox.textContent = 'Escolha um cliente da lista de busca.';
    erroBox.classList.add('visible');
    return;
  }

  const colaboradorIdValor = document.getElementById('editar-chamado-colaborador-id').value;
  const corpo = {
    cliente_id: Number(clienteIdValor),
    colaborador_id: colaboradorIdValor ? Number(colaboradorIdValor) : null,
    tipo: document.getElementById('editar-chamado-tipo').value,
    prioridade: document.getElementById('editar-chamado-prioridade').value,
    descricao: document.getElementById('editar-chamado-descricao').value,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoIdEmEdicaoBasico}/editar`, { method: 'PATCH', body: corpo });
    document.getElementById('editar-chamado-modal-overlay').hidden = true;
    carregarChamados();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar correção';
  }
}

function montarModalAcaoCorretiva() {
  const html = `
    <div class="modal-overlay" id="acao-corretiva-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Ação corretiva</h3>
          <button class="modal-close" id="acao-corretiva-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="acao-corretiva-form">
          <div class="field">
            <label for="acao-corretiva-texto">O que foi feito, qual método usado, etc.</label>
            <textarea id="acao-corretiva-texto" rows="5" placeholder="Descreva o que foi feito pra resolver esse chamado..."></textarea>
          </div>
          <div class="field">
            <label for="acao-corretiva-arquivo">Anexar documento (opcional, JPEG/PNG/PDF)</label>
            <input type="file" id="acao-corretiva-arquivo" accept=".jpg,.jpeg,.png,.pdf">
            <div class="meta" id="acao-corretiva-arquivo-atual" style="margin-top: 4px;"></div>
          </div>
          <div class="error-message" id="acao-corretiva-modal-erro"></div>
          <button type="submit" class="btn-primary" id="acao-corretiva-modal-enviar">Salvar</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('acao-corretiva-modal-fechar').addEventListener('click', () => {
    document.getElementById('acao-corretiva-modal-overlay').hidden = true;
  });
  document.getElementById('acao-corretiva-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'acao-corretiva-modal-overlay') document.getElementById('acao-corretiva-modal-overlay').hidden = true;
  });
  document.getElementById('acao-corretiva-form').addEventListener('submit', salvarAcaoCorretiva);
}

let chamadoIdEmEdicaoAcao = null;

function abrirModalAcaoCorretiva(chamadoId, acaoAtual) {
  chamadoIdEmEdicaoAcao = chamadoId;
  document.getElementById('acao-corretiva-texto').value = acaoAtual || '';
  document.getElementById('acao-corretiva-arquivo').value = '';
  document.getElementById('acao-corretiva-modal-erro').classList.remove('visible');

  const chamado = chamadosAtuais.find((c) => c.id === Number(chamadoId));
  document.getElementById('acao-corretiva-arquivo-atual').innerHTML =
    chamado && chamado.acao_corretiva_tem_arquivo
      ? `Já tem um documento anexado: <a href="#" id="link-ver-arquivo-acao" data-id="${chamadoId}">${chamado.acao_corretiva_arquivo_nome}</a>. Escolher outro vai substituí-lo.`
      : '';

  document.getElementById('acao-corretiva-modal-overlay').hidden = false;
}

async function salvarAcaoCorretiva(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('acao-corretiva-modal-erro');
  const botao = document.getElementById('acao-corretiva-modal-enviar');
  erroBox.classList.remove('visible');

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoIdEmEdicaoAcao}/editar`, {
      method: 'PATCH',
      body: { acao_corretiva: document.getElementById('acao-corretiva-texto').value || null },
    });

    const arquivo = document.getElementById('acao-corretiva-arquivo').files[0];
    if (arquivo) {
      const autenticacao = Shell.autenticacao();
      const formData = new FormData();
      formData.append('arquivo', arquivo);
      const resposta = await fetch(`/chamados-dados/${chamadoIdEmEdicaoAcao}/acao-corretiva-arquivo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${autenticacao.access_token}` },
        body: formData,
      });
      if (!resposta.ok) {
        const erroResposta = await resposta.json().catch(() => ({}));
        throw new Error(erroResposta.detail || 'Falha ao enviar o arquivo');
      }
    }

    document.getElementById('acao-corretiva-modal-overlay').hidden = true;
    carregarChamados();
  } catch (erro) {
    erroBox.textContent = erro.message || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

async function excluirChamado(chamadoId) {
  if (!confirm('Tem certeza que quer excluir esse chamado? Essa ação não pode ser desfeita.')) return;
  try {
    await Shell.chamarApi(`/chamados-dados/${chamadoId}`, { method: 'DELETE' });
    carregarChamados();
  } catch (erro) {
    if (erro.status === 403) {
      alert('Você não tem permissão pra excluir chamados. Fale com o escritório.');
    } else {
      alert('Não foi possível excluir agora.');
    }
  }
}

async function abrirArquivoAcaoCorretiva(chamadoId) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return;
  try {
    const resposta = await fetch(`/chamados-dados/${chamadoId}/acao-corretiva-arquivo`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (!resposta.ok) throw new Error('Falha ao baixar arquivo');
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (erro) {
    alert('Não foi possível abrir o arquivo agora.');
  }
}

montarModalEditarChamado();
montarModalAcaoCorretiva();

document.getElementById('acao-corretiva-arquivo-atual').addEventListener('click', (evento) => {
  const link = evento.target.closest('#link-ver-arquivo-acao');
  if (!link) return;
  evento.preventDefault();
  abrirArquivoAcaoCorretiva(link.dataset.id);
});

document.addEventListener('click', (evento) => {
  if (evento.target.closest('.btn-ver-mais-descricao')) return;
  document.querySelectorAll('.descricao-texto[data-expandido="true"]').forEach((span) => {
    span.textContent = span.dataset.resumo;
    span.dataset.expandido = 'false';
    const botao = span.nextElementSibling;
    if (botao) botao.textContent = 'Ver mais';
  });
});

iniciar();
