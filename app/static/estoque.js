const auth = Shell.montar('estoque', 'Estoque');

let empresas = [];
let itens = [];
let colaboradoresCache = [];
let empresaSelecionada = null;
let itemEmAcao = null;

function renderizarChips() {
  const container = document.getElementById('chips-empresas-estoque');
  container.innerHTML = '';

  const chipTodos = document.createElement('button');
  chipTodos.className = 'chip' + (empresaSelecionada === null ? ' active' : '');
  chipTodos.textContent = `Todos · ${itens.length}`;
  chipTodos.addEventListener('click', () => {
    empresaSelecionada = null;
    renderizarChips();
    renderizarLista();
  });
  container.appendChild(chipTodos);

  const totalGeral = itens.filter((i) => i.empresa_id === null).length;
  const chipGeral = document.createElement('button');
  chipGeral.className = 'chip' + (empresaSelecionada === 'geral' ? ' active' : '');
  chipGeral.textContent = `Geral · ${totalGeral}`;
  chipGeral.addEventListener('click', () => {
    empresaSelecionada = 'geral';
    renderizarChips();
    renderizarLista();
  });
  container.appendChild(chipGeral);

  empresas.forEach((empresa) => {
    const total = itens.filter((i) => i.empresa_id === empresa.id).length;
    const chip = document.createElement('button');
    chip.className = 'chip' + (empresaSelecionada === empresa.id ? ' active' : '');
    chip.textContent = `${empresa.nome} · ${total}`;
    chip.addEventListener('click', () => {
      empresaSelecionada = empresa.id;
      renderizarChips();
      renderizarLista();
    });
    container.appendChild(chip);
  });
}

function renderizarLista() {
  const container = document.getElementById('lista-estoque');
  let filtrados = itens;
  if (empresaSelecionada === 'geral') {
    filtrados = itens.filter((i) => i.empresa_id === null);
  } else if (empresaSelecionada !== null) {
    filtrados = itens.filter((i) => i.empresa_id === empresaSelecionada);
  }

  if (filtrados.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum item cadastrado.</div>';
    return;
  }

  const porPeca = {};
  filtrados.forEach((i) => {
    const chave = `${i.empresa_nome} · ${i.tipo_peca}`;
    if (!porPeca[chave]) porPeca[chave] = [];
    porPeca[chave].push(i);
  });

  container.innerHTML = Object.entries(porPeca)
    .map(([grupo, lista]) => {
      const linhas = lista
        .map(
          (i) => `
        <tr>
          <td>${i.tamanho}</td>
          <td><strong>${i.quantidade_atual}</strong></td>
          <td style="white-space: nowrap;">
            <button class="btn-ghost btn-estoque-entrada" data-item-id="${i.id}" style="padding: 4px 8px; font-size: 11.5px;">+ Entrada</button>
            <button class="btn-ghost btn-estoque-saida" data-item-id="${i.id}" style="padding: 4px 8px; font-size: 11.5px;">- Saída</button>
            <button class="btn-ghost btn-estoque-historico" data-item-id="${i.id}" style="padding: 4px 8px; font-size: 11.5px;">Histórico</button>
            <button class="btn-ghost btn-estoque-editar" data-item-id="${i.id}" style="padding: 4px 8px; font-size: 11.5px;">Editar</button>
            <button class="btn-ghost btn-estoque-excluir" data-item-id="${i.id}" style="padding: 4px 8px; font-size: 11.5px;">Excluir</button>
          </td>
        </tr>
      `
        )
        .join('');

      return `
        <div style="margin-bottom: 24px;">
          <div class="section-title" style="margin-bottom: 8px;">${grupo}</div>
          <table class="table-list">
            <thead><tr><th>Tamanho</th><th>Quantidade</th><th>Ações</th></tr></thead>
            <tbody>${linhas}</tbody>
          </table>
        </div>
      `;
    })
    .join('');
}

