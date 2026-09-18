const auth = Shell.montar('supervisao', 'Supervisão');

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

function formatarDataBR(isoString) {
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

let abaAtual = 'visitas';
let clientesSupervisaoCache = [];

function trocarAba(aba) {
  abaAtual = aba;
  document.querySelectorAll('.tab-relatorio').forEach((botao) => {
    botao.classList.toggle('ativa', botao.dataset.aba === aba);
  });
  document.getElementById('aba-visitas').hidden = aba !== 'visitas';
  document.getElementById('aba-ultima-visita').hidden = aba !== 'ultima-visita';

  if (aba === 'visitas') {
    carregarVisitas();
  } else {
    carregarRelatorioUltimaVisita();
  }
}

document.querySelectorAll('.tab-relatorio').forEach((botao) => {
  botao.addEventListener('click', () => trocarAba(botao.dataset.aba));
});

// ---------------------------------------------------------------------------
// Modal de registrar/editar visita
// ---------------------------------------------------------------------------

function montarModalVisita() {
  const html = `
    <div class="modal-overlay" id="visita-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="visita-modal-titulo">Registrar visita</h3>
          <button class="modal-close" id="visita-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="visita-form">
          <div class="field">
            <label for="visita-cliente-busca">Cliente</label>
            <div class="busca-select">
              <input type="text" id="visita-cliente-busca" placeholder="Digite pra buscar..." autocomplete="off">
              <input type="hidden" id="visita-cliente-id">
              <div class="busca-select-resultados" id="visita-cliente-resultados" hidden></div>
            </div>
          </div>
          <div class="field">
            <label for="visita-data">Data da visita</label>
            <input type="date" id="visita-data" required>
          </div>
          <div class="field">
            <label for="visita-pessoa">Com quem falou no local</label>
            <input type="text" id="visita-pessoa" placeholder="Ex: Zelador João, Síndica Maria...">
          </div>
          <div class="field">
            <label for="visita-observacoes">Observações</label>
            <textarea id="visita-observacoes" rows="4" placeholder="O que foi visto/conversado na visita"></textarea>
          </div>
          <div class="field">
            <label for="visita-acoes">Ações (o que foi feito - pode preencher agora ou depois)</label>
            <textarea id="visita-acoes" rows="4" placeholder="Ex: Solicitado troca de EPI, aguardando retorno do sindico..."></textarea>
          </div>
          <div class="error-message" id="visita-modal-erro"></div>
          <button type="submit" class="btn-primary" id="visita-modal-enviar">Salvar visita</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('visita-modal-fechar').addEventListener('click', fecharModalVisita);
  document.getElementById('visita-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'visita-modal-overlay') fecharModalVisita();
  });

  ligarBuscaClienteVisita();
  document.getElementById('visita-form').addEventListener('submit', salvarVisita);
}

function ligarBuscaClienteVisita() {
  const input = document.getElementById('visita-cliente-busca');
  const idInput = document.getElementById('visita-cliente-id');
  const resultadosBox = document.getElementById('visita-cliente-resultados');
  const container = input.closest('.busca-select');

  function renderizar(termo) {
    const termoNormalizado = termo.trim().toLowerCase();
    const filtrados = termoNormalizado
      ? clientesSupervisaoCache.filter((c) => c.nome.toLowerCase().includes(termoNormalizado))
      : clientesSupervisaoCache;
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

let visitaIdEmEdicao = null;

async function abrirModalNovaVisita() {
  visitaIdEmEdicao = null;
  document.getElementById('visita-modal-titulo').textContent = 'Registrar visita';
  document.getElementById('visita-form').reset();
  document.getElementById('visita-cliente-id').value = '';
  document.getElementById('visita-acoes').value = '';
  document.getElementById('visita-data').value = new Date().toISOString().slice(0, 10);
  document.getElementById('visita-modal-erro').classList.remove('visible');

  if (clientesSupervisaoCache.length === 0) {
    clientesSupervisaoCache = await Shell.chamarApi('/clientes-dados');
  }

  document.getElementById('visita-modal-overlay').hidden = false;
}

async function abrirModalEditarVisita(visita) {
  visitaIdEmEdicao = visita.id;
  document.getElementById('visita-modal-titulo').textContent = 'Editar visita';
  document.getElementById('visita-modal-erro').classList.remove('visible');

  if (clientesSupervisaoCache.length === 0) {
    clientesSupervisaoCache = await Shell.chamarApi('/clientes-dados');
  }

  document.getElementById('visita-cliente-busca').value = visita.cliente_nome;
  document.getElementById('visita-cliente-id').value = visita.cliente_id;
  document.getElementById('visita-data').value = visita.data_visita;
  document.getElementById('visita-pessoa').value = visita.pessoa_com_quem_falou || '';
  document.getElementById('visita-observacoes').value = visita.observacoes || '';
  document.getElementById('visita-acoes').value = visita.acoes || '';

  document.getElementById('visita-modal-overlay').hidden = false;
}

function fecharModalVisita() {
  document.getElementById('visita-modal-overlay').hidden = true;
}

async function salvarVisita(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('visita-modal-erro');
  const botao = document.getElementById('visita-modal-enviar');
  erroBox.classList.remove('visible');

  const clienteId = document.getElementById('visita-cliente-id').value;
  if (!clienteId) {
    erroBox.textContent = 'Escolha um cliente da lista de busca.';
    erroBox.classList.add('visible');
    return;
  }

  const corpo = {
    cliente_id: Number(clienteId),
    data_visita: document.getElementById('visita-data').value,
    pessoa_com_quem_falou: document.getElementById('visita-pessoa').value || null,
    observacoes: document.getElementById('visita-observacoes').value || null,
    acoes: document.getElementById('visita-acoes').value || null,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    if (visitaIdEmEdicao) {
      await Shell.chamarApi(`/visitas-supervisao/${visitaIdEmEdicao}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi('/visitas-supervisao', { method: 'POST', body: corpo });
    }
    fecharModalVisita();
    carregarVisitas();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar a visita agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar visita';
  }
}

