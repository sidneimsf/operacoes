const auth = Shell.montar('asos', 'ASOs');

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function labelSituacao(situacao, diasRestantes) {
  if (situacao === 'vencido') return `Vencido há ${Math.abs(diasRestantes)} dia(s)`;
  if (situacao === 'proximo') return `Vence em ${diasRestantes} dia(s)`;
  return `Em dia (${diasRestantes} dias)`;
}

let asosCompletos = [];
let termoBuscaAso = '';
let recemRealizados = {};

function formatarDataISO(d) {
  return d.toISOString().slice(0, 10);
}

function renderizarLista(asos) {
  const container = document.getElementById('lista-asos');

  const vencidos = asos.filter((a) => a.situacao === 'vencido').length;
  const proximos = asos.filter((a) => a.situacao === 'proximo').length;
  const emDia = asos.filter((a) => a.situacao === 'ok').length;

  const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
  cards[0].textContent = vencidos;
  cards[1].textContent = proximos;
  cards[2].textContent = emDia;

  if (asos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum ASO cadastrado ainda.</div>';
    return;
  }

  const linhas = asos
    .map((a) => {
      const foiRealizadoAgora = !!recemRealizados[a.evento_id];
      const botaoRealizadoOuDesfazer = foiRealizadoAgora
        ? `<button class="btn-ghost btn-aso-desfazer" data-evento-id="${a.evento_id}" style="padding: 5px 10px; font-size: 12px; color: var(--danger);">Desfazer</button>`
        : a.situacao !== 'ok'
        ? `<button class="btn-primary btn-aso-realizado" data-evento-id="${a.evento_id}" data-colaborador="${a.colaborador_nome}" style="width: auto; padding: 5px 10px; font-size: 12px;">ASO Realizado</button>`
        : '';

      return `
      <tr>
        <td><a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a></td>
        <td>${a.cargo || '—'}</td>
        <td>${a.empresa_nome}</td>
        <td>${formatarData(a.data_exame)}</td>
        <td>${formatarData(a.data_vencimento)}</td>
        <td><span class="aso-badge ${a.situacao}">${labelSituacao(a.situacao, a.dias_restantes)}</span></td>
        <td style="white-space: nowrap;">
          ${botaoRealizadoOuDesfazer}
          <button class="btn-ghost btn-aso-editar" data-evento-id="${a.evento_id}" data-colaborador="${a.colaborador_nome}" data-exame="${a.data_exame || ''}" data-vencimento="${a.data_vencimento || ''}" style="padding: 5px 10px; font-size: 12px;">Editar</button>
          <button class="btn-ghost btn-aso-excluir" data-evento-id="${a.evento_id}" data-colaborador="${a.colaborador_nome}" style="padding: 5px 10px; font-size: 12px;">Excluir</button>
        </td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Colaborador</th><th>Cargo</th><th>Empresa</th><th>Data do exame</th><th>Vencimento</th><th>Situação</th><th>Ações</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarAsos() {
  const container = document.getElementById('lista-asos');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const asos = await Shell.chamarApi('/asos-dados');
    if (asos === null) return;
    asosCompletos = asos;
    aplicarFiltroBuscaAso();
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

function aplicarFiltroBuscaAso() {
  const termo = termoBuscaAso.trim().toLowerCase();
  const filtrados = termo
    ? asosCompletos.filter((a) => a.colaborador_nome.toLowerCase().includes(termo))
    : asosCompletos;
  renderizarLista(filtrados);
}

async function marcarAsoRealizado(eventoId, colaboradorNome) {
  const registro = asosCompletos.find((a) => a.evento_id === Number(eventoId));
  if (!registro) return;

  if (!confirm(`Confirmar que o ASO de ${colaboradorNome} foi realizado hoje? Isso renova o vencimento por 1 ano.`)) return;

  recemRealizados[eventoId] = {
    data_exame_anterior: registro.data_exame,
    data_vencimento_anterior: registro.data_vencimento,
  };

  const hoje = new Date();
  const vencimentoNovo = new Date(hoje);
  vencimentoNovo.setDate(vencimentoNovo.getDate() + 365);

  try {
    await Shell.chamarApi(`/colaboradores-dados/eventos/${eventoId}`, {
      method: 'PATCH',
      body: { data_inicio: formatarDataISO(hoje), data_fim: formatarDataISO(vencimentoNovo) },
    });
    await carregarAsos();
  } catch (erro) {
    delete recemRealizados[eventoId];
    alert('Não foi possível marcar como realizado agora.');
  }
}

async function desfazerAsoRealizado(eventoId) {
  const anterior = recemRealizados[eventoId];
  if (!anterior) return;

  try {
    await Shell.chamarApi(`/colaboradores-dados/eventos/${eventoId}`, {
      method: 'PATCH',
      body: { data_inicio: anterior.data_exame_anterior, data_fim: anterior.data_vencimento_anterior },
    });
    delete recemRealizados[eventoId];
    await carregarAsos();
  } catch (erro) {
    alert('Não foi possível desfazer agora.');
  }
}

// ---------- Adicionar novo ASO ----------

let colaboradoresAgrupadosCache = null;

async function carregarColaboradoresAgrupados() {
  if (colaboradoresAgrupadosCache) return colaboradoresAgrupadosCache;
  const [empresas, colaboradores] = await Promise.all([
    Shell.chamarApi('/empresas'),
    Shell.chamarApi('/colaboradores-dados'),
  ]);
  colaboradoresAgrupadosCache = empresas.map((e) => ({
    empresa: e.nome,
    colaboradores: colaboradores.filter((c) => c.empresa_id === e.id),
  }));
  return colaboradoresAgrupadosCache;
}

function montarModalNovoAso() {
  const html = `
    <div class="modal-overlay" id="novo-aso-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Adicionar ASO</h3>
          <button class="modal-close" id="novo-aso-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="novo-aso-form">
          <div class="field">
            <label for="novo-aso-colaborador">Colaborador</label>
            <select id="novo-aso-colaborador" required></select>
          </div>
          <div class="field">
            <label for="novo-aso-exame">Data do exame</label>
            <input type="date" id="novo-aso-exame" required>
          </div>
          <div class="field">
            <label for="novo-aso-vencimento">Data de vencimento</label>
            <input type="date" id="novo-aso-vencimento" required>
          </div>
          <div class="error-message" id="novo-aso-modal-erro"></div>
          <button type="submit" class="btn-primary" id="novo-aso-modal-enviar">Adicionar ASO</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('novo-aso-modal-fechar').addEventListener('click', () => {
    document.getElementById('novo-aso-modal-overlay').hidden = true;
  });
  document.getElementById('novo-aso-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'novo-aso-modal-overlay') {
      document.getElementById('novo-aso-modal-overlay').hidden = true;
    }
  });
  document.getElementById('novo-aso-form').addEventListener('submit', enviarNovoAso);
}

