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

const DIAS_PADRAO = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado'];
const DIAS_LABEL = {
  segunda: 'Segunda', terca: 'Terça', quarta: 'Quarta', quinta: 'Quinta',
  sexta: 'Sexta', sabado: 'Sábado', domingo: 'Domingo',
};
const TURNOS_LABEL = { manha: 'Manhã', tarde: 'Tarde', noite: 'Noite' };

function celulaHorarioHtml(registro, campoNome, dia, turno) {
  if (!registro) {
    return `<td data-dia="${dia}" data-turno="${turno}"><span class="horario-celula-vazia">+</span></td>`;
  }
  return `
    <td data-dia="${dia}" data-turno="${turno}" data-horario-id="${registro.id}">
      <div class="horario-celula">
        <span class="nome">${registro[campoNome]}</span>
        <span class="hora">${registro.hora_inicio}-${registro.hora_fim}</span>
      </div>
    </td>
  `;
}

function montarGradeSemanal(horarios, campoNome) {
  const diasComDados = new Set(horarios.map((h) => h.dia_semana));
  const dias = [...DIAS_PADRAO];
  if (diasComDados.has('domingo')) dias.push('domingo');

  const porDiaTurno = {};
  horarios.forEach((h) => {
    porDiaTurno[`${h.dia_semana}_${h.turno}`] = h;
  });

  const headerCols = dias.map((d) => `<th>${DIAS_LABEL[d]}</th>`).join('');
  const linhaManha = dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_manha`], campoNome, d, 'manha')).join('');
  const linhaTarde = dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_tarde`], campoNome, d, 'tarde')).join('');
  const linhaNoite = dias.map((d) => celulaHorarioHtml(porDiaTurno[`${d}_noite`], campoNome, d, 'noite')).join('');

  return `
    <table class="horario-grid">
      <thead><tr><th></th>${headerCols}</tr></thead>
      <tbody>
        <tr><td>Manhã</td>${linhaManha}</tr>
        <tr><td>Tarde</td>${linhaTarde}</tr>
        <tr><td>Noite</td>${linhaNoite}</tr>
      </tbody>
    </table>
  `;
}

let horariosAtuais = [];
let clientesAgrupadosCache = null;
let celulaEmEdicao = null;

async function carregarClientesAgrupados() {
  if (clientesAgrupadosCache) return clientesAgrupadosCache;
  const [empresas, clientes] = await Promise.all([
    Shell.chamarApi('/empresas'),
    Shell.chamarApi('/clientes-dados?incluir_inativos=false'),
  ]);
  clientesAgrupadosCache = empresas.map((e) => ({
    empresa: e.nome,
    clientes: clientes.filter((c) => c.empresa_id === e.id),
  }));
  return clientesAgrupadosCache;
}

function montarModalHorario() {
  const html = `
    <div class="modal-overlay" id="horario-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="horario-modal-titulo">Horário</h3>
          <button class="modal-close" id="horario-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="horario-form">
          <div class="field">
            <label for="horario-cliente">Cliente</label>
            <select id="horario-cliente" required></select>
          </div>
          <div class="field">
            <label for="horario-hora-inicio">Início</label>
            <input type="time" id="horario-hora-inicio" required>
          </div>
          <div class="field">
            <label for="horario-hora-fim">Fim</label>
            <input type="time" id="horario-hora-fim" required>
          </div>
          <div class="error-message" id="horario-modal-erro"></div>
          <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn-primary" id="horario-modal-enviar" style="flex: 1;">Salvar</button>
            <button type="button" class="btn-ghost" id="horario-modal-remover" hidden>Remover</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('horario-modal-fechar').addEventListener('click', fecharModalHorario);
  document.getElementById('horario-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'horario-modal-overlay') fecharModalHorario();
  });
  document.getElementById('horario-form').addEventListener('submit', salvarHorario);
  document.getElementById('horario-modal-remover').addEventListener('click', removerHorarioAtual);
}

async function abrirModalHorario(dia, turno, horarioId) {
  celulaEmEdicao = { dia, turno, horarioId: horarioId ? Number(horarioId) : null };

  const erroBox = document.getElementById('horario-modal-erro');
  erroBox.classList.remove('visible');
  document.getElementById('horario-modal-titulo').textContent = `${DIAS_LABEL[dia]} · ${TURNOS_LABEL[turno]}`;

  const grupos = await carregarClientesAgrupados();
  const selectCliente = document.getElementById('horario-cliente');
  selectCliente.innerHTML = grupos
    .map(
      (g) =>
        `<optgroup label="${g.empresa}">${g.clientes.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('')}</optgroup>`
    )
    .join('');

  const botaoRemover = document.getElementById('horario-modal-remover');

  if (celulaEmEdicao.horarioId) {
    const registro = horariosAtuais.find((h) => h.id === celulaEmEdicao.horarioId);
    selectCliente.value = registro.cliente_id;
    document.getElementById('horario-hora-inicio').value = registro.hora_inicio;
    document.getElementById('horario-hora-fim').value = registro.hora_fim;
    botaoRemover.hidden = false;
  } else {
    document.getElementById('horario-hora-inicio').value = '';
    document.getElementById('horario-hora-fim').value = '';
    botaoRemover.hidden = true;
  }

  document.getElementById('horario-modal-overlay').hidden = false;
}

function fecharModalHorario() {
  document.getElementById('horario-modal-overlay').hidden = true;
}

async function salvarHorario(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('horario-modal-erro');
  erroBox.classList.remove('visible');

  const corpo = {
    cliente_id: Number(document.getElementById('horario-cliente').value),
    hora_inicio: document.getElementById('horario-hora-inicio').value,
    hora_fim: document.getElementById('horario-hora-fim').value,
  };

  try {
    if (celulaEmEdicao.horarioId) {
      await Shell.chamarApi(`/horarios-servico/${celulaEmEdicao.horarioId}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi('/horarios-servico', {
        method: 'POST',
        body: {
          colaborador_id: Number(colaboradorId),
          dia_semana: celulaEmEdicao.dia,
          turno: celulaEmEdicao.turno,
          ...corpo,
        },
      });
    }
    fecharModalHorario();
    carregarMapaServicos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  }
}

