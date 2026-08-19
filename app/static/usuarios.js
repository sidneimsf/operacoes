const auth = Shell.montar('usuarios', 'Usuários');

async function iniciar() {
  const container = document.getElementById('lista-usuarios');

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

iniciar();