async function abrirModalNovoAso() {
  document.getElementById('novo-aso-form').reset();
  document.getElementById('novo-aso-modal-erro').classList.remove('visible');

  const grupos = await carregarColaboradoresAgrupados();
  document.getElementById('novo-aso-colaborador').innerHTML = grupos
    .map(
      (g) =>
        `<optgroup label="${g.empresa}">${g.colaboradores.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('')}</optgroup>`
    )
    .join('');

  document.getElementById('novo-aso-modal-overlay').hidden = false;
}

async function enviarFormData(caminho, formData) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return null;

  const resposta = await fetch(caminho, {
    method: 'POST',
    headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    body: formData,
  });

  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error(`Falha ao chamar ${caminho}: ${resposta.status}`);
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }
  return resposta.json();
}

async function enviarNovoAso(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('novo-aso-modal-erro');
  const botao = document.getElementById('novo-aso-modal-enviar');
  erroBox.classList.remove('visible');

  const colaboradorId = document.getElementById('novo-aso-colaborador').value;
  const formData = new FormData();
  formData.append('tipo', 'aso');
  formData.append('data_inicio', document.getElementById('novo-aso-exame').value);
  formData.append('data_fim', document.getElementById('novo-aso-vencimento').value);

  botao.disabled = true;
  botao.textContent = 'Adicionando...';

  try {
    await enviarFormData(`/colaboradores-dados/${colaboradorId}/eventos`, formData);
    document.getElementById('novo-aso-modal-overlay').hidden = true;
    carregarAsos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível adicionar o ASO agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Adicionar ASO';
  }
}

// ---------- Editar ASO existente ----------

