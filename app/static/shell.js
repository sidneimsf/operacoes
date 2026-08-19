const Shell = (() => {
  const ICONS = {
    dashboard: '<path d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6V11h-6v9Zm0-16v5h6V4h-6Z"/>',
    clientes: '<path d="M4 21V6l7-3 7 3v15M4 21h16M4 21v-2M20 21v-2M9 21v-4h4v4M9 10h.01M13 10h.01M9 14h.01M13 14h.01"/>',
    colaboradores: '<path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM21 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    ponto: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    documentos: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
    uniformes: '<path d="m6 4-3 3 3 4h2v9h8v-9h2l3-4-3-3-4 2h-2L6 4Z"/>',
    ocorrencias: '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17h.01"/>',
    avisos: '<path d="M3 11v3a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1Z"/><path d="M16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14"/>',
    usuarios: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
  };

  const NAV_ITEMS = [
    { key: 'dashboard', label: 'Painel', href: '/dashboard' },
    { key: 'clientes', label: 'Clientes', href: '/clientes' },
    { key: 'colaboradores', label: 'Colaboradores', href: '/colaboradores' },
    { key: 'ocorrencias', label: 'Ocorrências', href: '/ocorrencias' },
    { key: 'avisos', label: 'Avisos', href: '/avisos' },
    { key: 'usuarios', label: 'Usuários', href: '/usuarios', papeis: ['escritorio'] },
  ];

  function autenticacao() {
    const bruto = localStorage.getItem('operacoes_auth');
    if (!bruto) {
      window.location.href = '/login';
      return null;
    }
    return JSON.parse(bruto);
  }

  function sair() {
    localStorage.removeItem('operacoes_auth');
    window.location.href = '/login';
  }

  async function chamarApi(caminho, opcoes = {}) {
    const auth = autenticacao();
    if (!auth) return null;

    const cabecalhos = { Authorization: `Bearer ${auth.access_token}` };
    if (opcoes.body) {
      cabecalhos['Content-Type'] = 'application/json';
    }

    const resposta = await fetch(caminho, {
      method: opcoes.method || 'GET',
      headers: cabecalhos,
      body: opcoes.body ? JSON.stringify(opcoes.body) : undefined,
    });

    if (resposta.status === 401) {
      sair();
      return null;
    }

    if (!resposta.ok) {
      const erro = new Error(`Falha ao chamar ${caminho}: ${resposta.status}`);
      erro.status = resposta.status;
      try {
        erro.detalhe = (await resposta.json()).detail;
      } catch (_) {
        // resposta sem corpo JSON, sem problema
      }
      throw erro;
    }

    return resposta.json();
  }

  function icone(chave) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONS[chave] || ''}</svg>`;
  }

  function montar(paginaAtiva, tituloTopbar) {
    const auth = autenticacao();
    if (!auth) return null;

    const itensVisiveis = NAV_ITEMS.filter((item) => !item.papeis || item.papeis.includes(auth.papel));

    const linksHtml = itensVisiveis
      .map((item) => `
        <a class="nav-item${item.key === paginaAtiva ? ' active' : ''}" href="${item.href}">
          ${icone(item.key)}
          <span>${item.label}</span>
        </a>
      `)
      .join('');

    const sidebarHtml = `
      <div class="sidebar">
        <div class="wordmark-block">
          <span class="wordmark">SolarSync</span>
          <div class="app-name">operações</div>
        </div>
        <nav class="sidebar-nav">${linksHtml}</nav>
      </div>
    `;

    const appShell = document.getElementById('app-shell');
    appShell.insertAdjacentHTML('afterbegin', sidebarHtml);

    document.getElementById('topbar-title').textContent = tituloTopbar;
    document.getElementById('topbar-title').insertAdjacentHTML(
      'afterend',
      '<button class="btn-primary btn-topbar" id="btn-abrir-chamado">+ Abrir chamado</button>'
    );

    const userInfoHtml = `
      <div class="user-info">
        <span id="user-nome">${auth.nome}</span>
        <span class="papel-badge">${auth.papel}</span>
        <button class="btn-ghost" id="btn-sair">Sair</button>
      </div>
    `;
    document.getElementById('topbar').insertAdjacentHTML('beforeend', userInfoHtml);
    document.getElementById('btn-sair').addEventListener('click', sair);

    montarModalChamado();
    document.getElementById('btn-abrir-chamado').addEventListener('click', abrirModalChamado);

    return auth;
  }

  function montarModalChamado() {
    const html = `
      <div class="modal-overlay" id="chamado-modal-overlay" hidden>
        <div class="modal">
          <div class="modal-header">
            <h3>Abrir chamado</h3>
            <button class="modal-close" id="chamado-modal-fechar" aria-label="Fechar">&times;</button>
          </div>
          <form id="chamado-form">
            <div class="field">
              <label for="chamado-empresa">Empresa</label>
              <select id="chamado-empresa" required></select>
            </div>
            <div class="field">
              <label for="chamado-cliente">Cliente</label>
              <select id="chamado-cliente" required disabled>
                <option value="">Selecione a empresa primeiro</option>
              </select>
            </div>
            <div class="field">
              <label for="chamado-tipo">Tipo de chamado</label>
              <select id="chamado-tipo" required></select>
            </div>
            <div class="field">
              <label for="chamado-responsavel">Responsável</label>
              <select id="chamado-responsavel" required></select>
            </div>
            <div class="field">
              <label for="chamado-descricao">Descrição</label>
              <textarea id="chamado-descricao" rows="4" required placeholder="Detalhe o que precisa ser feito..."></textarea>
            </div>
            <div class="error-message" id="chamado-modal-erro"></div>
            <button type="submit" class="btn-primary" id="chamado-modal-enviar">Abrir chamado</button>
          </form>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);

    document.getElementById('chamado-modal-fechar').addEventListener('click', fecharModalChamado);
    document.getElementById('chamado-modal-overlay').addEventListener('click', (evento) => {
      if (evento.target.id === 'chamado-modal-overlay') fecharModalChamado();
    });

    document.getElementById('chamado-empresa').addEventListener('change', async (evento) => {
      const empresaId = evento.target.value;
      const selectCliente = document.getElementById('chamado-cliente');
      selectCliente.disabled = true;
      selectCliente.innerHTML = '<option value="">Carregando...</option>';

      const clientes = await chamarApi(`/clientes-dados?empresa_id=${empresaId}`);
      selectCliente.innerHTML = clientes
        .map((c) => `<option value="${c.id}">${c.nome}</option>`)
        .join('');
      selectCliente.disabled = false;
    });

    document.getElementById('chamado-form').addEventListener('submit', enviarChamado);
  }

  async function abrirModalChamado() {
    const erroBox = document.getElementById('chamado-modal-erro');
    erroBox.classList.remove('visible');
    document.getElementById('chamado-form').reset();
    document.getElementById('chamado-cliente').innerHTML = '<option value="">Selecione a empresa primeiro</option>';
    document.getElementById('chamado-cliente').disabled = true;

    const [empresas, tiposEStatus, supervisores] = await Promise.all([
      chamarApi('/empresas'),
      chamarApi('/chamados-tipos'),
      chamarApi('/supervisores'),
    ]);

    const selectEmpresa = document.getElementById('chamado-empresa');
    selectEmpresa.innerHTML =
      '<option value="">Selecione...</option>' +
      empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

    const selectTipo = document.getElementById('chamado-tipo');
    selectTipo.innerHTML = tiposEStatus.tipos
      .map((t) => `<option value="${t.chave}">${t.label}</option>`)
      .join('');

    const selectResponsavel = document.getElementById('chamado-responsavel');
    selectResponsavel.innerHTML = supervisores
      .map((s) => `<option value="${s.id}">${s.nome}</option>`)
      .join('');

    document.getElementById('chamado-modal-overlay').hidden = false;
  }

  function fecharModalChamado() {
    document.getElementById('chamado-modal-overlay').hidden = true;
  }

  async function enviarChamado(evento) {
    evento.preventDefault();
    const erroBox = document.getElementById('chamado-modal-erro');
    const botao = document.getElementById('chamado-modal-enviar');
    erroBox.classList.remove('visible');

    const corpo = {
      cliente_id: Number(document.getElementById('chamado-cliente').value),
      tipo: document.getElementById('chamado-tipo').value,
      responsavel_id: Number(document.getElementById('chamado-responsavel').value),
      descricao: document.getElementById('chamado-descricao').value,
    };

    botao.disabled = true;
    botao.textContent = 'Abrindo...';

    try {
      await chamarApi('/chamados-dados', { method: 'POST', body: corpo });
      window.location.href = '/ocorrencias';
    } catch (erro) {
      erroBox.textContent = erro.detalhe || 'Não foi possível abrir o chamado. Tente novamente.';
      erroBox.classList.add('visible');
      botao.disabled = false;
      botao.textContent = 'Abrir chamado';
    }
  }

  return { montar, chamarApi, sair, autenticacao, icone };
})();
