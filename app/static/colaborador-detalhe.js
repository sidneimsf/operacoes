const parametrosUrl = new URLSearchParams(window.location.search);
const colaboradorId = parametrosUrl.get('id');

const auth = Shell.montar('colaboradores', 'Colaborador');

let TIPOS_EVENTO = [];
let colaboradorAtual = null;

function labelTipoEvento(chave) {
  const encontrado = TIPOS_EVENTO.find((t) => t.chave === chave);
  if (encontrado) return encontrado.label;
  if (chave === 'cobertura') return 'Cobriu falta';
  return chave;
}

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarDataHora(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
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
    const erro = new Error(`Falha ao chamar ${caminho}: ${resposta.status}`);
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }

  return resposta.json();
}

function montarModalRegistro() {
  const html = `
    <div class="modal-overlay" id="registro-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo registro</h3>
          <button class="modal-close" id="registro-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="registro-form">
          <div class="field">
            <label for="registro-tipo">Tipo</label>
            <select id="registro-tipo" required></select>
          </div>
          <div class="field">
            <label for="registro-descricao">Descrição / observação</label>
            <textarea id="registro-descricao" rows="3" placeholder="Detalhes..."></textarea>
          </div>
          <div class="field" id="campo-data-inicio">
            <label for="registro-data-inicio">Data <span id="label-data-obrigatoria"></span></label>
            <input type="date" id="registro-data-inicio">
          </div>
          <div class="field" id="campo-data-fim" hidden>
            <label for="registro-data-fim">Data final (se souber)</label>
            <input type="date" id="registro-data-fim">
          </div>
          <div class="field" id="campo-substituto" hidden>
            <label for="registro-substituto">Quem cobriu?</label>
            <select id="registro-substituto"><option value="">Selecione...</option></select>
          </div>
          <div class="field">
            <label for="registro-arquivo">Anexar documento (JPEG, PNG ou PDF)</label>
            <input type="file" id="registro-arquivo" accept=".jpg,.jpeg,.png,.pdf">
          </div>
          <div class="error-message" id="registro-modal-erro"></div>
          <button type="submit" class="btn-primary" id="registro-modal-enviar">Salvar registro</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('registro-modal-fechar').addEventListener('click', fecharModalRegistro);
  document.getElementById('registro-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'registro-modal-overlay') fecharModalRegistro();
  });

  document.getElementById('registro-tipo').addEventListener('change', atualizarCamposConformeTipo);
  document.getElementById('registro-form').addEventListener('submit', enviarRegistro);
}

function atualizarCamposConformeTipo() {
  const tipo = document.getElementById('registro-tipo').value;
  const precisaData = tipo === 'atestado' || tipo === 'falta' || tipo === 'ferias';
  const mostraDataFim = tipo === 'atestado' || tipo === 'ferias';
  const mostraSubstituto = tipo === 'falta';

  document.getElementById('label-data-obrigatoria').textContent = precisaData ? '(obrigatória)' : '(opcional)';
  document.getElementById('campo-data-fim').hidden = !mostraDataFim;
  document.getElementById('campo-substituto').hidden = !mostraSubstituto;
}

async function abrirModalRegistro() {
  document.getElementById('registro-form').reset();
  document.getElementById('registro-modal-erro').classList.remove('visible');

  const selectTipo = document.getElementById('registro-tipo');
  selectTipo.innerHTML = TIPOS_EVENTO.map((t) => `<option value="${t.chave}">${t.label}</option>`).join('');

  const colegas = await Shell.chamarApi(`/colaboradores-dados?empresa_id=${colaboradorAtual.empresa_id}&status_filtro=ativo`);
  const selectSubstituto = document.getElementById('registro-substituto');
  selectSubstituto.innerHTML =
    '<option value="">Selecione...</option>' +
    colegas
      .filter((c) => c.id !== Number(colaboradorId))
      .map((c) => `<option value="${c.id}">${c.nome}</option>`)
      .join('');

  atualizarCamposConformeTipo();
  document.getElementById('registro-modal-overlay').hidden = false;
}

function fecharModalRegistro() {
  document.getElementById('registro-modal-overlay').hidden = true;
}

async function enviarRegistro(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('registro-modal-erro');
  const botao = document.getElementById('registro-modal-enviar');
  erroBox.classList.remove('visible');

  const formData = new FormData();
  formData.append('tipo', document.getElementById('registro-tipo').value);
  formData.append('descricao', document.getElementById('registro-descricao').value);

  const dataInicio = document.getElementById('registro-data-inicio').value;
  if (dataInicio) formData.append('data_inicio', dataInicio);

  const dataFim = document.getElementById('registro-data-fim').value;
  if (dataFim) formData.append('data_fim', dataFim);

  const substituto = document.getElementById('registro-substituto').value;
  if (substituto) formData.append('colaborador_relacionado_id', substituto);

  const arquivoInput = document.getElementById('registro-arquivo');
  if (arquivoInput.files.length > 0) {
    formData.append('arquivo', arquivoInput.files[0]);
  }

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    await enviarFormData(`/colaboradores-dados/${colaboradorId}/eventos`, formData);
    fecharModalRegistro();
    carregarTimeline();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar o registro agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar registro';
  }
}

function renderizarTimeline(eventos) {
  const container = document.getElementById('timeline');

  if (eventos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum registro ainda para este colaborador.</div>';
    return;
  }

  container.innerHTML = eventos
    .map((e) => {
      let linhaRelacionado = '';
      if (e.colaborador_relacionado_nome) {
        const texto = e.tipo === 'falta'
          ? `Cobriu: ${e.colaborador_relacionado_nome}`
          : `Substituiu: ${e.colaborador_relacionado_nome}`;
        linhaRelacionado = `<div class="evento-relacionado">${texto}</div>`;
      }

      const linhaArquivo = e.tem_arquivo
        ? `<a class="evento-arquivo-link" href="#" data-evento-id="${e.id}">📎 ${e.arquivo_nome_original || 'Baixar arquivo'}</a>`
        : '';

      const periodo = e.data_fim && e.data_fim !== e.data_inicio
        ? `${formatarData(e.data_inicio)} até ${formatarData(e.data_fim)}`
        : formatarData(e.data_inicio);

      return `
        <div class="timeline-item">
          <div class="data-col">${formatarDataHora(e.criado_em)}</div>
          <div class="conteudo">
            <div class="linha-topo">
              <span class="evento-tipo-badge ${e.tipo}">${labelTipoEvento(e.tipo)}</span>
              ${e.data_inicio ? `<span class="meta">${periodo}</span>` : ''}
            </div>
            ${e.descricao ? `<div class="descricao">${e.descricao}</div>` : ''}
            ${linhaRelacionado}
            ${linhaArquivo}
            <div class="meta" style="margin-top: 6px;">Registrado por ${e.registrado_por}</div>
          </div>
        </div>
      `;
    })
    .join('');
}

async function abrirArquivoEvento(eventoId) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return;

  try {
    const resposta = await fetch(`/colaboradores-dados/eventos/${eventoId}/arquivo`, {
      headers: { Authorization: `Bearer ${autenticacao.access_token}` },
    });
    if (resposta.status === 401) {
      Shell.sair();
      return;
    }
    if (!resposta.ok) throw new Error('Falha ao baixar arquivo');

    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (erro) {
    alert('Não foi possível abrir o arquivo agora.');
  }
}

async function carregarTimeline() {
  const container = document.getElementById('timeline');
  container.innerHTML = '<div class="loading-state">Carregando histórico...</div>';
  try {
    const eventos = await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}/eventos`);
    if (eventos === null) return;
    renderizarTimeline(eventos);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o histórico agora.</div>';
  }
}

