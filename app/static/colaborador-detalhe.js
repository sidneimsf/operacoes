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

function celulaHorarioHtml(registros, campoNome, dia, turno) {
  const lista = (registros || []).slice().sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  const itensHtml = lista
    .map(
      (registro) => `
      <div class="horario-celula" data-horario-id="${registro.id}">
        <span class="nome">${registro[campoNome]}</span>
        <span class="hora">${registro.hora_inicio}-${registro.hora_fim}</span>
      </div>
    `
    )
    .join('');

  const dicaAdicionar = lista.length === 0
    ? '<span class="horario-celula-vazia">+</span>'
    : '<span class="horario-add-mais">+ adicionar outro</span>';

  return `<td data-dia="${dia}" data-turno="${turno}">${itensHtml}${dicaAdicionar}</td>`;
}

function montarGradeSemanal(horarios, campoNome) {
  const diasComDados = new Set(horarios.map((h) => h.dia_semana));
  const dias = [...DIAS_PADRAO];
  if (diasComDados.has('domingo')) dias.push('domingo');

  const porDiaTurno = {};
  horarios.forEach((h) => {
    const chave = `${h.dia_semana}_${h.turno}`;
    if (!porDiaTurno[chave]) porDiaTurno[chave] = [];
    porDiaTurno[chave].push(h);
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
let clientesListaPlanaCache = [];
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
            <label for="horario-cliente-busca">Cliente</label>
            <div class="busca-select">
              <input type="text" id="horario-cliente-busca" placeholder="Digite pra buscar o cliente..." autocomplete="off" required>
              <input type="hidden" id="horario-cliente-id">
              <div class="busca-select-resultados" id="horario-cliente-resultados" hidden></div>
            </div>
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

  const inputBusca = document.getElementById('horario-cliente-busca');
  inputBusca.addEventListener('input', () => {
    document.getElementById('horario-cliente-id').value = '';
    renderizarResultadosBuscaCliente(inputBusca.value);
  });
  inputBusca.addEventListener('focus', () => renderizarResultadosBuscaCliente(inputBusca.value));
  document.getElementById('horario-cliente-resultados').addEventListener('click', (evento) => {
    const item = evento.target.closest('.busca-select-item');
    if (!item) return;
    document.getElementById('horario-cliente-id').value = item.dataset.id;
    inputBusca.value = item.dataset.nome;
    document.getElementById('horario-cliente-resultados').hidden = true;
  });
  document.addEventListener('click', (evento) => {
    if (!evento.target.closest('.busca-select')) {
      const resultados = document.getElementById('horario-cliente-resultados');
      if (resultados) resultados.hidden = true;
    }
  });
  document.getElementById('horario-modal-remover').addEventListener('click', removerHorarioAtual);
}

async function abrirModalHorario(dia, turno, horarioId) {
  celulaEmEdicao = { dia, turno, horarioId: horarioId ? Number(horarioId) : null };

  const erroBox = document.getElementById('horario-modal-erro');
  erroBox.classList.remove('visible');
  document.getElementById('horario-modal-titulo').textContent = `${DIAS_LABEL[dia]} · ${TURNOS_LABEL[turno]}`;

  const grupos = await carregarClientesAgrupados();
  clientesListaPlanaCache = grupos.flatMap((g) => g.clientes.map((c) => ({ id: c.id, nome: c.nome, empresa: g.empresa })));

  const inputBusca = document.getElementById('horario-cliente-busca');
  const inputId = document.getElementById('horario-cliente-id');
  inputBusca.value = '';
  inputId.value = '';
  document.getElementById('horario-cliente-resultados').hidden = true;

  const botaoRemover = document.getElementById('horario-modal-remover');

  if (celulaEmEdicao.horarioId) {
    const registro = horariosAtuais.find((h) => h.id === celulaEmEdicao.horarioId);
    inputId.value = registro.cliente_id;
    inputBusca.value = registro.cliente_nome;
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

function renderizarResultadosBuscaCliente(termo) {
  const resultadosBox = document.getElementById('horario-cliente-resultados');
  const termoNormalizado = termo.trim().toLowerCase();
  const filtrados = termoNormalizado
    ? clientesListaPlanaCache.filter((c) => c.nome.toLowerCase().includes(termoNormalizado))
    : clientesListaPlanaCache;

  if (filtrados.length === 0) {
    resultadosBox.innerHTML = '<div class="busca-select-vazio">Nenhum cliente encontrado.</div>';
  } else {
    resultadosBox.innerHTML = filtrados
      .slice(0, 50)
      .map(
        (c) => `
        <div class="busca-select-item" data-id="${c.id}" data-nome="${c.nome}">
          <span class="busca-select-grupo">${c.empresa}</span>
          ${c.nome}
        </div>
      `
      )
      .join('');
  }
  resultadosBox.hidden = false;
}

function fecharModalHorario() {
  document.getElementById('horario-modal-overlay').hidden = true;
}

async function salvarHorario(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('horario-modal-erro');
  erroBox.classList.remove('visible');

  const clienteIdValor = document.getElementById('horario-cliente-id').value;
  if (!clienteIdValor) {
    erroBox.textContent = 'Escolha um cliente na lista de busca.';
    erroBox.classList.add('visible');
    return;
  }

  const corpo = {
    cliente_id: Number(clienteIdValor),
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

function montarModalDesligar() {
  const html = `
    <div class="modal-overlay" id="desligar-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Desligar colaborador</h3>
          <button class="modal-close" id="desligar-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="desligar-form">
          <p class="meta" style="margin-bottom: 14px;">Isso marca <strong id="desligar-nome-colaborador"></strong> como desligado e some da lista de colaboradores ativos.</p>
          <div class="field">
            <label for="desligar-data">Data do desligamento</label>
            <input type="date" id="desligar-data" required>
          </div>
          <div class="error-message" id="desligar-modal-erro"></div>
          <button type="submit" class="btn-primary" style="background: var(--danger);" id="desligar-modal-enviar">Confirmar desligamento</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('desligar-modal-fechar').addEventListener('click', () => {
    document.getElementById('desligar-modal-overlay').hidden = true;
  });
  document.getElementById('desligar-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'desligar-modal-overlay') document.getElementById('desligar-modal-overlay').hidden = true;
  });
  document.getElementById('desligar-form').addEventListener('submit', confirmarDesligamento);
}

function abrirModalDesligar() {
  document.getElementById('desligar-nome-colaborador').textContent = colaboradorAtual.nome;
  document.getElementById('desligar-data').value = new Date().toISOString().slice(0, 10);
  document.getElementById('desligar-modal-erro').classList.remove('visible');
  document.getElementById('desligar-modal-overlay').hidden = false;
}

async function confirmarDesligamento(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('desligar-modal-erro');
  const botao = document.getElementById('desligar-modal-enviar');
  erroBox.classList.remove('visible');

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    colaboradorAtual = await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}`, {
      method: 'PATCH',
      body: { status: 'desligado', data_desligamento: document.getElementById('desligar-data').value },
    });
    document.getElementById('desligar-modal-overlay').hidden = true;
    renderizarHeaderColaborador();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Confirmar desligamento';
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
            <label for="editar-colab-aniversario">Aniversário (dia/mês, opcional)</label>
            <input type="text" id="editar-colab-aniversario" placeholder="Ex: 24/01" maxlength="5">
          </div>
          <div class="field">
            <label for="editar-colab-experiencia-30">Fim do período de 30 dias (opcional)</label>
            <input type="date" id="editar-colab-experiencia-30">
          </div>
          <div class="field">
            <label for="editar-colab-experiencia-90">Fim do período de 90 dias (opcional)</label>
            <input type="date" id="editar-colab-experiencia-90">
          </div>
          <div class="field">
            <label for="editar-colab-vt-numero">Número do cartão VT</label>
            <input type="text" id="editar-colab-vt-numero">
          </div>
          <div class="field">
            <label for="editar-colab-vt-situacao">Situação do VT</label>
            <input type="text" id="editar-colab-vt-situacao" placeholder="Ex: Ativo, Está na empresa">
          </div>
          <div class="field">
            <label for="editar-colab-vt-saldo">Saldo do VT (R$)</label>
            <input type="number" id="editar-colab-vt-saldo" step="0.01" min="0">
          </div>
          <div class="field">
            <label for="editar-colab-seguro-inclusao">Seguro de vida - inclusão</label>
            <input type="date" id="editar-colab-seguro-inclusao">
          </div>
          <div class="field">
            <label for="editar-colab-seguro-exclusao">Seguro de vida - exclusão</label>
            <input type="date" id="editar-colab-seguro-exclusao">
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
          <div class="field">
            <label for="editar-colab-data-desligamento">Data de desligamento (se aplicável)</label>
            <input type="date" id="editar-colab-data-desligamento">
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
  const diaAniv = colaboradorAtual.aniversario_dia;
  const mesAniv = colaboradorAtual.aniversario_mes;
  document.getElementById('editar-colab-aniversario').value =
    diaAniv && mesAniv ? `${String(diaAniv).padStart(2, '0')}/${String(mesAniv).padStart(2, '0')}` : '';
  document.getElementById('editar-colab-experiencia-30').value = colaboradorAtual.data_fim_experiencia_30 || '';
  document.getElementById('editar-colab-experiencia-90').value = colaboradorAtual.data_fim_experiencia_90 || '';
  document.getElementById('editar-colab-vt-numero').value = colaboradorAtual.vt_numero_cartao || '';
  document.getElementById('editar-colab-vt-situacao').value = colaboradorAtual.vt_situacao || '';
  document.getElementById('editar-colab-vt-saldo').value = colaboradorAtual.vt_saldo ?? '';
  document.getElementById('editar-colab-seguro-inclusao').value = colaboradorAtual.seguro_vida_data_inclusao || '';
  document.getElementById('editar-colab-seguro-exclusao').value = colaboradorAtual.seguro_vida_data_exclusao || '';
  document.getElementById('editar-colab-status').value = colaboradorAtual.status;
  document.getElementById('editar-colab-data-desligamento').value = colaboradorAtual.data_desligamento || '';

  document.getElementById('editar-colab-modal-overlay').hidden = false;
}

async function salvarEdicaoColaborador(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('editar-colab-modal-erro');
  const botao = document.getElementById('editar-colab-modal-enviar');
  erroBox.classList.remove('visible');

  const textoAniversario = document.getElementById('editar-colab-aniversario').value.trim();
  let aniversarioDia = null;
  let aniversarioMes = null;
  if (textoAniversario) {
    const partes = textoAniversario.split('/');
    if (partes.length !== 2 || isNaN(Number(partes[0])) || isNaN(Number(partes[1]))) {
      erroBox.textContent = 'Aniversário deve estar no formato DD/MM, ex: 24/01';
      erroBox.classList.add('visible');
      return;
    }
    aniversarioDia = Number(partes[0]);
    aniversarioMes = Number(partes[1]);
  }

  const supervisorValor = document.getElementById('editar-colab-supervisor').value;
  const corpo = {
    empresa_id: Number(document.getElementById('editar-colab-empresa').value),
    nome: document.getElementById('editar-colab-nome').value,
    registro: document.getElementById('editar-colab-registro').value || null,
    cargo: document.getElementById('editar-colab-cargo').value || null,
    contato: document.getElementById('editar-colab-contato').value || null,
    data_admissao: document.getElementById('editar-colab-admissao').value || null,
    aniversario_dia: aniversarioDia,
    aniversario_mes: aniversarioMes,
    data_fim_experiencia_30: document.getElementById('editar-colab-experiencia-30').value || null,
    data_fim_experiencia_90: document.getElementById('editar-colab-experiencia-90').value || null,
    vt_numero_cartao: document.getElementById('editar-colab-vt-numero').value || null,
    vt_situacao: document.getElementById('editar-colab-vt-situacao').value || null,
    vt_saldo: document.getElementById('editar-colab-vt-saldo').value ? Number(document.getElementById('editar-colab-vt-saldo').value) : null,
    seguro_vida_data_inclusao: document.getElementById('editar-colab-seguro-inclusao').value || null,
    seguro_vida_data_exclusao: document.getElementById('editar-colab-seguro-exclusao').value || null,
    supervisor_id: supervisorValor ? Number(supervisorValor) : null,
    status: document.getElementById('editar-colab-status').value,
    data_desligamento: document.getElementById('editar-colab-data-desligamento').value || null,
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

function calcularTempoDeCasa(dataAdmissaoIso) {
  if (!dataAdmissaoIso) return null;
  const admissao = new Date(dataAdmissaoIso + 'T00:00:00');
  const hoje = new Date();
  let anos = hoje.getFullYear() - admissao.getFullYear();
  let meses = hoje.getMonth() - admissao.getMonth();
  if (hoje.getDate() < admissao.getDate()) meses -= 1;
  if (meses < 0) {
    anos -= 1;
    meses += 12;
  }
  if (anos <= 0 && meses <= 0) return 'menos de 1 mês de empresa';
  const partes = [];
  if (anos > 0) partes.push(`${anos} ano${anos > 1 ? 's' : ''}`);
  if (meses > 0) partes.push(`${meses} mês${meses > 1 ? 'es' : ''}`);
  return `${partes.join(' e ')} de empresa`;
}

const ICONE_COPIAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const ICONE_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

function copiarTexto(texto, botao) {
  navigator.clipboard.writeText(texto).then(() => {
    const original = botao.innerHTML;
    botao.innerHTML = ICONE_CHECK;
    botao.style.color = 'var(--success)';
    setTimeout(() => {
      botao.innerHTML = original;
      botao.style.color = '';
    }, 1500);
  });
}

function renderizarHeaderColaborador() {
  const c = colaboradorAtual;
  document.getElementById('topbar-title').textContent = c.nome;

  const tempoDeCasa = calcularTempoDeCasa(c.data_admissao);

  const itens = [];
  itens.push({
    label: 'Contato',
    valor: c.contato
      ? `${c.contato} <button class="btn-icone-acao btn-copiar-contato" data-valor="${c.contato}" title="Copiar telefone">${ICONE_COPIAR}</button>`
      : '—',
  });
  itens.push({ label: 'Admissão', valor: formatarData(c.data_admissao) });
  itens.push({ label: 'Supervisor', valor: c.supervisor_nome || 'Administrativo' });
  if (tempoDeCasa) itens.push({ label: 'Tempo de casa', valor: `🎉 ${tempoDeCasa}` });
  if (c.aniversario_dia && c.aniversario_mes) {
    itens.push({ label: 'Aniversário', valor: `🎂 ${String(c.aniversario_dia).padStart(2, '0')}/${String(c.aniversario_mes).padStart(2, '0')}` });
  }
  if (c.status === 'desligado' && c.data_desligamento) {
    itens.push({ label: 'Desligamento', valor: formatarData(c.data_desligamento) });
  }
  if (c.data_fim_experiencia_30) itens.push({ label: 'Experiência · 30 dias', valor: formatarData(c.data_fim_experiencia_30) });
  if (c.data_fim_experiencia_90) itens.push({ label: 'Experiência · 90 dias', valor: formatarData(c.data_fim_experiencia_90) });
  if (c.vt_numero_cartao) {
    itens.push({ label: 'Vale transporte', valor: `${c.vt_numero_cartao}${c.vt_situacao ? ` (${c.vt_situacao})` : ''}` });
  }
  if (c.vt_saldo != null) itens.push({ label: 'Saldo VT', valor: `R$ ${c.vt_saldo.toFixed(2)}` });
  if (c.seguro_vida_data_inclusao) {
    itens.push({
      label: 'Seguro de vida',
      valor: `desde ${formatarData(c.seguro_vida_data_inclusao)}${c.seguro_vida_data_exclusao ? ` até ${formatarData(c.seguro_vida_data_exclusao)}` : ''}`,
    });
  }

  const gridHtml = itens
    .map((item) => `<div class="info-item"><span class="info-label">${item.label}</span><span class="info-value">${item.valor}</span></div>`)
    .join('');

  document.getElementById('colaborador-header').innerHTML = `
    <span class="empresa-tag">${c.empresa_nome} · ${c.status === 'ativo' ? 'Ativo' : c.status === 'afastado' ? 'Afastado' : 'Desligado'}</span>
    <h2>${c.nome}</h2>
    <span class="cnpj">${c.cargo || 'Cargo não informado'} · Registro ${c.registro || '—'}</span>
    <div class="info-grid">${gridHtml}</div>
  `;

  document.querySelectorAll('.btn-copiar-contato').forEach((botao) => {
    botao.addEventListener('click', () => copiarTexto(botao.dataset.valor, botao));
  });
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

function renderizarListaMetlife(lancamentos) {
  const container = document.getElementById('lista-metlife');
  if (lancamentos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum lançamento do METLIFE ainda.</div>';
    return;
  }
  const linhas = lancamentos
    .map(
      (l) => `
      <tr>
        <td>${l.nome_dependente || '<em>Titular</em>'}</td>
        <td>${l.valor != null ? 'R$ ' + l.valor.toFixed(2) : '—'}</td>
        <td>${l.desconta ? 'Sim' : 'Não'}</td>
        <td>${l.data_inclusao ? formatarData(l.data_inclusao) : '—'}</td>
        <td>${l.data_exclusao ? formatarData(l.data_exclusao) : '—'}</td>
        <td>
          <button class="btn-ghost btn-metlife-editar" data-id="${l.id}" style="padding: 4px 8px; font-size: 11.5px;">Editar</button>
          <button class="btn-ghost btn-metlife-excluir" data-id="${l.id}" style="padding: 4px 8px; font-size: 11.5px;">Excluir</button>
        </td>
      </tr>
    `
    )
    .join('');
  container.innerHTML = `
    <table class="table-list">
      <thead><tr><th>Dependente</th><th>Valor</th><th>Desconta</th><th>Inclusão</th><th>Exclusão</th><th>Ações</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

let metlifeCacheAtual = [];

async function carregarMetlife() {
  const container = document.getElementById('lista-metlife');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';
  try {
    const lancamentos = await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}/metlife`);
    if (lancamentos === null) return;
    metlifeCacheAtual = lancamentos;
    renderizarListaMetlife(lancamentos);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar agora.</div>';
  }
}

function montarModalMetlife() {
  const html = `
    <div class="modal-overlay" id="metlife-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="metlife-modal-titulo">Lançamento METLIFE</h3>
          <button class="modal-close" id="metlife-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="metlife-form">
          <div class="field">
            <label for="metlife-dependente">Nome do dependente (deixe em branco se for o titular)</label>
            <input type="text" id="metlife-dependente">
          </div>
          <div class="field">
            <label for="metlife-valor">Valor (R$)</label>
            <input type="number" id="metlife-valor" step="0.01" min="0">
          </div>
          <div class="field">
            <label><input type="checkbox" id="metlife-desconta" style="width: auto; margin-right: 6px;">Desconta em folha</label>
          </div>
          <div class="field">
            <label for="metlife-inclusao">Data de inclusão</label>
            <input type="date" id="metlife-inclusao">
          </div>
          <div class="field">
            <label for="metlife-exclusao">Data de exclusão</label>
            <input type="date" id="metlife-exclusao">
          </div>
          <div class="error-message" id="metlife-modal-erro"></div>
          <button type="submit" class="btn-primary" id="metlife-modal-enviar">Salvar</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('metlife-modal-fechar').addEventListener('click', () => {
    document.getElementById('metlife-modal-overlay').hidden = true;
  });
  document.getElementById('metlife-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'metlife-modal-overlay') document.getElementById('metlife-modal-overlay').hidden = true;
  });
  document.getElementById('metlife-form').addEventListener('submit', salvarMetlife);
}

let metlifeIdEmEdicao = null;

function abrirModalMetlife(id) {
  metlifeIdEmEdicao = id;
  document.getElementById('metlife-form').reset();
  document.getElementById('metlife-modal-erro').classList.remove('visible');

  if (id) {
    const lancamento = metlifeCacheAtual.find((l) => l.id === id);
    document.getElementById('metlife-modal-titulo').textContent = 'Editar lançamento METLIFE';
    document.getElementById('metlife-dependente').value = lancamento.nome_dependente || '';
    document.getElementById('metlife-valor').value = lancamento.valor ?? '';
    document.getElementById('metlife-desconta').checked = lancamento.desconta;
    document.getElementById('metlife-inclusao').value = lancamento.data_inclusao || '';
    document.getElementById('metlife-exclusao').value = lancamento.data_exclusao || '';
  } else {
    document.getElementById('metlife-modal-titulo').textContent = 'Adicionar dependente';
  }

  document.getElementById('metlife-modal-overlay').hidden = false;
}

async function salvarMetlife(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('metlife-modal-erro');
  const botao = document.getElementById('metlife-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    nome_dependente: document.getElementById('metlife-dependente').value || null,
    valor: document.getElementById('metlife-valor').value ? Number(document.getElementById('metlife-valor').value) : null,
    desconta: document.getElementById('metlife-desconta').checked,
    data_inclusao: document.getElementById('metlife-inclusao').value || null,
    data_exclusao: document.getElementById('metlife-exclusao').value || null,
  };

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    if (metlifeIdEmEdicao) {
      await Shell.chamarApi(`/colaboradores-dados/metlife/${metlifeIdEmEdicao}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi(`/colaboradores-dados/${colaboradorId}/metlife`, { method: 'POST', body: corpo });
    }
    document.getElementById('metlife-modal-overlay').hidden = true;
    carregarMetlife();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

async function excluirMetlife(id) {
  if (!confirm('Excluir esse lançamento do METLIFE?')) return;
  try {
    await Shell.chamarApi(`/colaboradores-dados/metlife/${id}`, { method: 'DELETE' });
    carregarMetlife();
  } catch (erro) {
    alert('Não foi possível excluir agora.');
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
    montarModalDesligar();
    document.getElementById('btn-desligar-colaborador').addEventListener('click', abrirModalDesligar);

    montarModalHorario();
    document.getElementById('mapa-servicos').addEventListener('click', (evento) => {
      const itemExistente = evento.target.closest('.horario-celula[data-horario-id]');
      const td = evento.target.closest('td[data-dia]');
      if (!td) return;

      if (itemExistente) {
        abrirModalHorario(td.dataset.dia, td.dataset.turno, itemExistente.dataset.horarioId);
      } else {
        abrirModalHorario(td.dataset.dia, td.dataset.turno, null);
      }
    });

    document.getElementById('timeline').addEventListener('click', (evento) => {
      const link = evento.target.closest('.evento-arquivo-link');
      if (!link) return;
      evento.preventDefault();
      abrirArquivoEvento(link.dataset.eventoId);
    });

    montarModalMetlife();
    document.getElementById('btn-novo-metlife').addEventListener('click', () => abrirModalMetlife(null));
    document.getElementById('lista-metlife').addEventListener('click', (evento) => {
      const btnEditar = evento.target.closest('.btn-metlife-editar');
      if (btnEditar) return abrirModalMetlife(Number(btnEditar.dataset.id));
      const btnExcluir = evento.target.closest('.btn-metlife-excluir');
      if (btnExcluir) return excluirMetlife(Number(btnExcluir.dataset.id));
    });

    carregarMapaServicos();
    carregarTimeline();
    carregarMetlife();
  } catch (erro) {
    document.getElementById('colaborador-header').innerHTML =
      '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

iniciar();
