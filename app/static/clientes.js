const auth = Shell.montar('clientes', 'Clientes');

let empresas = [];
let clientes = [];
let empresaSelecionada = null;
let termoBusca = '';
let supervisoresCache = [];

function renderizarChips() {
  const container = document.getElementById('chips-empresas');
  container.innerHTML = '';

  const chipTodos = document.createElement('button');
  chipTodos.className = 'chip' + (empresaSelecionada === null ? ' active' : '');
  chipTodos.textContent = `Todos · ${clientes.length}`;
  chipTodos.addEventListener('click', () => {
    empresaSelecionada = null;
    renderizarChips();
    renderizarClientes();
  });
  container.appendChild(chipTodos);

  empresas.forEach((empresa) => {
    const total = clientes.filter((c) => c.empresa_id === empresa.id).length;
    const chip = document.createElement('button');
    chip.className = 'chip' + (empresaSelecionada === empresa.id ? ' active' : '');
    chip.textContent = `${empresa.nome} · ${total}`;
    chip.addEventListener('click', () => {
      empresaSelecionada = empresa.id;
      renderizarChips();
      renderizarClientes();
    });
    container.appendChild(chip);
  });
}

function renderizarClientes() {
  const container = document.getElementById('lista-clientes');
  let listaFiltrada = empresaSelecionada === null
    ? clientes
    : clientes.filter((c) => c.empresa_id === empresaSelecionada);

  if (termoBusca.trim()) {
    const termo = termoBusca.trim().toLowerCase();
    listaFiltrada = listaFiltrada.filter((c) => c.nome.toLowerCase().includes(termo));
  }

  if (listaFiltrada.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum cliente encontrado.</div>';
    return;
  }

  container.innerHTML = '';
  listaFiltrada.forEach((cliente) => {
    const linha = document.createElement('a');
    linha.className = 'cliente-row';
    linha.href = `/cliente-detalhe?id=${cliente.id}`;
    linha.innerHTML = `
      <span>${cliente.nome}</span>
      <span class="cnpj">${cliente.cnpj ?? '—'}</span>
    `;
    container.appendChild(linha);
  });
}

function montarModalCliente() {
  const html = `
    <div class="modal-overlay" id="cliente-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo cliente</h3>
          <button class="modal-close" id="cliente-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="cliente-form">
          <div class="field">
            <label for="cliente-form-empresa">Empresa</label>
            <select id="cliente-form-empresa" required></select>
          </div>
          <div class="field">
            <label for="cliente-form-nome">Nome do cliente</label>
            <input type="text" id="cliente-form-nome" required>
          </div>
          <div class="field">
            <label for="cliente-form-cnpj">CNPJ (opcional)</label>
            <input type="text" id="cliente-form-cnpj" placeholder="00.000.000/0001-00">
          </div>
          <div class="field">
            <label for="cliente-form-municipio">Município (opcional)</label>
            <input type="text" id="cliente-form-municipio">
          </div>
          <div class="field">
            <label for="cliente-form-endereco">Endereço (opcional)</label>
            <input type="text" id="cliente-form-endereco">
          </div>
          <div class="field">
            <label for="cliente-form-bairro">Bairro (opcional)</label>
            <input type="text" id="cliente-form-bairro">
          </div>
          <div class="field">
            <label for="cliente-form-cidade">Cidade (opcional)</label>
            <input type="text" id="cliente-form-cidade">
          </div>
          <div class="field">
            <label for="cliente-form-responsavel-nome">Responsável no local (opcional)</label>
            <input type="text" id="cliente-form-responsavel-nome">
          </div>
          <div class="field">
            <label for="cliente-form-responsavel-telefone">Telefone do responsável (opcional)</label>
            <input type="text" id="cliente-form-responsavel-telefone">
          </div>
          <div class="field">
            <label for="cliente-form-senha-acesso">Senha de acesso ao local (opcional)</label>
            <input type="text" id="cliente-form-senha-acesso">
          </div>
          <div class="field">
            <label for="cliente-form-chave-acesso">Chave / tag / cartão de acesso (opcional)</label>
            <input type="text" id="cliente-form-chave-acesso">
          </div>
          <div class="field">
            <label for="cliente-form-supervisor">Supervisor responsável (opcional)</label>
            <select id="cliente-form-supervisor"><option value="">Sem supervisor definido</option></select>
          </div>
          <div class="error-message" id="cliente-modal-erro"></div>
          <button type="submit" class="btn-primary" id="cliente-modal-enviar">Criar cliente</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('cliente-modal-fechar').addEventListener('click', fecharModalCliente);
  document.getElementById('cliente-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'cliente-modal-overlay') fecharModalCliente();
  });
  document.getElementById('cliente-form').addEventListener('submit', enviarNovoCliente);
}

function abrirModalCliente() {
  document.getElementById('cliente-form').reset();
  document.getElementById('cliente-modal-erro').classList.remove('visible');
  document.getElementById('cliente-form-empresa').innerHTML = empresas
    .map((e) => `<option value="${e.id}">${e.nome}</option>`)
    .join('');
  document.getElementById('cliente-form-supervisor').innerHTML =
    '<option value="">Sem supervisor definido</option>' +
    supervisoresCache.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');
  document.getElementById('cliente-modal-overlay').hidden = false;
}

function fecharModalCliente() {
  document.getElementById('cliente-modal-overlay').hidden = true;
}

async function enviarNovoCliente(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('cliente-modal-erro');
  const botao = document.getElementById('cliente-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    empresa_id: Number(document.getElementById('cliente-form-empresa').value),
    nome: document.getElementById('cliente-form-nome').value,
    cnpj: document.getElementById('cliente-form-cnpj').value || null,
    municipio: document.getElementById('cliente-form-municipio').value || null,
    endereco: document.getElementById('cliente-form-endereco').value || null,
    bairro: document.getElementById('cliente-form-bairro').value || null,
    cidade: document.getElementById('cliente-form-cidade').value || null,
    responsavel_nome: document.getElementById('cliente-form-responsavel-nome').value || null,
    responsavel_telefone: document.getElementById('cliente-form-responsavel-telefone').value || null,
    senha_acesso: document.getElementById('cliente-form-senha-acesso').value || null,
    chave_acesso: document.getElementById('cliente-form-chave-acesso').value || null,
    supervisor_id: document.getElementById('cliente-form-supervisor').value ? Number(document.getElementById('cliente-form-supervisor').value) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';

  try {
    await Shell.chamarApi('/clientes-dados', { method: 'POST', body: corpo });
    fecharModalCliente();
    iniciar();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar o cliente agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar cliente';
  }
}

async function iniciar() {
  try {
    empresas = await Shell.chamarApi('/empresas');
    if (empresas === null) return;

    supervisoresCache = await Shell.chamarApi('/supervisores');

    clientes = await Shell.chamarApi('/clientes-dados');
    if (clientes === null) return;

    renderizarChips();
    renderizarClientes();
  } catch (erro) {
    document.getElementById('lista-clientes').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

montarModalCliente();
document.getElementById('btn-novo-cliente').addEventListener('click', abrirModalCliente);
if (auth.papel !== 'escritorio') {
  document.getElementById('btn-novo-cliente').hidden = true;
}

document.getElementById('busca-cliente').addEventListener('input', (evento) => {
  termoBusca = evento.target.value;
  renderizarClientes();
});

iniciar();
