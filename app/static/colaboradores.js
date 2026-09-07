const auth = Shell.montar('colaboradores', 'Colaboradores');

const filtros = {
  empresa_id: '',
  supervisor_id: '',
  status_filtro: '',
  busca: '',
};

let temporizadorBusca = null;

const ICONE_COPIAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const ICONE_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
const ICONE_WHATSAPP = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2c-5.52 0-10 4.48-10 10 0 1.77.46 3.45 1.27 4.9L2 22l5.25-1.38a9.94 9.94 0 0 0 4.79 1.22h.01c5.52 0 10-4.48 10-10s-4.48-9.84-10.01-9.84zm0 18.1a8.3 8.3 0 0 1-4.24-1.16l-.3-.18-3.12.82.83-3.04-.2-.31a8.26 8.26 0 0 1-1.28-4.43c0-4.58 3.73-8.3 8.32-8.3 4.58 0 8.3 3.72 8.3 8.3 0 4.58-3.72 8.3-8.31 8.3zm4.55-6.22c-.25-.12-1.47-.72-1.7-.81-.23-.08-.39-.12-.56.13-.17.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.12-1.04-.38-1.99-1.22-.73-.66-1.23-1.46-1.37-1.71-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.12-.15.16-.25.24-.42.08-.17.04-.31-.02-.43-.06-.12-.56-1.36-.77-1.86-.2-.49-.41-.42-.56-.43-.14-.01-.31-.01-.48-.01-.17 0-.43.06-.66.31-.23.25-.86.85-.86 2.06 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.68 4.25 3.75.59.26 1.06.41 1.42.52.6.19 1.14.16 1.57.1.48-.07 1.47-.6 1.68-1.19.21-.58.21-1.08.14-1.19-.06-.1-.23-.16-.48-.28z"/></svg>';

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

function celulaContatoHtml(contato) {
  if (!contato) return '—';
  return `
    <span style="display: inline-flex; align-items: center; gap: 4px;">
      ${contato}
      <button class="btn-icone-acao btn-copiar-contato" data-valor="${contato}" title="Copiar telefone">${ICONE_COPIAR}</button>
      <a class="btn-icone-acao" href="${Shell.linkWhatsApp(contato)}" target="_blank" rel="noopener" title="Abrir no WhatsApp" style="color: #25D366;">${ICONE_WHATSAPP}</a>
    </span>
  `;
}

function montarBarras(container, itens, chaveLabel) {
  container.innerHTML = '';
  if (itens.length === 0) {
    container.innerHTML = '<div class="empty-state">Sem dados ainda.</div>';
    return;
  }
  const maiorTotal = Math.max(...itens.map((i) => i.total), 1);
  itens.forEach((item) => {
    const largura = Math.round((item.total / maiorTotal) * 100);
    const linha = document.createElement('div');
    linha.className = 'breakdown-row';
    linha.innerHTML = `
      <span class="nome-empresa">${item[chaveLabel]}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${largura}%"></div></div>
      <span class="total">${item.total}</span>
    `;
    container.appendChild(linha);
  });
}

async function carregarResumo() {
  try {
    const resumo = await Shell.chamarApi('/colaboradores-dados/resumo');
    if (resumo === null) return;

    const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
    cards[0].textContent = resumo.total;
    cards[1].textContent = resumo.ativos;
    cards[2].textContent = resumo.afastados;
    cards[3].textContent = resumo.admitidos_mes;
    cards[4].textContent = resumo.em_atestado;
    cards[5].textContent = resumo.faltantes_hoje;

    montarBarras(document.getElementById('breakdown-empresa'), resumo.por_empresa, 'empresa');
    montarBarras(document.getElementById('breakdown-supervisor'), resumo.por_supervisor, 'supervisor');
  } catch (erro) {
    document.getElementById('breakdown-empresa').innerHTML =
      '<div class="empty-state">Não foi possível carregar os indicadores agora.</div>';
  }
}

