const auth = Shell.montar('dashboard', 'Painel');

const CORES_AVATAR = ['#7d5f11', '#2f5b9e', '#8a3fa8', '#1f6b41', '#c13327', '#17354f'];

function corAvatar(nome) {
  let soma = 0;
  for (let i = 0; i < nome.length; i++) soma += nome.charCodeAt(i);
  return CORES_AVATAR[soma % CORES_AVATAR.length];
}

function iniciais(nome) {
  const partes = nome.trim().split(/\s+/);
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function avatarHtml(nome) {
  return `<div class="pessoa-avatar" style="background:${corAvatar(nome)}">${iniciais(nome)}</div>`;
}

function popularIconesEstaticos() {
  document.querySelectorAll('[data-icone]').forEach((el) => {
    el.innerHTML = Shell.icone(el.dataset.icone);
  });
}

function formatarData(isoString) {
  const data = new Date(isoString);
  return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function labelTipoChamado(chave) {
  const encontrado = TIPOS_CHAMADO.find((t) => t.chave === chave);
  return encontrado ? encontrado.label : chave;
}

function renderizarAvisoConfirmar(chamados) {
  const container = document.getElementById('aviso-confirmar-chamados');

  if (!chamados || chamados.length === 0) {
    container.innerHTML = '';
    return;
  }

  const cartoesHtml = chamados
    .map(
      (c) => `
      <div class="confirm-card" data-id="${c.id}">
        <div class="confirm-card-header">
          <span class="cliente">${c.cliente_nome}</span>
          <span class="tipo">${labelTipoChamado(c.tipo)}</span>
        </div>
        <div class="confirm-linha"><span>Pendência</span><span>${c.fechamento.pendencia ? 'Sim — ' + c.fechamento.pendencia_detalhe : 'Não'}</span></div>
        <div class="confirm-linha"><span>Documento enviado</span><span>${c.fechamento.documento_enviado ? 'Sim — ' + c.fechamento.documento_detalhe : 'Não'}</span></div>
        ${c.fechamento.observacoes ? `<div class="confirm-linha"><span>Observações</span><span>${c.fechamento.observacoes}</span></div>` : ''}
        <div class="confirm-linha"><span>Finalizado por</span><span>${c.finalizado_por}</span></div>
        <button class="btn-ghost btn-confirmar" data-id="${c.id}">Confirmar recebimento</button>
      </div>
    `
    )
    .join('');

  container.innerHTML = `
    <div class="alert-banner alert-banner-success">
      <div class="alert-banner-header">
        ${Shell.icone('ocorrencias')}
        <span>${chamados.length} chamado${chamados.length > 1 ? 's' : ''} finalizado${chamados.length > 1 ? 's' : ''} aguardando sua confirmação</span>
      </div>
      ${cartoesHtml}
    </div>
  `;

  container.querySelectorAll('.btn-confirmar').forEach((botao) => {
    botao.addEventListener('click', async () => {
      botao.disabled = true;
      botao.textContent = 'Confirmando...';
      await Shell.chamarApi(`/chamados-dados/${botao.dataset.id}/confirmar`, { method: 'POST' });
      const cartao = botao.closest('.confirm-card');
      cartao.remove();
      if (!container.querySelector('.confirm-card')) {
        container.innerHTML = '';
      }
    });
  });
}

function renderizarAvisoMeusChamados(meusChamados) {
  const container = document.getElementById('aviso-meus-chamados');

  if (!meusChamados || meusChamados.length === 0) {
    container.innerHTML = '';
    return;
  }

  const itensHtml = meusChamados
    .slice(0, 5)
    .map(
      (c) => `
      <div class="alert-item">
        <span class="cliente">${c.cliente_nome}</span>
        <span class="tipo">${c.descricao.length > 40 ? c.descricao.slice(0, 40) + '…' : c.descricao} · ${formatarData(c.criado_em)}</span>
      </div>
    `
    )
    .join('');

  container.innerHTML = `
    <div class="alert-banner">
      <div class="alert-banner-header">
        ${Shell.icone('ocorrencias')}
        <span>Você tem ${meusChamados.length} chamado${meusChamados.length > 1 ? 's' : ''} aguardando atendimento</span>
      </div>
      ${itensHtml}
      <a class="alert-banner-link" href="/ocorrencias?responsavel_id=${auth.id || ''}">Ver todos em Ocorrências →</a>
    </div>
  `;
}

function renderizarLembretes(dados) {
  const container = document.getElementById('lembretes-aniversarios');
  const { aniversarios_nascimento: nascimento, aniversarios_empresa: empresa } = dados;
  const todos = [...nascimento, ...empresa];

  document.getElementById('contador-aniversarios').textContent = todos.length;

  if (todos.length === 0) {
    container.innerHTML = '<div class="empty-state">Ninguém faz aniversário este mês.</div>';
    return;
  }

  const linhasNascimento = nascimento
    .sort((a, b) => a.dia - b.dia)
    .map(
      (a) => `
      <div class="pessoa-linha">
        ${avatarHtml(a.colaborador_nome)}
        <div class="pessoa-info">
          <a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a>
          <span class="pessoa-detalhe">Aniversário · dia ${String(a.dia).padStart(2, '0')}</span>
        </div>
        ${a.hoje ? '<span class="pessoa-tag" style="background: rgba(193,51,39,0.10); color: var(--danger);">hoje 🎂</span>' : ''}
      </div>
    `
    )
    .join('');

  const linhasEmpresa = empresa
    .sort((a, b) => a.dia - b.dia)
    .map(
      (a) => `
      <div class="pessoa-linha">
        ${avatarHtml(a.colaborador_nome)}
        <div class="pessoa-info">
          <a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a>
          <span class="pessoa-detalhe">${a.anos_completos} ano${a.anos_completos !== 1 ? 's' : ''} de empresa · dia ${String(a.dia).padStart(2, '0')}</span>
        </div>
        ${a.hoje ? '<span class="pessoa-tag" style="background: rgba(125,95,17,0.12); color: var(--accent);">hoje 🎉</span>' : ''}
      </div>
    `
    )
    .join('');

  container.innerHTML = `
    ${nascimento.length > 0 ? linhasNascimento : ''}
    ${empresa.length > 0 ? linhasEmpresa : ''}
  `;
}

async function carregarLembretes() {
  try {
    const dados = await Shell.chamarApi('/colaboradores-dados/lembretes');
    if (dados === null) return;
    renderizarLembretes(dados);
  } catch (erro) {
    document.getElementById('lembretes-aniversarios').innerHTML =
      '<div class="empty-state">Não foi possível carregar os lembretes agora.</div>';
  }
  carregarExperiencias();
}

function formatarDataExperiencia(isoString) {
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}`;
}

async function carregarExperiencias() {
  const container = document.getElementById('lembretes-experiencia');
  try {
    const criticos = await Shell.chamarApi('/colaboradores-dados/experiencia/criticos');
    if (criticos === null) return;

    document.getElementById('contador-experiencia').textContent = criticos.length;

    if (criticos.length === 0) {
      container.innerHTML = '<div class="empty-state">Nenhum checkpoint vencendo em breve.</div>';
      return;
    }

    container.innerHTML = criticos
      .map((c) => {
        const situacao = c.dias_restantes < 0 ? `venceu há ${Math.abs(c.dias_restantes)}d` : `em ${c.dias_restantes}d`;
        const corTag = c.dias_restantes < 0 ? 'rgba(193,51,39,0.10); color: var(--danger)' : 'rgba(125,95,17,0.12); color: var(--accent)';
        return `
          <div class="pessoa-linha">
            ${avatarHtml(c.colaborador_nome)}
            <div class="pessoa-info">
              <span class="pessoa-nome">${c.colaborador_nome}</span>
              <span class="pessoa-detalhe">${c.checkpoint} · ${c.empresa_nome} · ${formatarDataExperiencia(c.data_checkpoint)}</span>
            </div>
            <span class="pessoa-tag" style="background: ${corTag};">${situacao}</span>
          </div>
        `;
      })
      .join('');
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar agora.</div>';
  }
}

let TIPOS_CHAMADO = [];

async function iniciar() {
  popularIconesEstaticos();

  try {
    const [resumo, tiposEStatus] = await Promise.all([
      Shell.chamarApi('/dashboard/resumo'),
      Shell.chamarApi('/chamados-tipos'),
    ]);
    if (resumo === null) return;
    TIPOS_CHAMADO = tiposEStatus ? tiposEStatus.tipos : [];

    const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
    cards[0].textContent = resumo.total_clientes;
    cards[1].textContent = resumo.total_colaboradores;
    cards[2].textContent = resumo.total_empresas;
    cards[3].textContent = resumo.total_chamados_abertos;
    cards[4].textContent = resumo.total_usuarios;

    renderizarAvisoMeusChamados(resumo.meus_chamados);
    renderizarAvisoConfirmar(resumo.chamados_para_confirmar);

    const container = document.getElementById('breakdown-empresas');
    container.innerHTML = '';

    const maiorTotal = Math.max(...resumo.clientes_por_empresa.map((e) => e.total), 1);

    resumo.clientes_por_empresa.forEach((item) => {
      const largura = Math.round((item.total / maiorTotal) * 100);
      const linha = document.createElement('div');
      linha.className = 'breakdown-row';
      linha.innerHTML = `
        <span class="nome-empresa">${item.empresa}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${largura}%"></div></div>
        <span class="total">${item.total}</span>
      `;
      container.appendChild(linha);
    });

    carregarLembretes();
  } catch (erro) {
    document.getElementById('breakdown-empresas').innerHTML =
      '<div class="empty-state">Não foi possível carregar os indicadores agora.</div>';
  }
}

iniciar();
