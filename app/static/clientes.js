const auth = Shell.montar('clientes', 'Clientes');

let empresas = [];
let clientes = [];
let empresaSelecionada = null;
let termoBusca = '';
let bairroSelecionado = '';
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

// Agrupa grafias diferentes do mesmo bairro ("Centro", "CENTRO", "Centro ") numa opcao so
function chaveBairro(bairro) {
  return (bairro || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function renderizarFiltroBairro() {
  const select = document.getElementById('filtro-bairro');
  const bairros = new Map();
  clientes.forEach((c) => {
    const chave = chaveBairro(c.bairro);
    if (!chave) return;
    if (!bairros.has(chave)) bairros.set(chave, { nome: c.bairro.trim(), total: 0 });
    bairros.get(chave).total += 1;
  });
  const ordenados = [...bairros.entries()].sort((a, b) => a[1].nome.localeCompare(b[1].nome, 'pt-BR'));
  const semBairro = clientes.filter((c) => !chaveBairro(c.bairro)).length;

  select.innerHTML = '<option value="">Todos os bairros</option>'
    + ordenados.map(([chave, b]) => `<option value="${chave}">${b.nome} · ${b.total}</option>`).join('')
    + (semBairro ? `<option value="__sem__">Sem bairro cadastrado · ${semBairro}</option>` : '');
  select.value = bairroSelecionado;
  if (select.value !== bairroSelecionado) bairroSelecionado = '';
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

  if (bairroSelecionado === '__sem__') {
    listaFiltrada = listaFiltrada.filter((c) => !chaveBairro(c.bairro));
  } else if (bairroSelecionado) {
    listaFiltrada = listaFiltrada.filter((c) => chaveBairro(c.bairro) === bairroSelecionado);
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
      <span>${cliente.nome}${cliente.bairro ? ` <span class="cliente-bairro">· ${cliente.bairro}</span>` : ''}</span>
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
            <label for="cliente-form-uf">UF (opcional)</label>
            <input type="text" id="cliente-form-uf" maxlength="2" placeholder="SC">
          </div>
          <div class="field">
            <label for="cliente-form-cep">CEP (opcional)</label>
            <input type="text" id="cliente-form-cep" placeholder="00000-000">
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
    uf: document.getElementById('cliente-form-uf').value || null,
    cep: document.getElementById('cliente-form-cep').value || null,
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
    renderizarFiltroBairro();
    renderizarClientes();
  } catch (erro) {
    document.getElementById('lista-clientes').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

// ---------- Importar enderecos pela planilha de dados cadastrais ----------

const NOMES_CAMPO_ENDERECO = { endereco: 'Endereço', bairro: 'Bairro', cidade: 'Cidade', uf: 'UF', cep: 'CEP', cnpj: 'CNPJ' };
const SEMELHANCA_MARCADA = 0.85; // nomes parecidos abaixo disso vem desmarcados, pra conferir

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

async function enviarPlanilha(formData) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return null;
  const resposta = await fetch('/clientes-dados/importar-enderecos', {
    method: 'POST',
    headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    body: formData,
  });
  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error('Falha ao importar a planilha');
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }
  return resposta.json();
}

function montarModalImportacao() {
  const html = `
    <div class="modal-overlay" id="importar-modal-overlay" hidden>
      <div class="modal modal-largo">
        <div class="modal-header">
          <h3>Importar endereços (Excel)</h3>
          <button class="modal-close" id="importar-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <p class="importar-ajuda">Envie a planilha de dados cadastrais (colunas Empresa, Cliente, CNPJ, CEP, Endereço, Bairro, Cidade e UF). Nada é alterado antes de você conferir.</p>
        <div class="field">
          <input type="file" id="importar-arquivo" accept=".xlsx">
        </div>
        <div class="error-message" id="importar-erro"></div>
        <button type="button" class="btn-primary" id="importar-conferir">Conferir planilha</button>
        <div id="importar-conferencia"></div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);
  document.getElementById('importar-modal-fechar').addEventListener('click', fecharModalImportacao);
  document.getElementById('importar-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'importar-modal-overlay') fecharModalImportacao();
  });
  document.getElementById('importar-conferir').addEventListener('click', conferirPlanilha);
  document.getElementById('importar-conferencia').addEventListener('click', (evento) => {
    if (evento.target.id === 'importar-aplicar') aplicarPlanilha();
  });
}

function abrirModalImportacao() {
  document.getElementById('importar-arquivo').value = '';
  document.getElementById('importar-erro').classList.remove('visible');
  document.getElementById('importar-conferencia').innerHTML = '';
  document.getElementById('importar-conferir').hidden = false;
  document.getElementById('importar-modal-overlay').hidden = false;
}

function fecharModalImportacao() {
  document.getElementById('importar-modal-overlay').hidden = true;
}

function mostrarErroImportacao(texto) {
  const erroBox = document.getElementById('importar-erro');
  erroBox.textContent = texto;
  erroBox.classList.add('visible');
}

function formDataDaPlanilha() {
  const arquivo = document.getElementById('importar-arquivo').files[0];
  if (!arquivo) return null;
  const formData = new FormData();
  formData.append('arquivo', arquivo);
  return formData;
}

function textoMudancas(mudancas) {
  const campos = Object.keys(mudancas);
  if (campos.length === 0) return '<span class="importar-detalhe">já está igual</span>';
  return campos
    .map((campo) => {
      const [atual, novo] = mudancas[campo];
      return `<div><b>${NOMES_CAMPO_ENDERECO[campo] || campo}:</b> ${atual ? `<s>${escaparHtml(atual)}</s> → ` : ''}${escaparHtml(novo)}</div>`;
    })
    .join('');
}

async function conferirPlanilha() {
  document.getElementById('importar-erro').classList.remove('visible');
  const formData = formDataDaPlanilha();
  if (!formData) {
    mostrarErroImportacao('Escolha o arquivo da planilha primeiro.');
    return;
  }
  const botao = document.getElementById('importar-conferir');
  botao.disabled = true;
  botao.textContent = 'Conferindo...';
  try {
    const resultado = await enviarPlanilha(formData);
    if (resultado) renderizarConferencia(resultado);
  } catch (erro) {
    mostrarErroImportacao(erro.detalhe || 'Não foi possível ler a planilha agora.');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Conferir planilha';
  }
}

function renderizarConferencia(resultado) {
  const comMudanca = resultado.casadas.filter((c) => Object.keys(c.mudancas).length > 0);
  const linhas = resultado.casadas
    .map((c) => {
      const temMudanca = Object.keys(c.mudancas).length > 0;
      const marcada = temMudanca && (c.metodo !== 'parecido' || c.semelhanca >= SEMELHANCA_MARCADA);
      const comoAchou = { nome: 'nome igual', cnpj: 'mesmo CNPJ', outra_empresa: 'nome igual, cadastrado em outra empresa' }[c.metodo]
        || `nome parecido (${Math.round(c.semelhanca * 100)}%)`;
      return `
        <tr class="${c.metodo === 'parecido' ? 'importar-parecido' : ''}">
          <td><input type="checkbox" data-linha="${escaparHtml(c.linha_id)}" ${marcada ? 'checked' : ''} ${temMudanca ? '' : 'disabled'}></td>
          <td>${escaparHtml(c.planilha_nome)}<div class="importar-detalhe">${escaparHtml(c.empresa)}</div></td>
          <td>${escaparHtml(c.cliente_nome)}<div class="importar-detalhe">${comoAchou}</div></td>
          <td class="importar-mudancas">${textoMudancas(c.mudancas)}</td>
        </tr>
      `;
    })
    .join('');

  const naoEncontradas = resultado.nao_encontradas
    .map((n) => `<li>${escaparHtml(n.planilha_nome)} <span class="importar-detalhe">(${escaparHtml(n.empresa)}) — ${escaparHtml(n.motivo)}</span></li>`)
    .join('');
  const foraDaPlanilha = resultado.clientes_fora_da_planilha.map((nome) => `<li>${escaparHtml(nome)}</li>`).join('');

  document.getElementById('importar-conferir').hidden = true;
  document.getElementById('importar-conferencia').innerHTML = `
    <div class="importar-resumo">
      ${resultado.total_linhas} clientes na planilha · <b>${resultado.casadas.length}</b> encontrados no sistema
      (${comMudanca.length} com endereço a completar) · <b>${resultado.nao_encontradas.length}</b> não encontrados
    </div>
    <p class="importar-ajuda">Confira principalmente as linhas em amarelo (nome parecido, não igual). Desmarque o que estiver errado.</p>
    <div class="importar-tabela">
      <table>
        <thead><tr><th></th><th>Na planilha</th><th>No sistema</th><th>O que muda</th></tr></thead>
        <tbody>${linhas}</tbody>
      </table>
    </div>
    ${naoEncontradas ? `<details class="importar-lista"><summary>Não encontrados no sistema · ${resultado.nao_encontradas.length}</summary><ul>${naoEncontradas}</ul></details>` : ''}
    ${foraDaPlanilha ? `<details class="importar-lista"><summary>Clientes do sistema que não estão na planilha · ${resultado.clientes_fora_da_planilha.length}</summary><ul>${foraDaPlanilha}</ul></details>` : ''}
    <button type="button" class="btn-primary" id="importar-aplicar">Aplicar endereços marcados</button>
  `;
}

async function aplicarPlanilha() {
  document.getElementById('importar-erro').classList.remove('visible');
  const marcadas = [...document.querySelectorAll('#importar-conferencia input[data-linha]:checked')].map((c) => c.dataset.linha);
  if (marcadas.length === 0) {
    mostrarErroImportacao('Nenhuma linha marcada para aplicar.');
    return;
  }
  const formData = formDataDaPlanilha();
  if (!formData) return;
  formData.append('aplicar', 'true');
  formData.append('linhas_aceitas', marcadas.join(','));

  const botao = document.getElementById('importar-aplicar');
  botao.disabled = true;
  botao.textContent = 'Aplicando...';
  try {
    const resultado = await enviarPlanilha(formData);
    if (!resultado) return;
    const minutos = Math.max(1, Math.ceil((resultado.localizando * 3) / 60));
    document.getElementById('importar-conferencia').innerHTML = `
      <div class="importar-resumo">
        <b>${resultado.atualizados}</b> clientes com endereço atualizado.
        ${resultado.localizando ? `O sistema está localizando ${resultado.localizando} clientes no mapa em segundo plano. Leva até uns ${minutos} minutos. Pode fechar esta janela e continuar usando o sistema.` : ''}
      </div>
    `;
    clientes = await Shell.chamarApi('/clientes-dados');
    renderizarChips();
    renderizarFiltroBairro();
    renderizarClientes();
  } catch (erro) {
    mostrarErroImportacao(erro.detalhe || 'Não foi possível aplicar agora.');
    botao.disabled = false;
    botao.textContent = 'Aplicar endereços marcados';
  }
}

async function liberarImportacaoSeTiverPermissao() {
  try {
    const permissoes = await Shell.chamarApi('/minhas-permissoes');
    if (permissoes && permissoes.criar_cliente) {
      document.getElementById('btn-importar-enderecos').hidden = false;
    }
  } catch (erro) {
    // sem permissao conhecida, o botao continua escondido
  }
}

montarModalImportacao();
document.getElementById('btn-importar-enderecos').addEventListener('click', abrirModalImportacao);
liberarImportacaoSeTiverPermissao();

montarModalCliente();
document.getElementById('btn-novo-cliente').addEventListener('click', abrirModalCliente);
if (auth.papel !== 'escritorio') {
  document.getElementById('btn-novo-cliente').hidden = true;
}

document.getElementById('busca-cliente').addEventListener('input', (evento) => {
  termoBusca = evento.target.value;
  renderizarClientes();
});

document.getElementById('filtro-bairro').addEventListener('change', (evento) => {
  bairroSelecionado = evento.target.value;
  renderizarClientes();
});

iniciar();
