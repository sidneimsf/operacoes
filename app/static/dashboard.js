const auth = Shell.montar('dashboard', 'Painel');

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

  // meusChamados so vem preenchido quando quem logou e' supervisor.
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

const MESES_LABEL = {
  1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
  7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
};

function renderizarLembretes(dados) {
  const container = document.getElementById('lembretes-aniversarios');
  const { aniversarios_nascimento: nascimento, aniversarios_empresa: empresa } = dados;

  if (nascimento.length === 0 && empresa.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum aniversário este mês.</div>';
    return;
  }

  const listaNascimento = nascimento
    .map(
      (a) => `
      <div class="lembrete-item">
        <span class="lembrete-dia">${String(a.dia).padStart(2, '0')}</span>
        <a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a>
        ${a.hoje ? '<span class="lembrete-hoje">hoje 🎂</span>' : ''}
      </div>
    `
    )
    .join('');

  const listaEmpresa = empresa
    .map(
      (a) => `
      <div class="lembrete-item">
        <span class="lembrete-dia">${String(a.dia).padStart(2, '0')}</span>
        <a href="/colaborador-detalhe?id=${a.colaborador_id}">${a.colaborador_nome}</a>
        <span class="lembrete-anos">${a.anos_completos} ano${a.anos_completos !== 1 ? 's' : ''} de empresa</span>
        ${a.hoje ? '<span class="lembrete-hoje">hoje 🎉</span>' : ''}
      </div>
    `
    )
    .join('');

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px;">
      <div>
        <div class="lembrete-subtitulo">🎂 Aniversário (nascimento)</div>
        ${nascimento.length > 0 ? listaNascimento : '<div class="empty-state">Ninguém este mês.</div>'}
      </div>
      <div>
        <div class="lembrete-subtitulo">🎉 Aniversário de empresa</div>
        ${empresa.length > 0 ? listaEmpresa : '<div class="empty-state">Ninguém este mês.</div>'}
      </div>
    </div>
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
  return `${dia}/${mes}/${ano}`;
}

async function carregarExperiencias() {
  const container = document.getElementById('lembretes-experiencia');
  try {
    const criticos = await Shell.chamarApi('/colaboradores-dados/experiencia/criticos');
    if (criticos === null) return;

    if (criticos.length === 0) {
      container.innerHTML = '<div class="empty-state">Nenhum checkpoint de experiência vencendo em breve.</div>';
      return;
    }

    container.innerHTML = criticos
      .map((c) => {
        const situacao = c.dias_restantes < 0 ? `vencido há ${Math.abs(c.dias_restantes)} dia(s)` : `em ${c.dias_restantes} dia(s)`;
        const cor = c.dias_restantes < 0 ? 'vencido' : 'proximo';
        return `
          <div class="lembrete-item">
            <span class="aso-badge ${cor}" style="min-width: 70px; text-align: center;">${c.checkpoint}</span>
            <span>${c.colaborador_nome}</span>
            <span class="meta">${c.empresa_nome}</span>
            <span class="lembrete-anos">${formatarDataExperiencia(c.data_checkpoint)} · ${situacao}</span>
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
  try {
    const [resumo, tiposEStatus] = await Promise.all([
      Shell.chamarApi('/dashboard/resumo'),
      Shell.chamarApi('/chamados-tipos'),
    ]);
    if (resumo === null) return;
    TIPOS_CHAMADO = tiposEStatus ? tiposEStatus.tipos : [];

    const cards = document.querySelectorAll('#kpi-grid .kpi-card .value');
    cards[0].textContent = resumo.total_empresas;
    cards[1].textContent = resumo.total_clientes;
    cards[2].textContent = resumo.total_colaboradores;
    cards[3].textContent = resumo.total_usuarios;
    cards[4].textContent = resumo.total_chamados_abertos;

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