async function removerHorarioAtual() {
  if (!celulaEmEdicao.horarioId) return;
  if (!confirm('Remover esse horário da agenda?')) return;

  try {
    await Shell.chamarApi(`/horarios-servico/${celulaEmEdicao.horarioId}`, { method: 'DELETE' });
    fecharModalHorario();
    carregarMapaServicos();
  } catch (erro) {
    alert('Não foi possível remover agora.');
  }
}

async function carregarMapaServicos() {
  const container = document.getElementById('mapa-servicos');
  try {
    const horarios = await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}/horarios`);
    if (horarios === null) return;
    horariosAtuais = horarios;
    container.innerHTML = montarGradeSemanal(horarios, 'cliente_nome');
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o mapa de serviços agora.</div>';
  }
}

function montarModalEditarColaborador() {
  const html = `
    <div class="modal-overlay" id="editar-colab-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Editar colaborador</h3>
          <button class="modal-close" id="editar-colab-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="editar-colab-form">
          <div class="field">
            <label for="editar-colab-empresa">Empresa</label>
            <select id="editar-colab-empresa" required></select>
          </div>
          <div class="field">
            <label for="editar-colab-nome">Nome</label>
            <input type="text" id="editar-colab-nome" required>
          </div>
          <div class="field">
            <label for="editar-colab-registro">Registro</label>
            <input type="text" id="editar-colab-registro">
          </div>
          <div class="field">
            <label for="editar-colab-cargo">Cargo</label>
            <input type="text" id="editar-colab-cargo">
          </div>
          <div class="field">
            <label for="editar-colab-contato">Contato</label>
            <input type="text" id="editar-colab-contato">
          </div>
          <div class="field">
            <label for="editar-colab-admissao">Data de admissão</label>
            <input type="date" id="editar-colab-admissao">
          </div>
          <div class="field">
            <label for="editar-colab-supervisor">Supervisor</label>
            <select id="editar-colab-supervisor"><option value="">Administrativo / sem supervisor</option></select>
          </div>
          <div class="field">
            <label for="editar-colab-status">Status</label>
            <select id="editar-colab-status">
              <option value="ativo">Ativo</option>
              <option value="afastado">Afastado</option>
              <option value="desligado">Desligado</option>
            </select>
          </div>
          <div class="error-message" id="editar-colab-modal-erro"></div>
          <button type="submit" class="btn-primary" id="editar-colab-modal-enviar">Salvar alterações</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('editar-colab-modal-fechar').addEventListener('click', () => {
    document.getElementById('editar-colab-modal-overlay').hidden = true;
  });
  document.getElementById('editar-colab-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'editar-colab-modal-overlay') {
      document.getElementById('editar-colab-modal-overlay').hidden = true;
    }
  });
  document.getElementById('editar-colab-form').addEventListener('submit', salvarEdicaoColaborador);
}