async function iniciar() {
  if (!colaboradorId) {
    document.getElementById('colaborador-header').innerHTML = '<div class="empty-state">Colaborador não especificado.</div>';
    return;
  }

  try {
    const [colaborador, tiposEvento] = await Promise.all([
      Shell.chamarApi(`/colaboradores-dados/${colaboradorId}`),
      Shell.chamarApi('/colaboradores-dados/eventos-tipos'),
    ]);
    if (colaborador === null || tiposEvento === null) return;

    colaboradorAtual = colaborador;
    TIPOS_EVENTO = tiposEvento.tipos;

    document.getElementById('topbar-title').textContent = colaborador.nome;
    document.getElementById('colaborador-header').innerHTML = `
      <span class="empresa-tag">${colaborador.empresa_nome} · ${colaborador.status === 'ativo' ? 'Ativo' : 'Afastado'}</span>
      <h2>${colaborador.nome}</h2>
      <span class="cnpj">${colaborador.cargo || 'Cargo não informado'} · Registro ${colaborador.registro || '—'}</span>
      <div class="meta" style="margin-top: 8px;">
        Contato: ${colaborador.contato || '—'} · Admissão: ${formatarData(colaborador.data_admissao)} · Supervisor: ${colaborador.supervisor_nome || 'Administrativo'}
      </div>
    `;

    montarModalRegistro();
    document.getElementById('btn-novo-registro').addEventListener('click', abrirModalRegistro);

    document.getElementById('timeline').addEventListener('click', (evento) => {
      const link = evento.target.closest('.evento-arquivo-link');
      if (!link) return;
      evento.preventDefault();
      abrirArquivoEvento(link.dataset.eventoId);
    });

    carregarTimeline();
  } catch (erro) {
    document.getElementById('colaborador-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
