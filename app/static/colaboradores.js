const auth = Shell.montar('colaboradores', 'Colaboradores');

async function iniciar() {
  const container = document.getElementById('lista-colaboradores');

  try {
    const colaboradores = await Shell.chamarApi('/colaboradores-dados');
    if (colaboradores === null) return;

    if (colaboradores.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          Nenhum colaborador cadastrado ainda.<br>
          Assim que a lista de colaboradores por cliente estiver disponível, ela aparece aqui.
        </div>
      `;
      return;
    }

    const linhas = colaboradores
      .map(
        (c) => `
        <tr>
          <td>${c.nome}</td>
          <td>${c.cliente_nome}</td>
          <td>${c.ativo ? 'Ativo' : 'Inativo'}</td>
        </tr>
      `
      )
      .join('');

    container.innerHTML = `
      <table class="table-list">
        <thead>
          <tr><th>Nome</th><th>Cliente</th><th>Status</th></tr>
        </thead>
        <tbody>${linhas}</tbody>
      </table>
    `;
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
