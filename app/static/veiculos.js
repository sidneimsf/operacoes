const auth = Shell.montar('veiculos', 'Veículos');

function renderizarLista(veiculos) {
  const container = document.getElementById('lista-veiculos');

  if (veiculos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum veículo cadastrado ainda.</div>';
    return;
  }

  container.innerHTML = `
    <div class="kpi-grid">
      ${veiculos
        .map(
          (v) => `
        <a href="/veiculo-detalhe?id=${v.id}" class="kpi-card" style="text-decoration: none; color: inherit; display: block;">
          <div class="label">${v.apelido || v.placa} · ${v.modelo}</div>
          <div class="value">${v.km_atual.toLocaleString('pt-BR')} <span style="font-size: 14px; color: var(--text-muted);">km</span></div>
          <div class="meta" style="margin-top: 6px;">Placa ${v.placa}${v.ano ? ` · ${v.ano}` : ''}</div>
        </a>
      `
        )
        .join('')}
    </div>
  `;
}

async function carregarVeiculos() {
  const container = document.getElementById('lista-veiculos');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const veiculos = await Shell.chamarApi('/veiculos-dados');
    if (veiculos === null) return;
    renderizarLista(veiculos);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os veículos agora.</div>';
  }
}

function montarModalNovoVeiculo() {
  const html = `
    <div class="modal-overlay" id="novo-veiculo-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo veículo</h3>
          <button class="modal-close" id="novo-veiculo-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="novo-veiculo-form">
          <div class="field">
            <label for="veiculo-form-placa">Placa</label>
            <input type="text" id="veiculo-form-placa" required placeholder="Ex: ABC1D23">
          </div>
          <div class="field">
            <label for="veiculo-form-apelido">Apelido (opcional)</label>
            <input type="text" id="veiculo-form-apelido" placeholder="Ex: Mobi 1">
          </div>
          <div class="field">
            <label for="veiculo-form-modelo">Modelo</label>
            <input type="text" id="veiculo-form-modelo" value="Fiat Mobi" required>
          </div>
          <div class="field">
            <label for="veiculo-form-ano">Ano (opcional)</label>
            <input type="number" id="veiculo-form-ano" placeholder="Ex: 2024">
          </div>
          <div class="field">
            <label for="veiculo-form-km">Quilometragem atual</label>
            <input type="number" id="veiculo-form-km" min="0" value="0" required>
          </div>
          <div class="error-message" id="novo-veiculo-modal-erro"></div>
          <button type="submit" class="btn-primary" id="novo-veiculo-modal-enviar">Criar veículo</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('novo-veiculo-modal-fechar').addEventListener('click', () => {
    document.getElementById('novo-veiculo-modal-overlay').hidden = true;
  });
  document.getElementById('novo-veiculo-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'novo-veiculo-modal-overlay') {
      document.getElementById('novo-veiculo-modal-overlay').hidden = true;
    }
  });
  document.getElementById('novo-veiculo-form').addEventListener('submit', enviarNovoVeiculo);
}

function abrirModalNovoVeiculo() {
  document.getElementById('novo-veiculo-form').reset();
  document.getElementById('veiculo-form-modelo').value = 'Fiat Mobi';
  document.getElementById('veiculo-form-km').value = '0';
  document.getElementById('novo-veiculo-modal-erro').classList.remove('visible');
  document.getElementById('novo-veiculo-modal-overlay').hidden = false;
}

async function enviarNovoVeiculo(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('novo-veiculo-modal-erro');
  const botao = document.getElementById('novo-veiculo-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    placa: document.getElementById('veiculo-form-placa').value,
    apelido: document.getElementById('veiculo-form-apelido').value || null,
    modelo: document.getElementById('veiculo-form-modelo').value,
    ano: document.getElementById('veiculo-form-ano').value ? Number(document.getElementById('veiculo-form-ano').value) : null,
    km_atual: Number(document.getElementById('veiculo-form-km').value),
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';

  try {
    await Shell.chamarApi('/veiculos-dados', { method: 'POST', body: corpo });
    document.getElementById('novo-veiculo-modal-overlay').hidden = true;
    carregarVeiculos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar o veículo agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar veículo';
  }
}

montarModalNovoVeiculo();
document.getElementById('btn-novo-veiculo').addEventListener('click', abrirModalNovoVeiculo);
if (auth.papel !== 'escritorio') {
  document.getElementById('btn-novo-veiculo').hidden = true;
}

carregarVeiculos();
