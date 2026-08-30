const auth = Shell.montar('usuarios', 'Usuários');

async function carregarUsuarios() {
  const container = document.getElementById('lista-usuarios');
  container.innerHTML = '<div class="loading-state">Carregando usuários...</div>';

  try {
    const usuarios = await Shell.chamarApi('/usuarios-dados');
    if (usuarios === null) return;

    const linhas = usuarios
      .map(
        (u) => `
        <tr>
          <td>${u.nome}</td>
          <td>${u.email}</td>
          <td><span class="badge-papel">${u.papel}</span></td>
          <td>${u.ativo ? 'Ativo' : '<span class="badge-inativo">Inativo</span>'}</td>
        </tr>
      `
      )
      .join('');

    container.innerHTML = `
      <table class="table-list">
        <thead>
          <tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Status</th></tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    `;
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

function montarModalNovoUsuario() {
  const html = `
    <div class="modal-overlay" id="novo-usuario-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo usuário</h3>
          <button class="modal-close" id="novo-usuario-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="novo-usuario-form">
          <div class="field">
            <label for="usuario-form-nome">Nome</label>
            <input type="text" id="usuario-form-nome" required>
          </div>
          <div class="field">
            <label for="usuario-form-email">E-mail de login</label>
            <input type="email" id="usuario-form-email" required>
          </div>
          <div class="field">
            <label for="usuario-form-senha">Senha</label>
            <input type="text" id="usuario-form-senha" required placeholder="Pelo menos 4 caracteres">
          </div>
          <div class="field">
            <label for="usuario-form-papel">Papel</label>
            <select id="usuario-form-papel">
              <option value="supervisor">Supervisor</option>
              <option value="escritorio">Escritório</option>
            </select>
          </div>
          <div class="error-message" id="novo-usuario-modal-erro"></div>
          <button type="submit" class="btn-primary" id="novo-usuario-modal-enviar">Criar usuário</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('novo-usuario-modal-fechar').addEventListener('click', () => {
    document.getElementById('novo-usuario-modal-overlay').hidden = true;
  });
  document.getElementById('novo-usuario-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'novo-usuario-modal-overlay') {
      document.getElementById('novo-usuario-modal-overlay').hidden = true;
    }
  });
  document.getElementById('novo-usuario-form').addEventListener('submit', enviarNovoUsuario);
}

function abrirModalNovoUsuario() {
  document.getElementById('novo-usuario-form').reset();
  document.getElementById('novo-usuario-modal-erro').classList.remove('visible');
  document.getElementById('novo-usuario-modal-overlay').hidden = false;
}

async function enviarNovoUsuario(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('novo-usuario-modal-erro');
  const botao = document.getElementById('novo-usuario-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    nome: document.getElementById('usuario-form-nome').value,
    email: document.getElementById('usuario-form-email').value,
    senha: document.getElementById('usuario-form-senha').value,
    papel: document.getElementById('usuario-form-papel').value,
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';

  try {
    await Shell.chamarApi('/usuarios-dados', { method: 'POST', body: corpo });
    document.getElementById('novo-usuario-modal-overlay').hidden = true;
    carregarUsuarios();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar o usuário agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar usuário';
  }
}

montarModalNovoUsuario();
document.getElementById('btn-novo-usuario').addEventListener('click', abrirModalNovoUsuario);

carregarUsuarios();
