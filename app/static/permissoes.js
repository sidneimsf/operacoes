const auth = Shell.montar('permissoes', 'Permissões');

let dadosAtuais = null;

function renderizarMatriz(dados) {
  dadosAtuais = dados;
  const container = document.getElementById('matriz-permissoes');

  const headerColunas = dados.modulos.map((m) => `<th>${m.label}</th>`).join('');

  const linhas = dados.usuarios
    .map((u) => {
      const celulas = dados.modulos
        .map((m) => {
          const info = u.permissoes[m.chave];
          const marcado = info.efetivo;
          const temOverride = info.tem_override;
          return `
            <td style="text-align: center;">
              <label class="toggle-switch">
                <input type="checkbox" data-usuario-id="${u.usuario_id}" data-modulo="${m.chave}" ${marcado ? 'checked' : ''}>
                <span class="toggle-slider"></span>
              </label>
              ${temOverride ? `<button type="button" class="btn-resetar-permissao" data-usuario-id="${u.usuario_id}" data-modulo="${m.chave}" title="Voltar ao padrão">↺</button>` : ''}
            </td>
          `;
        })
        .join('');

      return `
        <tr>
          <td>${u.nome}${u.super_admin ? ' <span class="badge-super-admin">admin</span>' : ''}</td>
          <td class="meta">${u.papel === 'escritorio' ? 'Escritório' : 'Supervisor'}</td>
          ${celulas}
          <td>
            <button type="button" class="btn-ghost btn-editar-acesso" data-usuario-id="${u.usuario_id}" data-nome="${u.nome}" data-email="${u.email}" style="padding: 5px 10px; font-size: 12px;">Editar acesso</button>
          </td>
        </tr>
      `;
    })
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Usuário</th><th>Papel</th>${headerColunas}<th>Acesso</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarPermissoes() {
  const container = document.getElementById('matriz-permissoes');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const dados = await Shell.chamarApi('/admin/permissoes');
    if (dados === null) return;
    renderizarMatriz(dados);
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita aos administradores do sistema.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar as permissões agora.</div>';
  }
}

async function alternarPermissao(usuarioId, modulo, habilitado) {
  try {
    await Shell.chamarApi(`/admin/permissoes/${usuarioId}/${modulo}`, {
      method: 'PUT',
      body: { habilitado },
    });
    await carregarPermissoes();
  } catch (erro) {
    alert('Não foi possível salvar essa alteração agora.');
    await carregarPermissoes();
  }
}

async function resetarPermissao(usuarioId, modulo) {
  try {
    await Shell.chamarApi(`/admin/permissoes/${usuarioId}/${modulo}`, { method: 'DELETE' });
    await carregarPermissoes();
  } catch (erro) {
    alert('Não foi possível resetar agora.');
  }
}

// ---------- Editar acesso (e-mail / senha) ----------

function montarModalAcesso() {
  const html = `
    <div class="modal-overlay" id="acesso-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="acesso-modal-titulo">Editar acesso</h3>
          <button class="modal-close" id="acesso-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="acesso-form">
          <div class="field">
            <label for="acesso-email">E-mail de login</label>
            <input type="email" id="acesso-email" required>
          </div>
          <div class="field">
            <label for="acesso-nova-senha">Nova senha (deixe em branco pra não alterar)</label>
            <input type="text" id="acesso-nova-senha" placeholder="Digite uma nova senha, se quiser trocar">
          </div>
          <div class="error-message" id="acesso-modal-erro"></div>
          <div class="error-message" id="acesso-modal-sucesso" style="background: rgba(76,175,125,0.12); color: var(--success); border-color: rgba(76,175,125,0.3);"></div>
          <button type="submit" class="btn-primary" id="acesso-modal-enviar">Salvar</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('acesso-modal-fechar').addEventListener('click', () => {
    document.getElementById('acesso-modal-overlay').hidden = true;
  });
  document.getElementById('acesso-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'acesso-modal-overlay') {
      document.getElementById('acesso-modal-overlay').hidden = true;
    }
  });
  document.getElementById('acesso-form').addEventListener('submit', salvarAcesso);
}

let usuarioIdEmEdicaoAcesso = null;

function abrirModalAcesso(usuarioId, nome, email) {
  usuarioIdEmEdicaoAcesso = usuarioId;
  document.getElementById('acesso-modal-titulo').textContent = `Editar acesso · ${nome}`;
  document.getElementById('acesso-email').value = email;
  document.getElementById('acesso-nova-senha').value = '';
  document.getElementById('acesso-modal-erro').classList.remove('visible');
  document.getElementById('acesso-modal-sucesso').classList.remove('visible');
  document.getElementById('acesso-modal-overlay').hidden = false;
}

async function salvarAcesso(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('acesso-modal-erro');
  const sucessoBox = document.getElementById('acesso-modal-sucesso');
  const botao = document.getElementById('acesso-modal-enviar');
  erroBox.classList.remove('visible');
  sucessoBox.classList.remove('visible');

  const corpo = { email: document.getElementById('acesso-email').value };
  const novaSenha = document.getElementById('acesso-nova-senha').value;
  if (novaSenha) corpo.nova_senha = novaSenha;

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    await Shell.chamarApi(`/admin/usuarios/${usuarioIdEmEdicaoAcesso}/acesso`, { method: 'PATCH', body: corpo });
    sucessoBox.textContent = novaSenha ? 'E-mail e senha atualizados com sucesso.' : 'E-mail atualizado com sucesso.';
    sucessoBox.classList.add('visible');
    document.getElementById('acesso-nova-senha').value = '';
    await carregarPermissoes();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

document.getElementById('matriz-permissoes').addEventListener('change', (evento) => {
  const checkbox = evento.target.closest('input[type="checkbox"][data-usuario-id]');
  if (!checkbox) return;
  alternarPermissao(checkbox.dataset.usuarioId, checkbox.dataset.modulo, checkbox.checked);
});

document.getElementById('matriz-permissoes').addEventListener('click', (evento) => {
  const botaoReset = evento.target.closest('.btn-resetar-permissao');
  if (botaoReset) {
    resetarPermissao(botaoReset.dataset.usuarioId, botaoReset.dataset.modulo);
    return;
  }
  const botaoAcesso = evento.target.closest('.btn-editar-acesso');
  if (botaoAcesso) {
    abrirModalAcesso(botaoAcesso.dataset.usuarioId, botaoAcesso.dataset.nome, botaoAcesso.dataset.email);
  }
});

montarModalAcesso();
carregarPermissoes();