function montarModalEditarAso() {
  const html = `
    <div class="modal-overlay" id="editar-aso-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="editar-aso-modal-titulo">Editar ASO</h3>
          <button class="modal-close" id="editar-aso-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="editar-aso-form">
          <div class="field">
            <label for="editar-aso-exame">Data do exame</label>
            <input type="date" id="editar-aso-exame" required>
          </div>
          <div class="field">
            <label for="editar-aso-vencimento">Data de vencimento</label>
            <input type="date" id="editar-aso-vencimento" required>
          </div>
          <div class="error-message" id="editar-aso-modal-erro"></div>
          <button type="submit" class="btn-primary" id="editar-aso-modal-enviar">Salvar alterações</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('editar-aso-modal-fechar').addEventListener('click', () => {
    document.getElementById('editar-aso-modal-overlay').hidden = true;
  });
  document.getElementById('editar-aso-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'editar-aso-modal-overlay') {
      document.getElementById('editar-aso-modal-overlay').hidden = true;
    }
  });
  document.getElementById('editar-aso-form').addEventListener('submit', salvarEdicaoAso);
}

let eventoIdEmEdicao = null;

function abrirModalEditarAso(eventoId, colaboradorNome, dataExame, dataVencimento) {
  eventoIdEmEdicao = eventoId;
  document.getElementById('editar-aso-modal-titulo').textContent = `Editar ASO · ${colaboradorNome}`;
  document.getElementById('editar-aso-exame').value = dataExame;
  document.getElementById('editar-aso-vencimento').value = dataVencimento;
  document.getElementById('editar-aso-modal-erro').classList.remove('visible');
  document.getElementById('editar-aso-modal-overlay').hidden = false;
}

async function salvarEdicaoAso(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-aso-modal-erro');
  const botao = document.getElementById('editar-aso-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    data_inicio: document.getElementById('editar-aso-exame').value,
    data_fim: document.getElementById('editar-aso-vencimento').value,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    await Shell.chamarApi(`/colaboradores-dados/eventos/${eventoIdEmEdicao}`, { method: 'PATCH', body: corpo });
    document.getElementById('editar-aso-modal-overlay').hidden = true;
    carregarAsos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar alterações';
  }
}

// ---------- Excluir ASO ----------

async function excluirAso(eventoId, colaboradorNome) {
  if (!confirm(`Excluir o registro de ASO de ${colaboradorNome}?`)) return;
  try {
    await Shell.chamarApi(`/colaboradores-dados/eventos/${eventoId}`, { method: 'DELETE' });
    carregarAsos();
  } catch (erro) {
    alert('Não foi possível excluir agora.');
  }
}

async function testarEnvioEmail() {
  const botao = document.getElementById('btn-testar-email');
  const resultadoBox = document.getElementById('resultado-teste-email');
  botao.disabled = true;
  botao.textContent = 'Enviando...';
  resultadoBox.innerHTML = '';

  try {
    const resultado = await Shell.chamarApi('/asos-dados/testar-email', { method: 'POST' });
    if (resultado.enviado) {
      resultadoBox.innerHTML = `<div class="error-message visible" style="background: rgba(92,184,138,0.12); color: var(--success); border-color: rgba(92,184,138,0.3);">
        E-mail enviado para ${resultado.destinatarios.join(', ')} com ${resultado.total} ASO(s) crítico(s).
      </div>`;
    } else {
      resultadoBox.innerHTML = `<div class="error-message visible">${resultado.motivo}</div>`;
    }
  } catch (erro) {
    resultadoBox.innerHTML = `<div class="error-message visible">${erro.detalhe || 'Não foi possível enviar o e-mail agora.'}</div>`;
  } finally {
    botao.disabled = false;
    botao.textContent = 'Testar envio de e-mail';
  }
}

document.getElementById('btn-testar-email').addEventListener('click', testarEnvioEmail);

montarModalNovoAso();
document.getElementById('btn-novo-aso').addEventListener('click', abrirModalNovoAso);

montarModalEditarAso();
document.getElementById('lista-asos').addEventListener('click', (evento) => {
  const botaoRealizado = evento.target.closest('.btn-aso-realizado');
  if (botaoRealizado) {
    marcarAsoRealizado(botaoRealizado.dataset.eventoId, botaoRealizado.dataset.colaborador);
    return;
  }
  const botaoDesfazer = evento.target.closest('.btn-aso-desfazer');
  if (botaoDesfazer) {
    desfazerAsoRealizado(botaoDesfazer.dataset.eventoId);
    return;
  }
  const botaoEditar = evento.target.closest('.btn-aso-editar');
  if (botaoEditar) {
    abrirModalEditarAso(
      botaoEditar.dataset.eventoId,
      botaoEditar.dataset.colaborador,
      botaoEditar.dataset.exame,
      botaoEditar.dataset.vencimento
    );
    return;
  }
  const botaoExcluir = evento.target.closest('.btn-aso-excluir');
  if (botaoExcluir) {
    excluirAso(botaoExcluir.dataset.eventoId, botaoExcluir.dataset.colaborador);
  }
});

document.getElementById("busca-aso").addEventListener("input", (evento) => {
  termoBuscaAso = evento.target.value;
  aplicarFiltroBuscaAso();
});

carregarAsos();
