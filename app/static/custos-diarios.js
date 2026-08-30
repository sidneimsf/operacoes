const auth = Shell.montar('custos-diarios', 'Custos Diários');

let TIPOS_CUSTO = [];
let custoIdEmEdicao = null;

function formatarData(isoString) {
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarMoeda(valor) {
  return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function labelTipoCusto(chave) {
  const encontrado = TIPOS_CUSTO.find((t) => t.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function renderizarLista(custos) {
  const container = document.getElementById('lista-custos');

  const total = custos.reduce((soma, c) => soma + c.valor, 0);
  const pendentes = custos.filter((c) => !c.reembolsado);
  const reembolsados = custos.filter((c) => c.reembolsado);

  const cards = document.querySelectorAll('#kpi-grid-custos .kpi-card .value');
  cards[0].textContent = formatarMoeda(total);
  cards[1].textContent = formatarMoeda(pendentes.reduce((s, c) => s + c.valor, 0));
  cards[2].textContent = formatarMoeda(reembolsados.reduce((s, c) => s + c.valor, 0));

  if (custos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum custo lançado ainda.</div>';
    return;
  }

  const ehEscritorio = auth.papel === 'escritorio';

  const linhas = custos
    .map((c) => {
      const podeEditar = c.usuario_id === auth.id || ehEscritorio;
      const linhaComprovante = c.tem_comprovante
        ? `<a href="#" class="link-comprovante" data-custo-id="${c.id}">📎 ver</a>`
        : '—';
      const botaoReembolso = ehEscritorio
        ? `<button class="btn-ghost btn-toggle-reembolso" data-custo-id="${c.id}" data-atual="${c.reembolsado}" style="padding: 4px 8px; font-size: 11.5px;">${c.reembolsado ? 'Desfazer' : 'Marcar reembolsado'}</button>`
        : '';
      const botoesEdicao = podeEditar
        ? `
          <button class="btn-ghost btn-custo-editar" data-custo-id="${c.id}" style="padding: 4px 8px; font-size: 11.5px;">Editar</button>
          <button class="btn-ghost btn-custo-excluir" data-custo-id="${c.id}" style="padding: 4px 8px; font-size: 11.5px;">Excluir</button>
        `
        : '';

      return `
      <tr>
        <td>${formatarData(c.data)}</td>
        <td>${c.usuario_nome}</td>
        <td>${labelTipoCusto(c.tipo)}</td>
        <td>${formatarMoeda(c.valor)}</td>
        <td>${c.nome_beneficiario || c.usuario_nome}${c.chave_pix ? ` <span class="meta">(${c.chave_pix})</span>` : ''}</td>
        <td>${c.descricao || '—'}</td>
        <td>${linhaComprovante}</td>
        <td><span class="aso-badge ${c.reembolsado ? 'ok' : 'proximo'}">${c.reembolsado ? 'Reembolsado' : 'Pendente'}</span></td>
        <td style="white-space: nowrap;">${botaoReembolso} ${botoesEdicao}</td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Data</th><th>Quem lançou</th><th>Tipo</th><th>Valor</th><th>Reembolsar para</th><th>Descrição</th><th>Comprovante</th><th>Status</th><th>Ações</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function carregarCustos() {
  const container = document.getElementById('lista-custos');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const custos = await Shell.chamarApi('/custos-diarios-dados');
    if (custos === null) return;
    renderizarLista(custos);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

async function verComprovante(custoId) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return;
  try {
    const resposta = await fetch(`/custos-diarios-dados/${custoId}/comprovante`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) throw new Error('Falha ao baixar');
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (erro) {
    alert('Não foi possível abrir o comprovante agora.');
  }
}

function montarModalNovoCusto() {
  const html = `
    <div class="modal-overlay" id="novo-custo-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="custo-modal-titulo">Lançar custo</h3>
          <button class="modal-close" id="novo-custo-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="novo-custo-form">
          <div class="field">
            <label for="custo-tipo">Tipo de custo</label>
            <select id="custo-tipo" required></select>
          </div>
          <div class="field">
            <label for="custo-valor">Valor (R$)</label>
            <input type="number" id="custo-valor" min="0.01" step="0.01" required>
          </div>
          <div class="field">
            <label for="custo-data">Data</label>
            <input type="date" id="custo-data" required>
          </div>
          <div class="field">
            <label for="custo-descricao">Descrição (opcional)</label>
            <textarea id="custo-descricao" rows="2" placeholder="Ex: Combustível pra visitar o cliente X"></textarea>
          </div>
          <div class="field">
            <label for="custo-nome-beneficiario">Reembolsar para (nome, se for diferente de você)</label>
            <input type="text" id="custo-nome-beneficiario" placeholder="Deixe em branco se for você mesmo">
          </div>
          <div class="field">
            <label for="custo-chave-pix">Chave PIX pro reembolso</label>
            <input type="text" id="custo-chave-pix" placeholder="CPF, telefone, e-mail ou chave aleatória">
          </div>
          <div class="field" id="campo-comprovante">
            <label for="custo-comprovante">Comprovante (opcional, JPEG/PNG/PDF)</label>
            <input type="file" id="custo-comprovante" accept=".jpg,.jpeg,.png,.pdf">
          </div>
          <div class="error-message" id="custo-modal-erro"></div>
          <button type="submit" class="btn-primary" id="custo-modal-enviar">Salvar</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('novo-custo-modal-fechar').addEventListener('click', fecharModalCusto);
  document.getElementById('novo-custo-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'novo-custo-modal-overlay') fecharModalCusto();
  });
  document.getElementById('novo-custo-form').addEventListener('submit', salvarCusto);
}

function abrirModalNovoCusto() {
  custoIdEmEdicao = null;
  document.getElementById('custo-modal-titulo').textContent = 'Lançar custo';
  document.getElementById('novo-custo-form').reset();
  document.getElementById('custo-tipo').innerHTML = TIPOS_CUSTO.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');
  document.getElementById('custo-data').value = new Date().toISOString().slice(0, 10);
  document.getElementById('campo-comprovante').hidden = false;
  document.getElementById('custo-modal-erro').classList.remove('visible');
  document.getElementById('novo-custo-modal-overlay').hidden = false;
}

function abrirModalEditarCusto(custoId, custo) {
  custoIdEmEdicao = custoId;
  document.getElementById('custo-modal-titulo').textContent = 'Editar custo';
  document.getElementById('novo-custo-form').reset();
  document.getElementById('custo-tipo').innerHTML = TIPOS_CUSTO.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');
  document.getElementById('custo-tipo').value = custo.tipo;
  document.getElementById('custo-valor').value = custo.valor;
  document.getElementById('custo-data').value = custo.data;
  document.getElementById('custo-descricao').value = custo.descricao || '';
  document.getElementById('custo-nome-beneficiario').value = custo.nome_beneficiario || '';
  document.getElementById('custo-chave-pix').value = custo.chave_pix || '';
  document.getElementById('campo-comprovante').hidden = true;
  document.getElementById('custo-modal-erro').classList.remove('visible');
  document.getElementById('novo-custo-modal-overlay').hidden = false;
}

function fecharModalCusto() {
  document.getElementById('novo-custo-modal-overlay').hidden = true;
}

async function enviarFormData(caminho, formData) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return null;

  const resposta = await fetch(caminho, {
    method: 'POST',
    headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    body: formData,
  });

  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error(`Falha ao chamar ${caminho}`);
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }
  return resposta.json();
}

async function salvarCusto(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('custo-modal-erro');
  const botao = document.getElementById('custo-modal-enviar');
  erroBox.classList.remove('visible');

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    if (custoIdEmEdicao) {
      const corpo = {
        tipo: document.getElementById('custo-tipo').value,
        valor: Number(document.getElementById('custo-valor').value),
        data: document.getElementById('custo-data').value,
        descricao: document.getElementById('custo-descricao').value || null,
        nome_beneficiario: document.getElementById('custo-nome-beneficiario').value || null,
        chave_pix: document.getElementById('custo-chave-pix').value || null,
      };
      await Shell.chamarApi(`/custos-diarios-dados/${custoIdEmEdicao}`, { method: 'PATCH', body: corpo });
    } else {
      const formData = new FormData();
      formData.append('tipo', document.getElementById('custo-tipo').value);
      formData.append('valor', document.getElementById('custo-valor').value);
      formData.append('data_custo', document.getElementById('custo-data').value);
      formData.append('descricao', document.getElementById('custo-descricao').value || '');
      formData.append('nome_beneficiario', document.getElementById('custo-nome-beneficiario').value || '');
      formData.append('chave_pix', document.getElementById('custo-chave-pix').value || '');
      const arquivo = document.getElementById('custo-comprovante').files[0];
      if (arquivo) formData.append('comprovante', arquivo);
      await enviarFormData('/custos-diarios-dados', formData);
    }
    fecharModalCusto();
    carregarCustos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

async function excluirCusto(custoId) {
  if (!confirm('Excluir esse custo lançado?')) return;
  try {
    await Shell.chamarApi(`/custos-diarios-dados/${custoId}`, { method: 'DELETE' });
    carregarCustos();
  } catch (erro) {
    alert('Não foi possível excluir agora.');
  }
}

async function alternarReembolso(custoId, estadoAtual) {
  try {
    await Shell.chamarApi(`/custos-diarios-dados/${custoId}`, {
      method: 'PATCH',
      body: { reembolsado: estadoAtual !== 'true' },
    });
    carregarCustos();
  } catch (erro) {
    alert('Não foi possível atualizar agora.');
  }
}

async function testarEnvioEmail() {
  const botao = document.getElementById('btn-testar-email-custos');
  const resultadoBox = document.getElementById('resultado-teste-email');
  botao.disabled = true;
  botao.textContent = 'Enviando...';
  resultadoBox.innerHTML = '';

  try {
    const resultado = await Shell.chamarApi('/custos-diarios-dados/testar-email', { method: 'POST' });
    if (resultado.enviado) {
      resultadoBox.innerHTML = `<div class="error-message visible" style="background: rgba(92,184,138,0.12); color: var(--success); border-color: rgba(92,184,138,0.3);">
        E-mail enviado para ${resultado.destinatarios.join(', ')} com ${resultado.total} custo(s), totalizando ${formatarMoeda(resultado.valor_total)}.
      </div>`;
    } else {
      resultadoBox.innerHTML = `<div class="error-message visible">${resultado.motivo}</div>`;
    }
  } catch (erro) {
    resultadoBox.innerHTML = `<div class="error-message visible">${erro.detalhe || 'Não foi possível enviar agora.'}</div>`;
  } finally {
    botao.disabled = false;
    botao.textContent = 'Testar envio de e-mail';
  }
}

async function iniciar() {
  const tiposResposta = await Shell.chamarApi('/custos-diarios-dados-tipos');
  if (tiposResposta === null) return;
  TIPOS_CUSTO = tiposResposta.tipos;

  if (auth.papel === 'escritorio') {
    document.getElementById('btn-testar-email-custos').hidden = false;
  }

  await carregarCustos();
}

document.getElementById('lista-custos').addEventListener('click', async (evento) => {
  const linkComprovante = evento.target.closest('.link-comprovante');
  if (linkComprovante) {
    evento.preventDefault();
    verComprovante(linkComprovante.dataset.custoId);
    return;
  }
  const botaoExcluir = evento.target.closest('.btn-custo-excluir');
  if (botaoExcluir) {
    excluirCusto(botaoExcluir.dataset.custoId);
    return;
  }
  const botaoReembolso = evento.target.closest('.btn-toggle-reembolso');
  if (botaoReembolso) {
    alternarReembolso(botaoReembolso.dataset.custoId, botaoReembolso.dataset.atual);
    return;
  }
  const botaoEditar = evento.target.closest('.btn-custo-editar');
  if (botaoEditar) {
    const custos = await Shell.chamarApi('/custos-diarios-dados');
    const custo = custos.find((c) => c.id === Number(botaoEditar.dataset.custoId));
    if (custo) abrirModalEditarCusto(custo.id, custo);
  }
});

montarModalNovoCusto();
document.getElementById('btn-novo-custo').addEventListener('click', abrirModalNovoCusto);
document.getElementById('btn-testar-email-custos').addEventListener('click', testarEnvioEmail);

iniciar();