// ---------------------------------------------------------------------------
// Lista de visitas
// ---------------------------------------------------------------------------

const LIMITE_OBS_CURTA = 90;

function celulaObsHtml(id, texto) {
  if (!texto) return '—';
  if (texto.length <= LIMITE_OBS_CURTA) return escaparHtml(texto);
  const resumo = texto.slice(0, LIMITE_OBS_CURTA).trim() + '…';
  return `
    <span class="descricao-texto" data-completo="${escaparHtml(texto)}" data-resumo="${escaparHtml(resumo)}" data-expandido="false">${escaparHtml(resumo)}</span>
    <button type="button" class="btn-ver-mais-descricao" data-id="${id}">Ver mais</button>
  `;
}

let visitasCompletas = [];
let buscaVisitasLigada = false;

async function carregarVisitas() {
  const container = document.getElementById('lista-visitas');
  container.innerHTML = '<div class="loading-state">Carregando visitas...</div>';
  try {
    const visitas = await Shell.chamarApi('/visitas-supervisao');
    if (visitas === null) return;
    visitasCompletas = visitas;
    renderizarVisitas(visitas);
    ligarBuscaVisitas();
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar as visitas agora.</div>';
  }
}

function ligarBuscaVisitas() {
  if (buscaVisitasLigada) return;
  buscaVisitasLigada = true;

  const input = document.getElementById('visitas-busca-cliente');
  const resultadosBox = document.getElementById('visitas-busca-cliente-resultados');
  const container = input.closest('.busca-select');

  function nomesUnicos() {
    return [...new Set(visitasCompletas.map((v) => v.cliente_nome))];
  }

  function renderizarSugestoes(termo) {
    const termoNormalizado = termo.trim().toLowerCase();
    if (!termoNormalizado) {
      resultadosBox.hidden = true;
      return;
    }
    const filtrados = nomesUnicos().filter((nome) => nome.toLowerCase().includes(termoNormalizado));
    resultadosBox.innerHTML =
      filtrados.length === 0
        ? '<div class="busca-select-vazio">Nada encontrado.</div>'
        : filtrados.slice(0, 50).map((nome) => `<div class="busca-select-item" data-nome="${escaparHtml(nome)}">${escaparHtml(nome)}</div>`).join('');
    resultadosBox.hidden = false;
  }

  input.addEventListener('input', () => {
    renderizarSugestoes(input.value);
    const termo = input.value.trim().toLowerCase();
    const filtradas = termo ? visitasCompletas.filter((v) => v.cliente_nome.toLowerCase().includes(termo)) : visitasCompletas;
    renderizarVisitas(filtradas);
  });
  input.addEventListener('focus', () => renderizarSugestoes(input.value));
  resultadosBox.addEventListener('click', (evento) => {
    const item = evento.target.closest('.busca-select-item');
    if (!item) return;
    input.value = item.dataset.nome;
    resultadosBox.hidden = true;
    const filtradas = visitasCompletas.filter((v) => v.cliente_nome === item.dataset.nome);
    renderizarVisitas(filtradas);
  });
  document.addEventListener('click', (evento) => {
    if (!container.contains(evento.target)) resultadosBox.hidden = true;
  });
}