async function carregarTudo() {
  const container = document.getElementById('lista-estoque');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    empresas = await Shell.chamarApi('/empresas');
    if (empresas === null) return;
    itens = await Shell.chamarApi('/estoque-dados');
    if (itens === null) return;
    if (colaboradoresCache.length === 0) {
      colaboradoresCache = await Shell.chamarApi('/colaboradores-dados');
    }
    renderizarChips();
    renderizarLista();
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

function montarModalNovoItem() {
  const html = `
    <div class="modal-overlay" id="novo-item-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo item de estoque</h3>
          <button class="modal-close" id="novo-item-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="novo-item-form">
          <div class="field">
            <label for="item-form-empresa">Empresa (deixe "Geral" se a peça não tem logo)</label>
            <select id="item-form-empresa"></select>
          </div>
          <div class="field">
            <label for="item-form-peca">Tipo de peça</label>
            <input type="text" id="item-form-peca" placeholder="Ex: CAMISETA, CALÇA, SAPATO" required>
          </div>
          <div class="field">
            <label for="item-form-tamanho">Tamanho</label>
            <input type="text" id="item-form-tamanho" placeholder="Ex: P, M, G, GG, ou número (calçado)" required>
          </div>
          <div class="field">
            <label for="item-form-quantidade">Quantidade inicial</label>
            <input type="number" id="item-form-quantidade" min="0" value="0" required>
          </div>
          <div class="error-message" id="novo-item-modal-erro"></div>
          <button type="submit" class="btn-primary" id="novo-item-modal-enviar">Criar item</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('novo-item-modal-fechar').addEventListener('click', () => {
    document.getElementById('novo-item-modal-overlay').hidden = true;
  });
  document.getElementById('novo-item-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'novo-item-modal-overlay') document.getElementById('novo-item-modal-overlay').hidden = true;
  });
  document.getElementById('novo-item-form').addEventListener('submit', enviarNovoItem);
}

function abrirModalNovoItem() {
  document.getElementById('novo-item-form').reset();
  document.getElementById('item-form-empresa').innerHTML =
    '<option value="">Geral (sem logo, compartilhado)</option>' +
    empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');
  document.getElementById('novo-item-modal-erro').classList.remove('visible');
  document.getElementById('novo-item-modal-overlay').hidden = false;
}

async function enviarNovoItem(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('novo-item-modal-erro');
  const botao = document.getElementById('novo-item-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    empresa_id: document.getElementById('item-form-empresa').value ? Number(document.getElementById('item-form-empresa').value) : null,
    tipo_peca: document.getElementById('item-form-peca').value,
    tamanho: document.getElementById('item-form-tamanho').value,
    quantidade_inicial: Number(document.getElementById('item-form-quantidade').value),
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';
  try {
    await Shell.chamarApi('/estoque-dados', { method: 'POST', body: corpo });
    document.getElementById('novo-item-modal-overlay').hidden = true;
    carregarTudo();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar item';
  }
}

function montarModalMovimento() {
  const html = `
    <div class="modal-overlay" id="movimento-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="movimento-modal-titulo">Registrar movimento</h3>
          <button class="modal-close" id="movimento-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="movimento-form">
          <div class="field">
            <label for="movimento-quantidade">Quantidade</label>
            <input type="number" id="movimento-quantidade" min="1" value="1" required>
          </div>
          <div class="field" id="campo-movimento-colaborador">
            <label for="movimento-colaborador">Entregue para (opcional)</label>
            <select id="movimento-colaborador"><option value="">Não informado</option></select>
          </div>
          <div class="field">
            <label for="movimento-motivo">Motivo / observação (opcional)</label>
            <input type="text" id="movimento-motivo" placeholder="Ex: Compra mensal, admissão de novo colaborador...">
          </div>
          <div class="error-message" id="movimento-modal-erro"></div>
          <button type="submit" class="btn-primary" id="movimento-modal-enviar">Confirmar</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('movimento-modal-fechar').addEventListener('click', () => {
    document.getElementById('movimento-modal-overlay').hidden = true;
  });
  document.getElementById('movimento-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'movimento-modal-overlay') document.getElementById('movimento-modal-overlay').hidden = true;
  });
  document.getElementById('movimento-form').addEventListener('submit', enviarMovimento);
}

let tipoMovimentoAtual = null;

function abrirModalMovimento(itemId, tipo) {
  itemEmAcao = itemId;
  tipoMovimentoAtual = tipo;
  const item = itens.find((i) => i.id === Number(itemId));
  document.getElementById('movimento-modal-titulo').textContent =
    tipo === 'entrada' ? `+ Entrada · ${item.tipo_peca} ${item.tamanho}` : `- Saída · ${item.tipo_peca} ${item.tamanho}`;
  document.getElementById('movimento-form').reset();
  document.getElementById('campo-movimento-colaborador').hidden = tipo !== 'saida';
  document.getElementById('movimento-colaborador').innerHTML =
    '<option value="">Não informado</option>' + colaboradoresCache.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  document.getElementById('movimento-modal-erro').classList.remove('visible');
  document.getElementById('movimento-modal-overlay').hidden = false;
}

