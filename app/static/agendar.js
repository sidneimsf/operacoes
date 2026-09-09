const auth = Shell.montar('agendar', 'Agendar');

const DIAS_SEMANA_LABEL = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MESES_LABEL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

const hoje = new Date();
let mesAtual = hoje.getMonth();
let anoAtual = hoje.getFullYear();
let tarefasDoMes = [];
let tarefaIdEmEdicao = null;

function formatarDataISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function hojeISO() {
  return formatarDataISO(new Date());
}

async function carregarMes() {
  document.getElementById('calendario-titulo-mes').textContent = `${MESES_LABEL[mesAtual]} de ${anoAtual}`;

  const primeiroDiaMes = new Date(anoAtual, mesAtual, 1);
  const ultimoDiaMes = new Date(anoAtual, mesAtual + 1, 0);
  const dataInicioBusca = formatarDataISO(primeiroDiaMes);
  const dataFimBusca = formatarDataISO(ultimoDiaMes);

  try {
    tarefasDoMes = await Shell.chamarApi(`/tarefas-dados?data_inicio=${dataInicioBusca}&data_fim=${dataFimBusca}`);
    if (tarefasDoMes === null) return;
    renderizarCalendario();
  } catch (erro) {
    document.getElementById('calendario-grade').innerHTML = '<div class="empty-state">Não foi possível carregar o calendário agora.</div>';
  }
}

