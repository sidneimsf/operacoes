const parametrosUrl = new URLSearchParams(window.location.search);
const veiculoId = parametrosUrl.get('id');

const auth = Shell.montar('veiculos', 'Veículo');

let veiculoAtual = null;

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarMoeda(valor) {
  if (valor === null || valor === undefined) return '—';
  return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// ---------- Cabeçalho, editar, remover ----------

function renderizarHeaderVeiculo() {
  const v = veiculoAtual;
  document.getElementById('topbar-title').textContent = v.apelido || v.placa;
  document.getElementById('veiculo-header').innerHTML = `
    <span class="empresa-tag">${v.modelo}${v.ano ? ` · ${v.ano}` : ''}${v.ativo ? '' : ' · INATIVO'}</span>
    <h2>${v.apelido || v.placa}</h2>
    <span class="cnpj">Placa ${v.placa} · ${v.km_atual.toLocaleString('pt-BR')} km</span>
  `;
  const btnToggle = document.getElementById('btn-toggle-veiculo');
  btnToggle.textContent = v.ativo ? 'Remover veículo' : 'Reativar veículo';
}

function montarModalEditarVeiculo() {
  const html = `
    <div class="modal-overlay" id="editar-veiculo-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Editar veículo</h3>
          <button class="modal-close" id="editar-veiculo-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="editar-veiculo-form">
          <div class="field">
            <label for="editar-veiculo-placa">Placa</label>
            <input type="text" id="editar-veiculo-placa" required>
          </div>
          <div class="field">
            <label for="editar-veiculo-apelido">Apelido</label>
            <input type="text" id="editar-veiculo-apelido">
          </div>
          <div class="field">
            <label for="editar-veiculo-modelo">Modelo</label>
            <input type="text" id="editar-veiculo-modelo" required>
          </div>
          <div class="field">
            <label for="editar-veiculo-ano">Ano</label>
            <input type="number" id="editar-veiculo-ano">
          </div>
          <div class="field">
            <label for="editar-veiculo-km">Quilometragem atual</label>
            <input type="number" id="editar-veiculo-km" min="0" required>
          </div>
          <div class="error-message" id="editar-veiculo-modal-erro"></div>
          <button type="submit" class="btn-primary" id="editar-veiculo-modal-enviar">Salvar alterações</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('editar-veiculo-modal-fechar').addEventListener('click', () => {
    document.getElementById('editar-veiculo-modal-overlay').hidden = true;
  });
  document.getElementById('editar-veiculo-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'editar-veiculo-modal-overlay') {
      document.getElementById('editar-veiculo-modal-overlay').hidden = true;
    }
  });
  document.getElementById('editar-veiculo-form').addEventListener('submit', salvarEdicaoVeiculo);
}

function abrirModalEditarVeiculo() {
  document.getElementById('editar-veiculo-modal-erro').classList.remove('visible');
  document.getElementById('editar-veiculo-placa').value = veiculoAtual.placa;
  document.getElementById('editar-veiculo-apelido').value = veiculoAtual.apelido || '';
  document.getElementById('editar-veiculo-modelo').value = veiculoAtual.modelo;
  document.getElementById('editar-veiculo-ano').value = veiculoAtual.ano || '';
  document.getElementById('editar-veiculo-km').value = veiculoAtual.km_atual;
  document.getElementById('editar-veiculo-modal-overlay').hidden = false;
}

async function salvarEdicaoVeiculo(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-veiculo-modal-erro');
  const botao = document.getElementById('editar-veiculo-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    placa: document.getElementById('editar-veiculo-placa').value,
    apelido: document.getElementById('editar-veiculo-apelido').value || null,
    modelo: document.getElementById('editar-veiculo-modelo').value,
    ano: document.getElementById('editar-veiculo-ano').value ? Number(document.getElementById('editar-veiculo-ano').value) : null,
    km_atual: Number(document.getElementById('editar-veiculo-km').value),
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    veiculoAtual = await Shell.chamarApi(`/veiculos-dados/${veiculoId}`, { method: 'PATCH', body: corpo });
    document.getElementById('editar-veiculo-modal-overlay').hidden = true;
    renderizarHeaderVeiculo();
    renderizarPlano(veiculoAtual.plano_sugerido);
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar alterações';
  }
}

async function alternarStatusVeiculo() {
  const acao = veiculoAtual.ativo ? 'remover' : 'reativar';
  if (!confirm(`Tem certeza que quer ${acao} este veículo?`)) return;

  try {
    veiculoAtual = await Shell.chamarApi(`/veiculos-dados/${veiculoId}`, {
      method: 'PATCH',
      body: { ativo: !veiculoAtual.ativo },
    });
    renderizarHeaderVeiculo();
  } catch (erro) {
    alert('Não foi possível concluir a ação agora.');
  }
}

// ---------- Plano de manutenção sugerido ----------

function renderizarPlano(plano) {
  const container = document.getElementById('plano-manutencao');
  if (!plano || plano.length === 0) {
    container.innerHTML = '<div class="empty-state">Sem plano de referência para este modelo.</div>';
    return;
  }

  const linhas = plano
    .map(
      (p) => `
      <tr>
        <td>${p.item}${p.critico ? ' <span class="aso-badge vencido" style="margin-left:6px;">crítico</span>' : ''}</td>
        <td>a cada ${p.intervalo_km.toLocaleString('pt-BR')} km</td>
        <td>${p.proximo_km.toLocaleString('pt-BR')} km</td>
        <td><span class="aso-badge ${p.situacao}">${p.situacao === 'vencido' ? 'Vencido' : p.situacao === 'proximo' ? 'Próximo' : 'Em dia'}</span></td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead><tr><th>Item</th><th>Intervalo</th><th>Próxima troca</th><th>Situação</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

// ---------- Histórico de manutenções ----------

let manutencoesAtuais = [];

function renderizarManutencoes(manutencoes) {
  const container = document.getElementById('lista-manutencoes');
  manutencoesAtuais = manutencoes;

  if (manutencoes.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhuma manutenção registrada ainda.</div>';
    return;
  }

  const linhas = manutencoes
    .map(
      (m) => `
      <tr>
        <td>${formatarData(m.data)}</td>
        <td><span class="evento-tipo-badge ${m.tipo === 'preventiva' ? 'ferias' : 'falta'}">${m.tipo === 'preventiva' ? 'Preventiva' : 'Corretiva'}</span></td>
        <td>${m.km.toLocaleString('pt-BR')} km</td>
        <td>${m.descricao}</td>
        <td>${formatarMoeda(m.custo)}</td>
        <td>${m.registrado_por}</td>
        <td>
          <button class="btn-ghost btn-manutencao-editar" data-id="${m.id}" style="padding: 5px 10px; font-size: 12px;">Editar</button>
          <button class="btn-ghost btn-manutencao-excluir" data-id="${m.id}" style="padding: 5px 10px; font-size: 12px;">Excluir</button>
        </td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead><tr><th>Data</th><th>Tipo</th><th>KM</th><th>Descrição</th><th>Custo</th><th>Registrado por</th><th>Ações</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarManutencoes() {
  const container = document.getElementById('lista-manutencoes');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const manutencoes = await Shell.chamarApi(`/veiculos-dados/${veiculoId}/manutencoes`);
    if (manutencoes === null) return;
    renderizarManutencoes(manutencoes);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o histórico agora.</div>';
  }
}

function montarModalManutencao() {
  const html = `
    <div class="modal-overlay" id="manutencao-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="manutencao-modal-titulo">Nova manutenção</h3>
          <button class="modal-close" id="manutencao-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="manutencao-form">
          <div class="field">
            <label for="manutencao-tipo">Tipo</label>
            <select id="manutencao-tipo" required>
              <option value="preventiva">Preventiva</option>
              <option value="corretiva">Corretiva</option>
            </select>
          </div>
          <div class="field">
            <label for="manutencao-data">Data</label>
            <input type="date" id="manutencao-data" required>
          </div>
          <div class="field">
            <label for="manutencao-km">Quilometragem no momento</label>
            <input type="number" id="manutencao-km" min="0" required>
          </div>
          <div class="field">
            <label for="manutencao-descricao">Descrição</label>
            <textarea id="manutencao-descricao" rows="3" required placeholder="Ex: Troca de óleo e filtro"></textarea>
          </div>
          <div class="field">
            <label for="manutencao-custo">Custo (opcional)</label>
            <input type="number" id="manutencao-custo" min="0" step="0.01" placeholder="Ex: 180.00">
          </div>
          <div class="error-message" id="manutencao-modal-erro"></div>
          <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn-primary" id="manutencao-modal-enviar" style="flex: 1;">Salvar</button>
            <button type="button" class="btn-ghost" id="manutencao-modal-remover" hidden>Excluir</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('manutencao-modal-fechar').addEventListener('click', () => {
    document.getElementById('manutencao-modal-overlay').hidden = true;
  });
  document.getElementById('manutencao-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'manutencao-modal-overlay') {
      document.getElementById('manutencao-modal-overlay').hidden = true;
    }
  });
  document.getElementById('manutencao-form').addEventListener('submit', salvarManutencao);
  document.getElementById('manutencao-modal-remover').addEventListener('click', excluirManutencaoAtual);
}

let manutencaoIdEmEdicao = null;

function abrirModalNovaManutencao() {
  manutencaoIdEmEdicao = null;
  document.getElementById('manutencao-form').reset();
  document.getElementById('manutencao-modal-titulo').textContent = 'Nova manutenção';
  document.getElementById('manutencao-km').value = veiculoAtual.km_atual;
  document.getElementById('manutencao-data').value = new Date().toISOString().slice(0, 10);
  document.getElementById('manutencao-modal-erro').classList.remove('visible');
  document.getElementById('manutencao-modal-remover').hidden = true;
  document.getElementById('manutencao-modal-overlay').hidden = false;
}

function abrirModalEditarManutencao(id) {
  const registro = manutencoesAtuais.find((m) => m.id === Number(id));
  if (!registro) return;
  manutencaoIdEmEdicao = registro.id;

  document.getElementById('manutencao-modal-titulo').textContent = 'Editar manutenção';
  document.getElementById('manutencao-tipo').value = registro.tipo;
  document.getElementById('manutencao-data').value = registro.data;
  document.getElementById('manutencao-km').value = registro.km;
  document.getElementById('manutencao-descricao').value = registro.descricao;
  document.getElementById('manutencao-custo').value = registro.custo ?? '';
  document.getElementById('manutencao-modal-erro').classList.remove('visible');
  document.getElementById('manutencao-modal-remover').hidden = false;
  document.getElementById('manutencao-modal-overlay').hidden = false;
}

async function salvarManutencao(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('manutencao-modal-erro');
  const botao = document.getElementById('manutencao-modal-enviar');
  erroBox.classList.remove('visible');

  const custoValor = document.getElementById('manutencao-custo').value;
  const corpo = {
    tipo: document.getElementById('manutencao-tipo').value,
    data: document.getElementById('manutencao-data').value,
    km: Number(document.getElementById('manutencao-km').value),
    descricao: document.getElementById('manutencao-descricao').value,
    custo: custoValor ? Number(custoValor) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    if (manutencaoIdEmEdicao) {
      await Shell.chamarApi(`/veiculos-dados/manutencoes/${manutencaoIdEmEdicao}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi(`/veiculos-dados/${veiculoId}/manutencoes`, { method: 'POST', body: corpo });
    }
    document.getElementById('manutencao-modal-overlay').hidden = true;
    await recarregarTudo();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

async function excluirManutencaoAtual() {
  if (!manutencaoIdEmEdicao) return;
  if (!confirm('Excluir este registro de manutenção?')) return;

  try {
    await Shell.chamarApi(`/veiculos-dados/manutencoes/${manutencaoIdEmEdicao}`, { method: 'DELETE' });
    document.getElementById('manutencao-modal-overlay').hidden = true;
    await recarregarTudo();
  } catch (erro) {
    alert('Não foi possível excluir agora.');
  }
}

async function recarregarTudo() {
  veiculoAtual = await Shell.chamarApi(`/veiculos-dados/${veiculoId}`);
  renderizarHeaderVeiculo();
  renderizarPlano(veiculoAtual.plano_sugerido);
  await carregarManutencoes();
}

// ---------- Inicialização ----------

async function iniciar() {
  if (!veiculoId) {
    document.getElementById('veiculo-header').innerHTML = '<div class="empty-state">Veículo não especificado.</div>';
    return;
  }

  try {
    veiculoAtual = await Shell.chamarApi(`/veiculos-dados/${veiculoId}`);
    if (veiculoAtual === null) return;

    renderizarHeaderVeiculo();
    renderizarPlano(veiculoAtual.plano_sugerido);

    montarModalEditarVeiculo();
    document.getElementById('btn-editar-veiculo').addEventListener('click', abrirModalEditarVeiculo);
    document.getElementById('btn-toggle-veiculo').addEventListener('click', alternarStatusVeiculo);

    montarModalManutencao();
    document.getElementById('btn-nova-manutencao').addEventListener('click', abrirModalNovaManutencao);
    document.getElementById('lista-manutencoes').addEventListener('click', (evento) => {
      const botaoEditar = evento.target.closest('.btn-manutencao-editar');
      if (botaoEditar) {
        abrirModalEditarManutencao(botaoEditar.dataset.id);
        return;
      }
      const botaoExcluir = evento.target.closest('.btn-manutencao-excluir');
      if (botaoExcluir) {
        manutencaoIdEmEdicao = Number(botaoExcluir.dataset.id);
        excluirManutencaoAtual();
      }
    });

    await carregarManutencoes();
  } catch (erro) {
    if (erro.status === 403) {
      document.getElementById('veiculo-header').innerHTML =
        '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    document.getElementById('veiculo-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