async function enviarMovimento(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('movimento-modal-erro');
  const botao = document.getElementById('movimento-modal-enviar');
  erroBox.classList.remove('visible');

  const colaboradorValor = document.getElementById('movimento-colaborador').value;
  const corpo = {
    tipo: tipoMovimentoAtual,
    quantidade: Number(document.getElementById('movimento-quantidade').value),
    motivo: document.getElementById('movimento-motivo').value || null,
    colaborador_id: colaboradorValor ? Number(colaboradorValor) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    await Shell.chamarApi(`/estoque-dados/${itemEmAcao}/movimentos`, { method: 'POST', body: corpo });
    document.getElementById('movimento-modal-overlay').hidden = true;
    carregarTudo();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível registrar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Confirmar';
  }
}

function montarModalHistorico() {
  const html = `
    <div class="modal-overlay" id="historico-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="historico-modal-titulo">Histórico</h3>
          <button class="modal-close" id="historico-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <div id="historico-modal-conteudo"><div class="loading-state">Carregando...</div></div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('historico-modal-fechar').addEventListener('click', () => {
    document.getElementById('historico-modal-overlay').hidden = true;
  });
  document.getElementById('historico-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'historico-modal-overlay') document.getElementById('historico-modal-overlay').hidden = true;
  });
}

async function abrirModalHistorico(itemId) {
  const item = itens.find((i) => i.id === Number(itemId));
  document.getElementById('historico-modal-titulo').textContent = `Histórico · ${item.tipo_peca} ${item.tamanho}`;
  document.getElementById('historico-modal-overlay').hidden = false;
  const conteudo = document.getElementById('historico-modal-conteudo');
  conteudo.innerHTML = '<div class="loading-state">Carregando...</div>';

  try {
    const movimentos = await Shell.chamarApi(`/estoque-dados/${itemId}/movimentos`);
    if (movimentos.length === 0) {
      conteudo.innerHTML = '<div class="empty-state">Nenhuma movimentação registrada ainda.</div>';
      return;
    }
    const linhas = movimentos
      .map((m) => {
        const data = new Date(m.criado_em).toLocaleDateString('pt-BR');
        const sinal = m.tipo === 'entrada' ? '+' : '-';
        return `
        <tr>
          <td>${data}</td>
          <td>${sinal}${m.quantidade}</td>
          <td>${m.colaborador_nome || '—'}</td>
          <td>${m.motivo || '—'}</td>
          <td>${m.registrado_por}</td>
        </tr>
      `;
      })
      .join('');
    conteudo.innerHTML = `
      <table class="table-list">
        <thead><tr><th>Data</th><th>Qtd</th><th>Para</th><th>Motivo</th><th>Registrado por</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>
    `;
  } catch (erro) {
    conteudo.innerHTML = '<div class="empty-state">Não foi possível carregar o histórico agora.</div>';
  }
}

async function editarItem(itemId) {
  const item = itens.find((i) => i.id === Number(itemId));
  const novoTipo = prompt('Tipo de peça:', item.tipo_peca);
  if (novoTipo === null) return;
  const novoTamanho = prompt('Tamanho:', item.tamanho);
  if (novoTamanho === null) return;

  try {
    await Shell.chamarApi(`/estoque-dados/${itemId}`, {
      method: 'PATCH',
      body: { tipo_peca: novoTipo, tamanho: novoTamanho },
    });
    carregarTudo();
  } catch (erro) {
    alert(erro.detalhe || 'Não foi possível editar agora.');
  }
}

async function excluirItem(itemId) {
  if (!confirm('Excluir esse item de estoque? O histórico de movimentações também será apagado.')) return;
  try {
    await Shell.chamarApi(`/estoque-dados/${itemId}`, { method: 'DELETE' });
    carregarTudo();
  } catch (erro) {
    alert('Não foi possível excluir agora.');
  }
}

montarModalNovoItem();
montarModalMovimento();
montarModalHistorico();

document.getElementById('btn-novo-item-estoque').addEventListener('click', abrirModalNovoItem);

document.getElementById('lista-estoque').addEventListener('click', (evento) => {
  const btnEntrada = evento.target.closest('.btn-estoque-entrada');
  if (btnEntrada) return abrirModalMovimento(btnEntrada.dataset.itemId, 'entrada');
  const btnSaida = evento.target.closest('.btn-estoque-saida');
  if (btnSaida) return abrirModalMovimento(btnSaida.dataset.itemId, 'saida');
  const btnHistorico = evento.target.closest('.btn-estoque-historico');
  if (btnHistorico) return abrirModalHistorico(btnHistorico.dataset.itemId);
  const btnEditar = evento.target.closest('.btn-estoque-editar');
  if (btnEditar) return editarItem(btnEditar.dataset.itemId);
  const btnExcluir = evento.target.closest('.btn-estoque-excluir');
  if (btnExcluir) return excluirItem(btnExcluir.dataset.itemId);
});

carregarTudo();