function renderizarVisitas(visitas) {
  const container = document.getElementById('lista-visitas');
  if (visitas.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhuma visita registrada ainda.</div>';
    return;
  }

  const linhas = visitas
    .map((v) => {
      const podeGerenciar = v.supervisor_id === auth.id || auth.papel === 'escritorio';
      return `
      <tr>
        <td>${formatarDataBR(v.data_visita)}</td>
        <td><a href="/cliente-detalhe?id=${v.cliente_id}">${escaparHtml(v.cliente_nome)}</a></td>
        <td>${escaparHtml(v.pessoa_com_quem_falou || '—')}</td>
        <td class="chamado-descricao">${celulaObsHtml(`obs-${v.id}`, v.observacoes)}</td>
        <td class="chamado-descricao">${celulaObsHtml(`acoes-${v.id}`, v.acoes)}</td>
        <td>${escaparHtml(v.supervisor_nome)}</td>
        <td class="celula-acoes-tabela">
          ${podeGerenciar ? `<button class="btn-ghost btn-editar-visita" data-id="${v.id}">Editar</button>` : ''}
          ${podeGerenciar ? `<button class="btn-ghost btn-excluir-visita" data-id="${v.id}" style="color: var(--danger);">Excluir</button>` : ''}
        </td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <div class="table-scroll-wrapper"><table class="table-list">
      <thead><tr><th>Data</th><th>Cliente</th><th>Falou com</th><th>Observações</th><th>Ações</th><th>Registrado por</th><th>Gerenciar</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table></div>
  `;

  const visitasAtuais = visitas;

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

  container.querySelectorAll('.btn-editar-visita').forEach((botao) => {
    botao.addEventListener('click', () => {
      const visita = visitasAtuais.find((v) => v.id === Number(botao.dataset.id));
      if (visita) abrirModalEditarVisita(visita);
    });
  });

  container.querySelectorAll('.btn-excluir-visita').forEach((botao) => {
    botao.addEventListener('click', async () => {
      if (!confirm('Excluir esse registro de visita?')) return;
      try {
        await Shell.chamarApi(`/visitas-supervisao/${botao.dataset.id}`, { method: 'DELETE' });
        carregarVisitas();
      } catch (erro) {
        alert('Não foi possível excluir agora.');
      }
    });
  });
}

document.addEventListener('click', (evento) => {
  if (evento.target.closest('.btn-ver-mais-descricao')) return;
  document.querySelectorAll('.descricao-texto[data-expandido="true"]').forEach((span) => {
    span.textContent = span.dataset.resumo;
    span.dataset.expandido = 'false';
    const botao = span.nextElementSibling;
    if (botao) botao.textContent = 'Ver mais';
  });
});

// ---------------------------------------------------------------------------
// Relatório de última visita por cliente
// ---------------------------------------------------------------------------

async function carregarRelatorioUltimaVisita() {
  const container = document.getElementById('relatorio-ultima-visita');
  container.innerHTML = '<div class="loading-state">Carregando relatório...</div>';
  try {
    const dados = await Shell.chamarApi('/relatorios-dados/ultima-visita-por-cliente');
    if (dados === null) return;
    dadosUltimaVisitaCompletos = dados;
    renderizarRelatorioUltimaVisita(dados);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o relatório agora.</div>';
  }
}

let dadosUltimaVisitaCompletos = null;

function renderizarRelatorioUltimaVisita(dados) {
  const container = document.getElementById('relatorio-ultima-visita');

  const linhas = dados.clientes
    .map((c) => {
      let situacaoHtml;
      if (c.ultima_visita === null) {
        situacaoHtml = '<span class="priority-badge urgente">Nunca visitado</span>';
      } else if (c.dias_sem_visita > 60) {
        situacaoHtml = `<span class="priority-badge urgente">${c.dias_sem_visita} dias sem visita</span>`;
      } else if (c.dias_sem_visita > 30) {
        situacaoHtml = `<span class="priority-badge normal">${c.dias_sem_visita} dias sem visita</span>`;
      } else {
        situacaoHtml = `<span class="meta">${c.dias_sem_visita} dia(s) atrás</span>`;
      }
      return `
      <tr>
        <td><a href="/cliente-detalhe?id=${c.cliente_id}">${escaparHtml(c.cliente_nome)}</a></td>
        <td>${escaparHtml(c.empresa_nome)}</td>
        <td>${escaparHtml(c.supervisor_nome || '—')}</td>
        <td>${c.ultima_visita ? formatarDataBR(c.ultima_visita) : '—'}</td>
        <td>${situacaoHtml}</td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">clientes</div><div class="value">${dados.total_clientes}</div></div>
      <div class="kpi-card"><div class="label">nunca visitados</div><div class="value">${dados.clientes.filter((c) => c.ultima_visita === null).length}</div></div>
    </div>
    <div class="field" style="max-width: 320px; margin-top: 20px;">
      <label for="ultima-visita-busca">Buscar cliente</label>
      <div class="busca-select">
        <input type="text" id="ultima-visita-busca" placeholder="Digite o nome do cliente..." autocomplete="off">
        <div class="busca-select-resultados" id="ultima-visita-resultados" hidden></div>
      </div>
    </div>
    <div class="section-title" style="margin-top: 20px;">Última visita por cliente</div>
    <div class="table-scroll-wrapper"><table class="table-list">
      <thead><tr><th>Cliente</th><th>Empresa</th><th>Supervisor</th><th>Última visita</th><th>Situação</th></tr></thead>
      <tbody id="corpo-ultima-visita">${linhas}</tbody>
    </table></div>
  `;

  ligarBuscaUltimaVisita();
}

function ligarBuscaUltimaVisita() {
  const input = document.getElementById('ultima-visita-busca');
  const resultadosBox = document.getElementById('ultima-visita-resultados');
  const container = input.closest('.busca-select');

  function renderizarSugestoes(termo) {
    const termoNormalizado = termo.trim().toLowerCase();
    if (!termoNormalizado) {
      resultadosBox.hidden = true;
      return;
    }
    const filtrados = dadosUltimaVisitaCompletos.clientes.filter((c) => c.cliente_nome.toLowerCase().includes(termoNormalizado));
    resultadosBox.innerHTML =
      filtrados.length === 0
        ? '<div class="busca-select-vazio">Nada encontrado.</div>'
        : filtrados.slice(0, 50).map((c) => `<div class="busca-select-item" data-id="${c.cliente_id}">${c.cliente_nome}</div>`).join('');
    resultadosBox.hidden = false;
  }

  input.addEventListener('input', () => {
    renderizarSugestoes(input.value);
    if (!input.value.trim()) {
      renderizarRelatorioUltimaVisita(dadosUltimaVisitaCompletos);
    }
  });
  input.addEventListener('focus', () => renderizarSugestoes(input.value));
  resultadosBox.addEventListener('click', (evento) => {
    const item = evento.target.closest('.busca-select-item');
    if (!item) return;
    const clienteFiltrado = dadosUltimaVisitaCompletos.clientes.filter((c) => c.cliente_id === Number(item.dataset.id));
    const corpo = document.getElementById('corpo-ultima-visita');
    corpo.innerHTML = clienteFiltrado
      .map((c) => {
        let situacaoHtml;
        if (c.ultima_visita === null) {
          situacaoHtml = '<span class="priority-badge urgente">Nunca visitado</span>';
        } else if (c.dias_sem_visita > 60) {
          situacaoHtml = `<span class="priority-badge urgente">${c.dias_sem_visita} dias sem visita</span>`;
        } else if (c.dias_sem_visita > 30) {
          situacaoHtml = `<span class="priority-badge normal">${c.dias_sem_visita} dias sem visita</span>`;
        } else {
          situacaoHtml = `<span class="meta">${c.dias_sem_visita} dia(s) atrás</span>`;
        }
        return `
        <tr>
          <td><a href="/cliente-detalhe?id=${c.cliente_id}">${escaparHtml(c.cliente_nome)}</a></td>
          <td>${escaparHtml(c.empresa_nome)}</td>
          <td>${escaparHtml(c.supervisor_nome || '—')}</td>
          <td>${c.ultima_visita ? formatarDataBR(c.ultima_visita) : '—'}</td>
          <td>${situacaoHtml}</td>
        </tr>
      `;
      })
      .join('');
    input.value = item.textContent;
    resultadosBox.hidden = true;
  });
  document.addEventListener('click', (evento) => {
    if (!container.contains(evento.target)) resultadosBox.hidden = true;
  });
}

montarModalVisita();
document.getElementById('btn-nova-visita').addEventListener('click', abrirModalNovaVisita);
carregarVisitas();