async function abrirModalEditarColaborador() {
  document.getElementById('editar-colab-modal-erro').classList.remove('visible');

  const [empresas, supervisores] = await Promise.all([
    Shell.chamarApi('/empresas'),
    Shell.chamarApi('/supervisores'),
  ]);

  document.getElementById('editar-colab-empresa').innerHTML = empresas
    .map((e) => `<option value="${e.id}" ${e.id === colaboradorAtual.empresa_id ? 'selected' : ''}>${e.nome}</option>`)
    .join('');
  document.getElementById('editar-colab-supervisor').innerHTML =
    '<option value="">Administrativo / sem supervisor</option>' +
    supervisores
      .map((s) => `<option value="${s.id}" ${s.id === colaboradorAtual.supervisor_id ? 'selected' : ''}>${s.nome}</option>`)
      .join('');

  document.getElementById('editar-colab-nome').value = colaboradorAtual.nome;
  document.getElementById('editar-colab-registro').value = colaboradorAtual.registro || '';
  document.getElementById('editar-colab-cargo').value = colaboradorAtual.cargo || '';
  document.getElementById('editar-colab-contato').value = colaboradorAtual.contato || '';
  document.getElementById('editar-colab-admissao').value = colaboradorAtual.data_admissao || '';
  document.getElementById('editar-colab-status').value = colaboradorAtual.status;

  document.getElementById('editar-colab-modal-overlay').hidden = false;
}

async function salvarEdicaoColaborador(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-colab-modal-erro');
  const botao = document.getElementById('editar-colab-modal-enviar');
  erroBox.classList.remove('visible');

  const supervisorValor = document.getElementById('editar-colab-supervisor').value;
  const corpo = {
    empresa_id: Number(document.getElementById('editar-colab-empresa').value),
    nome: document.getElementById('editar-colab-nome').value,
    registro: document.getElementById('editar-colab-registro').value || null,
    cargo: document.getElementById('editar-colab-cargo').value || null,
    contato: document.getElementById('editar-colab-contato').value || null,
    data_admissao: document.getElementById('editar-colab-admissao').value || null,
    supervisor_id: supervisorValor ? Number(supervisorValor) : null,
    status: document.getElementById('editar-colab-status').value,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';

  try {
    colaboradorAtual = await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}`, {
      method: 'PATCH',
      body: corpo,
    });
    document.getElementById('editar-colab-modal-overlay').hidden = true;
    renderizarHeaderColaborador();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar alterações';
  }
}

function renderizarHeaderColaborador() {
  const c = colaboradorAtual;
  document.getElementById('topbar-title').textContent = c.nome;
  document.getElementById('colaborador-header').innerHTML = `
    <span class="empresa-tag">${c.empresa_nome} · ${c.status === 'ativo' ? 'Ativo' : c.status === 'afastado' ? 'Afastado' : 'Desligado'}</span>
    <h2>${c.nome}</h2>
    <span class="cnpj">${c.cargo || 'Cargo não informado'} · Registro ${c.registro || '—'}</span>
    <div class="meta" style="margin-top: 8px;">
      Contato: ${c.contato || '—'} · Admissão: ${formatarData(c.data_admissao)} · Supervisor: ${c.supervisor_nome || 'Administrativo'}
    </div>
  `;
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
  const precisaData = tipo === 'atestado' || tipo === 'falta' || tipo === 'ferias' || tipo === 'aso';
  const mostraDataFim = tipo === 'atestado' || tipo === 'ferias' || tipo === 'aso';
  const mostraSubstituto = tipo === 'falta';

  document.getElementById('label-data-obrigatoria').textContent = precisaData ? '(obrigatória)' : '(opcional)';
  document.getElementById('campo-data-fim').hidden = !mostraDataFim;
  document.getElementById('campo-substituto').hidden = !mostraSubstituto;

  const labelDataInicio = tipo === 'aso' ? 'Data do exame' : 'Data';
  const labelDataFim = tipo === 'aso' ? 'Data de vencimento' : 'Data final (se souber)';
  document.querySelector('label[for="registro-data-inicio"]').firstChild.textContent = `${labelDataInicio} `;
  document.querySelector('label[for="registro-data-fim"]').textContent = labelDataFim;
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

    renderizarHeaderColaborador();

    montarModalRegistro();
    document.getElementById('btn-novo-registro').addEventListener('click', abrirModalRegistro);

    montarModalEditarColaborador();
    document.getElementById('btn-editar-colaborador').addEventListener('click', abrirModalEditarColaborador);

    montarModalHorario();
    document.getElementById('mapa-servicos').addEventListener('click', (evento) => {
      const celula = evento.target.closest('td[data-dia]');
      if (!celula) return;
      abrirModalHorario(celula.dataset.dia, celula.dataset.turno, celula.dataset.horarioId);
    });

    document.getElementById('timeline').addEventListener('click', (evento) => {
      const link = evento.target.closest('.evento-arquivo-link');
      if (!link) return;
      evento.preventDefault();
      abrirArquivoEvento(link.dataset.eventoId);
    });

    carregarMapaServicos();
    carregarTimeline();
  } catch (erro) {
    document.getElementById('colaborador-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
