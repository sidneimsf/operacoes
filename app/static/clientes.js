const auth = Shell.montar('clientes', 'Clientes');

let empresas = [];
let clientes = [];
let empresaSelecionada = null;

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
  const listaFiltrada = empresaSelecionada === null
    ? clientes
    : clientes.filter((c) => c.empresa_id === empresaSelecionada);

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

async function iniciar() {
  try {
    empresas = await Shell.chamarApi('/empresas');
    if (empresas === null) return;

    clientes = await Shell.chamarApi('/clientes-dados');
    if (clientes === null) return;

    renderizarChips();
    renderizarClientes();
  } catch (erro) {
    document.getElementById('lista-clientes').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
