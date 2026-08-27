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
        </tr>
      `;
    })
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Usuário</th><th>Papel</th>${headerColunas}</tr>
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

document.getElementById('matriz-permissoes').addEventListener('change', (evento) => {
  const checkbox = evento.target.closest('input[type="checkbox"][data-usuario-id]');
  if (!checkbox) return;
  alternarPermissao(checkbox.dataset.usuarioId, checkbox.dataset.modulo, checkbox.checked);
});

document.getElementById('matriz-permissoes').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.btn-resetar-permissao');
  if (!botao) return;
  resetarPermissao(botao.dataset.usuarioId, botao.dataset.modulo);
});

carregarPermissoes();