function formatarData(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function montarQueryString() {
  const params = new URLSearchParams();
  if (filtros.empresa_id) params.set('empresa_id', filtros.empresa_id);
  if (filtros.supervisor_id) params.set('supervisor_id', filtros.supervisor_id);
  if (filtros.status_filtro) params.set('status_filtro', filtros.status_filtro);
  if (filtros.busca) params.set('busca', filtros.busca);
  return params.toString();
}

function renderizarTabela(colaboradores) {
  const container = document.getElementById('lista-colaboradores');

  if (colaboradores.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum colaborador encontrado com esses filtros.</div>';
    return;
  }

  const linhas = colaboradores
    .map(
      (c) => `
      <tr>
        <td>${c.registro || '—'}</td>
        <td><a href="/colaborador-detalhe?id=${c.id}">${c.nome}</a></td>
        <td>${c.cargo || '—'}</td>
        <td>${celulaContatoHtml(c.contato)}</td>
        <td>${formatarData(c.data_admissao)}</td>
        <td>${c.empresa_nome}</td>
        <td>${c.supervisor_nome || 'Administrativo'}</td>
        <td>${labelStatus(c.status)}</td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <table class="table-list">
      <thead>
        <tr><th>Registro</th><th>Nome</th><th>Cargo</th><th>Contato</th><th>Admissão</th><th>Empresa</th><th>Supervisor</th><th>Status</th></tr>
      </thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

function labelStatus(status) {
  if (status === 'ativo') return 'Ativo';
  if (status === 'afastado') return '<span class="badge-inativo">Afastado</span>';
  if (status === 'desligado') return '<span class="badge-inativo">Desligado</span>';
  return status;
}

async function carregarLista() {
  const container = document.getElementById('lista-colaboradores');
  container.innerHTML = '<div class="loading-state">Carregando colaboradores...</div>';
  try {
    const colaboradores = await Shell.chamarApi(`/colaboradores-dados?${montarQueryString()}`);
    if (colaboradores === null) return;
    renderizarTabela(colaboradores);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os dados agora.</div>';
  }
}

let empresasCache = [];
let supervisoresCache = [];

function calcularVencimentoAso(dataExameStr, anos) {
  if (!dataExameStr) return '';
  const [ano, mes, dia] = dataExameStr.split('-').map(Number);
  const dataExame = new Date(ano, mes - 1, dia);
  dataExame.setFullYear(dataExame.getFullYear() + anos);
  return dataExame.toISOString().slice(0, 10);
}

function montarModalColaborador() {
  const html = `
    <div class="modal-overlay" id="colaborador-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Novo colaborador</h3>
          <button class="modal-close" id="colaborador-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="colaborador-form">
          <div class="field">
            <label for="colaborador-form-empresa">Empresa</label>
            <select id="colaborador-form-empresa" required></select>
          </div>
          <div class="field">
            <label for="colaborador-form-nome">Nome</label>
            <input type="text" id="colaborador-form-nome" required>
          </div>
          <div class="field">
            <label for="colaborador-form-registro">Registro (opcional)</label>
            <input type="text" id="colaborador-form-registro">
          </div>
          <div class="field">
            <label for="colaborador-form-cargo">Cargo (opcional)</label>
            <input type="text" id="colaborador-form-cargo">
          </div>
          <div class="field">
            <label for="colaborador-form-contato">Contato (opcional)</label>
            <input type="text" id="colaborador-form-contato">
          </div>
          <div class="field">
            <label for="colaborador-form-admissao">Data de admissão (opcional)</label>
            <input type="date" id="colaborador-form-admissao">
          </div>
          <div class="field">
            <label for="colaborador-form-aniversario">Aniversário (dia/mês, opcional)</label>
            <input type="text" id="colaborador-form-aniversario" placeholder="Ex: 24/01" maxlength="5">
          </div>
          <div class="field">
            <label for="colaborador-form-aso-exame">Data do exame ASO (opcional)</label>
            <input type="date" id="colaborador-form-aso-exame">
          </div>
          <div class="field">
            <label>Validade do ASO</label>
            <div style="display: flex; gap: 8px;">
              <button type="button" class="btn-ghost btn-validade-aso-colab" data-anos="1" style="flex: 1;">1 ano</button>
              <button type="button" class="btn-ghost btn-validade-aso-colab" data-anos="2" style="flex: 1;">2 anos</button>
            </div>
          </div>
          <div class="field">
            <label for="colaborador-form-aso-vencimento">Vencimento do ASO</label>
            <input type="date" id="colaborador-form-aso-vencimento">
          </div>
          <div class="field">
            <label for="colaborador-form-supervisor">Supervisor (opcional)</label>
            <select id="colaborador-form-supervisor"><option value="">Administrativo / sem supervisor</option></select>
          </div>
          <div class="error-message" id="colaborador-modal-erro"></div>
          <button type="submit" class="btn-primary" id="colaborador-modal-enviar">Criar colaborador</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('colaborador-modal-fechar').addEventListener('click', fecharModalColaborador);
  document.getElementById('colaborador-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'colaborador-modal-overlay') fecharModalColaborador();
  });
  document.getElementById('colaborador-form').addEventListener('submit', enviarNovoColaborador);

  document.querySelectorAll('.btn-validade-aso-colab').forEach((botao) => {
    botao.addEventListener('click', () => {
      document.querySelectorAll('.btn-validade-aso-colab').forEach((b) => b.classList.remove('ativa'));
      botao.classList.add('ativa');
      const exame = document.getElementById('colaborador-form-aso-exame').value;
      if (exame) {
        document.getElementById('colaborador-form-aso-vencimento').value = calcularVencimentoAso(exame, Number(botao.dataset.anos));
      }
    });
  });
}

function abrirModalColaborador() {
  document.getElementById('colaborador-form').reset();
  document.getElementById('colaborador-modal-erro').classList.remove('visible');
  document.querySelectorAll('.btn-validade-aso-colab').forEach((b) => b.classList.remove('ativa'));
  document.getElementById('colaborador-form-empresa').innerHTML = empresasCache
    .map((e) => `<option value="${e.id}">${e.nome}</option>`)
    .join('');
  document.getElementById('colaborador-form-supervisor').innerHTML =
    '<option value="">Administrativo / sem supervisor</option>' +
    supervisoresCache.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');
  document.getElementById('colaborador-modal-overlay').hidden = false;
}

function fecharModalColaborador() {
  document.getElementById('colaborador-modal-overlay').hidden = true;
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

async function enviarNovoColaborador(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('colaborador-modal-erro');
  const botao = document.getElementById('colaborador-modal-enviar');
  erroBox.classList.remove('visible');

  const textoAniversario = document.getElementById('colaborador-form-aniversario').value.trim();
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

  const dataExameAso = document.getElementById('colaborador-form-aso-exame').value;
  const dataVencimentoAso = document.getElementById('colaborador-form-aso-vencimento').value;
  if (dataExameAso && !dataVencimentoAso) {
    erroBox.textContent = 'Escolha a validade do ASO (1 ou 2 anos) ou preencha o vencimento.';
    erroBox.classList.add('visible');
    return;
  }

  const supervisorValor = document.getElementById('colaborador-form-supervisor').value;
  const corpo = {
    empresa_id: Number(document.getElementById('colaborador-form-empresa').value),
    nome: document.getElementById('colaborador-form-nome').value,
    registro: document.getElementById('colaborador-form-registro').value || null,
    cargo: document.getElementById('colaborador-form-cargo').value || null,
    contato: document.getElementById('colaborador-form-contato').value || null,
    data_admissao: document.getElementById('colaborador-form-admissao').value || null,
    aniversario_dia: aniversarioDia,
    aniversario_mes: aniversarioMes,
    supervisor_id: supervisorValor ? Number(supervisorValor) : null,
  };

  botao.disabled = true;
  botao.textContent = 'Criando...';

  try {
    const novoColaborador = await Shell.chamarApi('/colaboradores-dados', { method: 'POST', body: corpo });

    if (dataExameAso && dataVencimentoAso) {
      const formDataAso = new FormData();
      formDataAso.append('tipo', 'aso');
      formDataAso.append('data_inicio', dataExameAso);
      formDataAso.append('data_fim', dataVencimentoAso);
      await enviarFormData(`/colaboradores-dados/${novoColaborador.id}/eventos`, formDataAso);
    }

    fecharModalColaborador();
    carregarResumo();
    carregarLista();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível criar o colaborador agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Criar colaborador';
  }
}

async function iniciar() {
  const empresas = await Shell.chamarApi('/empresas');
  if (empresas === null) return;
  empresasCache = empresas;
  document.getElementById('filtro-empresa').innerHTML =
    '<option value="">Todas</option>' + empresas.map((e) => `<option value="${e.id}">${e.nome}</option>`).join('');

  const supervisores = await Shell.chamarApi('/supervisores');
  if (supervisores === null) return;
  supervisoresCache = supervisores;
  document.getElementById('filtro-supervisor').innerHTML =
    '<option value="">Todos</option>' + supervisores.map((s) => `<option value="${s.id}">${s.nome}</option>`).join('');

  document.getElementById('filtro-empresa').addEventListener('change', (evento) => {
    filtros.empresa_id = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-supervisor').addEventListener('change', (evento) => {
    filtros.supervisor_id = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-status').addEventListener('change', (evento) => {
    filtros.status_filtro = evento.target.value;
    carregarLista();
  });

  document.getElementById('filtro-busca').addEventListener('input', (evento) => {
    clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(() => {
      filtros.busca = evento.target.value;
      carregarLista();
    }, 350);
  });

  carregarResumo();
  carregarLista();
}

montarModalColaborador();
document.getElementById('btn-novo-colaborador').addEventListener('click', abrirModalColaborador);
if (auth.papel !== 'escritorio') {
  document.getElementById('btn-novo-colaborador').hidden = true;
}

document.getElementById('lista-colaboradores').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.btn-copiar-contato');
  if (botao) copiarTexto(botao.dataset.valor, botao);
});

iniciar();
