const auth = Shell.montar('asos', 'ASOs');

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function labelSituacao(situacao, diasRestantes) {
  if (situacao === 'vencido') return `Vencido há ${Math.abs(diasRestantes)} dia(s)`;
  if (situacao === 'proximo') return `Vence em ${diasRestantes} dia(s)`;
  return `Em dia (${diasRestantes} dias)`;
}

function renderizarLista(asos) {
  const container = document.getElementById('lista-asos');

  const vencidos = asos.filter((a) => a.situacao === 'vencido').length;
  const proximos = asos.filter((a) => a.situacao === 'proximo').length;
  const emDia = asos.filter((a) => a.situacao === 'ok').length;

  const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
  cards[0].textContent = vencidos;
  cards[1].textContent = proximos;
  cards[2].textContent = emDia;

  if (asos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum ASO cadastrado ainda.</div>';
    return;
  }

  const linhas = asos
    .map(
      (a) => `
      <tr>
        <td><a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a></td>
        <td>${a.cargo || '—'}</td>
        <td>${a.empresa_nome}</td>
        <td>${formatarData(a.data_exame)}</td>
        <td>${formatarData(a.data_vencimento)}</td>
        <td><span class="aso-badge ${a.situacao}">${labelSituacao(a.situacao, a.dias_restantes)}</span></td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Colaborador</th><th>Cargo</th><th>Empresa</th><th>Data do exame</th><th>Vencimento</th><th>Situação</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarAsos() {
  const container = document.getElementById('lista-asos');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const asos = await Shell.chamarApi('/asos-dados');
    if (asos === null) return;
    renderizarLista(asos);
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

async function testarEnvioEmail() {
  const botao = document.getElementById('btn-testar-email');
  const resultadoBox = document.getElementById('resultado-teste-email');
  botao.disabled = true;
  botao.textContent = 'Enviando...';
  resultadoBox.innerHTML = '';

  try {
    const resultado = await Shell.chamarApi('/asos-dados/testar-email', { method: 'POST' });
    if (resultado.enviado) {
      resultadoBox.innerHTML = `<div class="error-message visible" style="background: rgba(92,184,138,0.12); color: var(--success); border-color: rgba(92,184,138,0.3);">
        E-mail enviado para ${resultado.destinatarios.join(', ')} com ${resultado.total} ASO(s) crítico(s).
      </div>`;
    } else {
      resultadoBox.innerHTML = `<div class="error-message visible">${resultado.motivo}</div>`;
    }
  } catch (erro) {
    resultadoBox.innerHTML = `<div class="error-message visible">${erro.detalhe || 'Não foi possível enviar o e-mail agora.'}</div>`;
  } finally {
    botao.disabled = false;
    botao.textContent = 'Testar envio de e-mail';
  }
}

document.getElementById('btn-testar-email').addEventListener('click', testarEnvioEmail);
carregarAsos();
