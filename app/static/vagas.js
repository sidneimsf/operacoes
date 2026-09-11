const auth = Shell.montar('vagas', 'Vagas Abertas');

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

let clientesVagaCache = [];

function montarModalVaga() {
  const html = `
    <div class="modal-overlay" id="vaga-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="vaga-modal-titulo">Cadastrar vaga</h3>
          <button class="modal-close" id="vaga-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="vaga-form">
          <div class="field">
            <label for="vaga-titulo">Título da vaga</label>
            <input type="text" id="vaga-titulo" required placeholder="Ex: Auxiliar de Serviços Gerais">
          </div>
          <div class="field">
            <label for="vaga-cliente-busca">Cliente / local (opcional)</label>
            <div class="busca-select">
              <input type="text" id="vaga-cliente-busca" placeholder="Digite pra buscar, ou deixe em branco..." autocomplete="off">
              <input type="hidden" id="vaga-cliente-id">
              <div class="busca-select-resultados" id="vaga-cliente-resultados" hidden></div>
            </div>
          </div>
          <div class="field">
            <label for="vaga-descricao">Descrição</label>
            <textarea id="vaga-descricao" rows="5" required placeholder="Requisitos, horário, salário, etc."></textarea>
          </div>
          <div class="error-message" id="vaga-modal-erro"></div>
          <button type="submit" class="btn-primary" id="vaga-modal-enviar">Publicar vaga</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('vaga-modal-fechar').addEventListener('click', fecharModalVaga);
  document.getElementById('vaga-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'vaga-modal-overlay') fecharModalVaga();
  });

  ligarBuscaCliente();
  document.getElementById('vaga-form').addEventListener('submit', enviarVaga);
}

function ligarBuscaCliente() {
  const input = document.getElementById('vaga-cliente-busca');
  const idInput = document.getElementById('vaga-cliente-id');
  const resultadosBox = document.getElementById('vaga-cliente-resultados');
  const container = input.closest('.busca-select');

  function renderizar(termo) {
    const termoNormalizado = termo.trim().toLowerCase();
    const filtrados = termoNormalizado
      ? clientesVagaCache.filter((c) => c.nome.toLowerCase().includes(termoNormalizado))
      : clientesVagaCache;
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

let vagaIdEmEdicao = null;

async function abrirModalNovaVaga() {
  vagaIdEmEdicao = null;
  document.getElementById('vaga-modal-titulo').textContent = 'Cadastrar vaga';
  document.getElementById('vaga-form').reset();
  document.getElementById('vaga-cliente-id').value = '';
  document.getElementById('vaga-modal-erro').classList.remove('visible');

  if (clientesVagaCache.length === 0) {
    clientesVagaCache = await Shell.chamarApi('/clientes-dados');
  }

  document.getElementById('vaga-modal-overlay').hidden = false;
}

function fecharModalVaga() {
  document.getElementById('vaga-modal-overlay').hidden = true;
}

async function enviarVaga(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('vaga-modal-erro');
  const botao = document.getElementById('vaga-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    titulo: document.getElementById('vaga-titulo').value,
    descricao: document.getElementById('vaga-descricao').value,
    cliente_id: document.getElementById('vaga-cliente-id').value ? Number(document.getElementById('vaga-cliente-id').value) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Publicando...';
  try {
    await Shell.chamarApi('/vagas-dados', { method: 'POST', body: corpo });
    fecharModalVaga();
    carregarVagas();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível publicar a vaga agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Publicar vaga';
  }
}

function formatarData(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function renderizarMural(vagas) {
  const container = document.getElementById('mural-vagas');

  if (vagas.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhuma vaga cadastrada ainda.</div>';
    return;
  }

  container.innerHTML = vagas
    .map((v) => {
      const podeGerenciar = v.criado_por_id === auth.id || auth.papel === 'escritorio';
      return `
      <div class="postit ${v.aberta ? '' : 'postit-fechada'}">
        <div class="pin"></div>
        ${podeGerenciar ? `<button class="postit-excluir" data-vaga-id="${v.id}" aria-label="Excluir vaga" title="Excluir">&times;</button>` : ''}
        <div class="mensagem"><strong>${escaparHtml(v.titulo)}</strong>${!v.aberta ? ' <span class="meta">(preenchida)</span>' : ''}</div>
        <div class="mensagem" style="font-size: 13px; margin-top: 6px;">${escaparHtml(v.descricao)}</div>
        <div class="rodape">
          <span>${v.cliente_nome ? `${v.cliente_nome} · ` : ''}${v.criado_por_nome} · ${formatarData(v.criado_em)}</span>
        </div>
        ${podeGerenciar ? `<button class="btn-ghost btn-toggle-vaga" data-vaga-id="${v.id}" data-atual="${v.aberta}" style="margin-top: 8px;">${v.aberta ? 'Marcar como preenchida' : 'Reabrir vaga'}</button>` : ''}
      </div>
    `;
    })
    .join('');
}

async function excluirVaga(vagaId) {
  if (!confirm('Excluir esta vaga do mural?')) return;
  try {
    await Shell.chamarApi(`/vagas-dados/${vagaId}`, { method: 'DELETE' });
    carregarVagas();
  } catch (erro) {
    alert('Não foi possível excluir a vaga agora.');
  }
}

async function alternarVaga(vagaId, atual) {
  try {
    await Shell.chamarApi(`/vagas-dados/${vagaId}`, { method: 'PATCH', body: { aberta: atual !== 'true' } });
    carregarVagas();
  } catch (erro) {
    alert('Não foi possível atualizar a vaga agora.');
  }
}

async function carregarVagas() {
  const container = document.getElementById('mural-vagas');
  container.innerHTML = '<div class="loading-state">Carregando vagas...</div>';
  try {
    const vagas = await Shell.chamarApi('/vagas-dados');
    if (vagas === null) return;
    renderizarMural(vagas);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar as vagas agora.</div>';
  }
}

document.getElementById('mural-vagas').addEventListener('click', (evento) => {
  const botaoExcluir = evento.target.closest('.postit-excluir');
  if (botaoExcluir) {
    excluirVaga(botaoExcluir.dataset.vagaId);
    return;
  }
  const botaoToggle = evento.target.closest('.btn-toggle-vaga');
  if (botaoToggle) {
    alternarVaga(botaoToggle.dataset.vagaId, botaoToggle.dataset.atual);
  }
});

montarModalVaga();
document.getElementById('btn-nova-vaga').addEventListener('click', abrirModalNovaVaga);
carregarVagas();