function renderizarCalendario() {
  const container = document.getElementById('calendario-grade');
  const primeiroDiaMes = new Date(anoAtual, mesAtual, 1);
  const ultimoDiaMes = new Date(anoAtual, mesAtual + 1, 0);
  const diaSemanaInicio = primeiroDiaMes.getDay();
  const totalDias = ultimoDiaMes.getDate();

  const tarefasPorDia = {};
  tarefasDoMes.forEach((t) => {
    if (!tarefasPorDia[t.data]) tarefasPorDia[t.data] = [];
    tarefasPorDia[t.data].push(t);
  });

  const cabecalhoHtml = DIAS_SEMANA_LABEL.map((d) => `<div class="calendario-dia-semana">${d}</div>`).join('');

  const celulasVaziasInicio = Array.from({ length: diaSemanaInicio }, () => '<div class="calendario-celula vazia"></div>').join('');

  const celulasDias = Array.from({ length: totalDias }, (_, i) => {
    const dia = i + 1;
    const dataISO = formatarDataISO(new Date(anoAtual, mesAtual, dia));
    const tarefasDoDia = tarefasPorDia[dataISO] || [];
    const ehHoje = dataISO === hojeISO();

    const chipsHtml = tarefasDoDia
      .slice(0, 3)
      .map(
        (t) => `<div class="calendario-tarefa-chip ${t.concluida ? 'concluida' : ''}" data-id="${t.id}">${t.titulo}</div>`
      )
      .join('');
    const maisHtml = tarefasDoDia.length > 3 ? `<div class="calendario-tarefa-mais">+${tarefasDoDia.length - 3}</div>` : '';

    return `
      <div class="calendario-celula ${ehHoje ? 'hoje' : ''}" data-data="${dataISO}">
        <div class="calendario-numero-dia">${dia}</div>
        <div class="calendario-tarefas-dia">${chipsHtml}${maisHtml}</div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="calendario-mes">
      ${cabecalhoHtml}
      ${celulasVaziasInicio}
      ${celulasDias}
    </div>
  `;
}

async function carregarPendentes() {
  const container = document.getElementById('lista-pendentes');
  try {
    const tarefas = await Shell.chamarApi('/tarefas-dados/hoje');
    if (tarefas === null) return;
    if (tarefas.length === 0) {
      container.innerHTML = '<div class="empty-state">Nada pendente por aqui. 🎉</div>';
      return;
    }
    container.innerHTML = tarefas
      .map(
        (t) => `
        <div class="pendente-item" data-id="${t.id}">
          <span class="pendente-titulo">${t.titulo}</span>
          <span class="meta">${formatarDataBR(t.data)}</span>
          <button class="btn-ghost btn-concluir-pendente" data-id="${t.id}" style="padding: 4px 10px; font-size: 12px;">Marcar concluída</button>
        </div>
      `
      )
      .join('');
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar agora.</div>';
  }
}

function formatarDataBR(dataISO) {
  const [ano, mes, dia] = dataISO.split('-');
  return `${dia}/${mes}/${ano}`;
}

function montarModalTarefa() {
  const html = `
    <div class="modal-overlay" id="tarefa-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3 id="tarefa-modal-titulo">Nova tarefa</h3>
          <button class="modal-close" id="tarefa-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="tarefa-form">
          <div class="field">
            <label for="tarefa-titulo">Título</label>
            <input type="text" id="tarefa-titulo" required placeholder="Ex: Pagar Carro">
          </div>
          <div class="field">
            <label for="tarefa-data">Data</label>
            <input type="date" id="tarefa-data" required>
          </div>
          <div class="field">
            <label for="tarefa-descricao">Descrição (opcional)</label>
            <textarea id="tarefa-descricao" rows="3"></textarea>
          </div>
          <div class="field" id="campo-tarefa-concluida" hidden>
            <label><input type="checkbox" id="tarefa-concluida"> Concluída</label>
          </div>
          <div class="error-message" id="tarefa-modal-erro"></div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button type="submit" class="btn-primary" id="tarefa-modal-enviar" style="flex: 1;">Salvar</button>
            <button type="button" class="btn-ghost" id="tarefa-modal-excluir" style="color: var(--danger); display: none;">Excluir</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('tarefa-modal-fechar').addEventListener('click', fecharModalTarefa);
  document.getElementById('tarefa-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'tarefa-modal-overlay') fecharModalTarefa();
  });
  document.getElementById('tarefa-form').addEventListener('submit', salvarTarefa);
  document.getElementById('tarefa-modal-excluir').addEventListener('click', excluirTarefaAtual);
}

function fecharModalTarefa() {
  document.getElementById('tarefa-modal-overlay').hidden = true;
}

function abrirModalNovaTarefa(dataPreSelecionada) {
  tarefaIdEmEdicao = null;
  document.getElementById('tarefa-modal-titulo').textContent = 'Nova tarefa';
  document.getElementById('tarefa-form').reset();
  document.getElementById('tarefa-data').value = dataPreSelecionada || hojeISO();
  document.getElementById('campo-tarefa-concluida').hidden = true;
  document.getElementById('tarefa-modal-excluir').style.display = 'none';
  document.getElementById('tarefa-modal-erro').classList.remove('visible');
  document.getElementById('tarefa-modal-overlay').hidden = false;
}

function abrirModalEditarTarefa(tarefaId) {
  const tarefa = tarefasDoMes.find((t) => t.id === Number(tarefaId));
  if (!tarefa) return;
  tarefaIdEmEdicao = tarefaId;

  document.getElementById('tarefa-modal-titulo').textContent = 'Editar tarefa';
  document.getElementById('tarefa-titulo').value = tarefa.titulo;
  document.getElementById('tarefa-data').value = tarefa.data;
  document.getElementById('tarefa-descricao').value = tarefa.descricao || '';
  document.getElementById('tarefa-concluida').checked = tarefa.concluida;
  document.getElementById('campo-tarefa-concluida').hidden = false;
  document.getElementById('tarefa-modal-excluir').style.display = '';
  document.getElementById('tarefa-modal-erro').classList.remove('visible');
  document.getElementById('tarefa-modal-overlay').hidden = false;
}

async function salvarTarefa(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('tarefa-modal-erro');
  const botao = document.getElementById('tarefa-modal-enviar');
  erroBox.classList.remove('visible');

  const corpo = {
    titulo: document.getElementById('tarefa-titulo').value,
    data: document.getElementById('tarefa-data').value,
    descricao: document.getElementById('tarefa-descricao').value || null,
  };
  if (tarefaIdEmEdicao) {
    corpo.concluida = document.getElementById('tarefa-concluida').checked;
  }

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  try {
    if (tarefaIdEmEdicao) {
      await Shell.chamarApi(`/tarefas-dados/${tarefaIdEmEdicao}`, { method: 'PATCH', body: corpo });
    } else {
      await Shell.chamarApi('/tarefas-dados', { method: 'POST', body: corpo });
    }
    fecharModalTarefa();
    await Promise.all([carregarMes(), carregarPendentes()]);
  } catch (erro) {
    erroBox.textContent = 'Não foi possível salvar agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar';
  }
}

async function excluirTarefaAtual() {
  if (!tarefaIdEmEdicao) return;
  if (!confirm('Tem certeza que quer excluir essa tarefa?')) return;
  try {
    await Shell.chamarApi(`/tarefas-dados/${tarefaIdEmEdicao}`, { method: 'DELETE' });
    fecharModalTarefa();
    await Promise.all([carregarMes(), carregarPendentes()]);
  } catch (erro) {
    alert('Não foi possível excluir agora.');
  }
}

async function marcarPendenteConcluida(tarefaId) {
  try {
    await Shell.chamarApi(`/tarefas-dados/${tarefaId}`, { method: 'PATCH', body: { concluida: true } });
    await Promise.all([carregarMes(), carregarPendentes()]);
  } catch (erro) {
    alert('Não foi possível atualizar agora.');
  }
}

function iniciar() {
  montarModalTarefa();

  document.getElementById('btn-mes-anterior').addEventListener('click', () => {
    mesAtual -= 1;
    if (mesAtual < 0) { mesAtual = 11; anoAtual -= 1; }
    carregarMes();
  });
  document.getElementById('btn-mes-seguinte').addEventListener('click', () => {
    mesAtual += 1;
    if (mesAtual > 11) { mesAtual = 0; anoAtual += 1; }
    carregarMes();
  });
  document.getElementById('btn-mes-hoje').addEventListener('click', () => {
    mesAtual = new Date().getMonth();
    anoAtual = new Date().getFullYear();
    carregarMes();
  });
  document.getElementById('btn-nova-tarefa').addEventListener('click', () => abrirModalNovaTarefa());

  document.getElementById('calendario-grade').addEventListener('click', (evento) => {
    const chip = evento.target.closest('.calendario-tarefa-chip');
    if (chip) {
      abrirModalEditarTarefa(chip.dataset.id);
      return;
    }
    const celula = evento.target.closest('.calendario-celula:not(.vazia)');
    if (celula) {
      abrirModalNovaTarefa(celula.dataset.data);
    }
  });

  document.getElementById('lista-pendentes').addEventListener('click', (evento) => {
    const botaoConcluir = evento.target.closest('.btn-concluir-pendente');
    if (botaoConcluir) {
      marcarPendenteConcluida(botaoConcluir.dataset.id);
      return;
    }
    const item = evento.target.closest('.pendente-item');
    if (item) {
      abrirModalEditarTarefa(item.dataset.id);
    }
  });

  carregarMes();
  carregarPendentes();
}

iniciar();
