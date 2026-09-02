const auth = Shell.montar('relatorios', 'Relatórios');

let abaAtual = 'geral';
let dadosAtuais = null;
let clientesCache = null;
let colaboradoresCache = null;

function formatarDataISO(d) {
  return d.toISOString().slice(0, 10);
}

function formatarDataBR(isoString) {
  const [ano, mes, dia] = isoString.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarMoeda(valor) {
  return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function aplicarPreset(preset) {
  const hoje = new Date();
  let inicio, fim;

  if (preset === 'hoje') {
    inicio = hoje;
    fim = hoje;
  } else if (preset === 'semana-atual') {
    const diaSemana = hoje.getDay(); // 0=domingo
    const deslocamentoSegunda = diaSemana === 0 ? 6 : diaSemana - 1;
    inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - deslocamentoSegunda);
    fim = new Date(inicio);
    fim.setDate(inicio.getDate() + 6);
  } else if (preset === 'mes-atual') {
    inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    fim = hoje;
  } else if (preset === 'mes-passado') {
    inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
    fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
  } else if (preset === 'ultimos-3-meses') {
    inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 2, 1);
    fim = hoje;
  } else if (preset === 'ano-atual') {
    inicio = new Date(hoje.getFullYear(), 0, 1);
    fim = hoje;
  }

  document.getElementById('filtro-data-inicio').value = formatarDataISO(inicio);
  document.getElementById('filtro-data-fim').value = formatarDataISO(fim);
  carregarRelatorio();
}

function montarBarras(itens, chaveLabel, chaveValor) {
  if (itens.length === 0) return '<div class="empty-state">Sem dados no período.</div>';
  const maior = Math.max(...itens.map((i) => i[chaveValor]), 1);
  return itens
    .map((item) => {
      const largura = Math.round((item[chaveValor] / maior) * 100);
      return `
      <div class="breakdown-row">
        <span class="nome-empresa">${item[chaveLabel]}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${largura}%"></div></div>
        <span class="total">${item[chaveValor]}</span>
      </div>
    `;
    })
    .join('');
}

function trocarAba(aba) {
  abaAtual = aba;
  document.querySelectorAll('.tab-relatorio').forEach((botao) => {
    botao.classList.toggle('ativa', botao.dataset.aba === aba);
  });
  document.getElementById('campo-select-cliente').hidden = aba !== 'cliente' && aba !== 'horas';
  document.getElementById('campo-select-colaborador').hidden = aba !== 'colaborador' && aba !== 'faltas' && aba !== 'horas';
  carregarRelatorio();
}

async function carregarListasSelect() {
  if (!clientesCache) {
    clientesCache = await Shell.chamarApi('/clientes-dados');
    document.getElementById('filtro-cliente').innerHTML =
      '<option value="">Todos</option>' +
      clientesCache.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  }
  if (!colaboradoresCache) {
    colaboradoresCache = await Shell.chamarApi('/colaboradores-dados');
    document.getElementById('filtro-colaborador').innerHTML =
      '<option value="">Todos</option>' +
      colaboradoresCache.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  }
}

function renderizarGeral(dados) {
  const container = document.getElementById('relatorio-conteudo');
  const c = dados.chamados;
  const p = dados.colaboradores;
  const v = dados.veiculos;
  const cl = dados.clientes;

  const linhasCustoVeiculo = v.custo_por_veiculo
    .map((item) => `<tr><td>${item.veiculo}</td><td>${item.total_manutencoes}</td><td>${formatarMoeda(item.custo)}</td></tr>`)
    .join('');
  const linhasTopClientes = c.top_clientes.map((item) => `<tr><td>${item.cliente}</td><td>${item.total}</td></tr>`).join('');
  const linhasTopSupervisores = c.top_supervisores
    .map((item) => `<tr><td>${item.supervisor}</td><td>${item.total}</td></tr>`)
    .join('');

  container.innerHTML = `
    <div class="meta" style="margin-bottom: 20px;">Período: ${formatarDataBR(dados.periodo.inicio)} até ${formatarDataBR(dados.periodo.fim)}</div>

    <div class="section-title">Chamados</div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">abertos no período</div><div class="value">${c.total_abertos}</div></div>
      <div class="kpi-card"><div class="label">finalizados no período</div><div class="value">${c.total_finalizados}</div></div>
      <div class="kpi-card"><div class="label">tempo médio de resolução</div><div class="value">${c.tempo_medio_horas !== null ? c.tempo_medio_horas + 'h' : '—'}</div></div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 20px;">
      <div><div class="lembrete-subtitulo">Por tipo</div>${montarBarras(c.por_tipo, 'tipo', 'total')}</div>
      <div><div class="lembrete-subtitulo">Por prioridade</div>${montarBarras(c.por_prioridade, 'prioridade', 'total')}</div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 24px;">
      <div>
        <div class="lembrete-subtitulo">Clientes com mais chamados</div>
        ${c.top_clientes.length > 0 ? `<table class="table-list"><thead><tr><th>Cliente</th><th>Chamados</th></tr></thead><tbody>${linhasTopClientes}</tbody></table>` : '<div class="empty-state">Sem dados no período.</div>'}
      </div>
      <div>
        <div class="lembrete-subtitulo">Supervisores que mais finalizaram</div>
        ${c.top_supervisores.length > 0 ? `<table class="table-list"><thead><tr><th>Supervisor</th><th>Finalizados</th></tr></thead><tbody>${linhasTopSupervisores}</tbody></table>` : '<div class="empty-state">Sem dados no período.</div>'}
      </div>
    </div>

    <div class="section-title" style="margin-top: 36px;">Colaboradores</div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total ativos</div><div class="value">${p.total_ativos}</div></div>
      <div class="kpi-card"><div class="label">admissões no período</div><div class="value">${p.admissoes_periodo}</div></div>
      <div class="kpi-card"><div class="label">faltas no período</div><div class="value">${p.faltas_periodo}</div></div>
      <div class="kpi-card"><div class="label">advertências no período</div><div class="value">${p.advertencias_periodo}</div></div>
      <div class="kpi-card"><div class="label">ASOs vencidos agora</div><div class="value">${p.asos_vencidos_atual}</div></div>
    </div>

    <div class="section-title" style="margin-top: 36px;">Frota</div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">custo total no período</div><div class="value" style="font-size: 26px;">${formatarMoeda(v.custo_total_periodo)}</div></div>
      ${v.manutencoes_por_tipo.map((item) => `<div class="kpi-card"><div class="label">${item.tipo.toLowerCase()}s</div><div class="value">${item.total}</div></div>`).join('')}
    </div>
    <div style="margin-top: 16px;">
      ${v.custo_por_veiculo.length > 0 ? `<table class="table-list"><thead><tr><th>Veículo</th><th>Manutenções</th><th>Custo</th></tr></thead><tbody>${linhasCustoVeiculo}</tbody></table>` : '<div class="empty-state">Nenhuma manutenção registrada no período.</div>'}
    </div>

    <div class="section-title" style="margin-top: 36px;">Clientes</div>
    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total ativos</div><div class="value">${cl.total_ativos}</div></div>
      <div class="kpi-card"><div class="label">novos no período</div><div class="value">${cl.novos_periodo}</div></div>
    </div>
  `;
}

function renderizarPorCliente(dados) {
  const container = document.getElementById('relatorio-conteudo');

  const linhasChamados = dados.chamados
    .map(
      (c) => `
      <tr>
        <td>${formatarDataBR(c.data)}</td>
        <td>${c.tipo}</td>
        <td>${c.prioridade}</td>
        <td>${c.status}</td>
        <td>${c.responsavel}</td>
        <td>${c.descricao}</td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <div class="meta" style="margin-bottom: 8px;">Período: ${formatarDataBR(dados.periodo.inicio)} até ${formatarDataBR(dados.periodo.fim)}</div>
    <h2 style="margin: 0 0 4px;">${dados.cliente.nome}</h2>
    <div class="meta" style="margin-bottom: 20px;">${dados.cliente.empresa_nome}</div>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total de chamados</div><div class="value">${dados.total_chamados}</div></div>
      <div class="kpi-card"><div class="label">tempo médio de resolução</div><div class="value">${dados.tempo_medio_horas !== null ? dados.tempo_medio_horas + 'h' : '—'}</div></div>
      <div class="kpi-card"><div class="label">colaboradores que atendem</div><div class="value" style="font-size: 22px;">${dados.quem_atende.length}</div></div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 32px; margin-top: 24px;">
      <div><div class="lembrete-subtitulo">Por tipo</div>${montarBarras(dados.por_tipo, 'tipo', 'total')}</div>
      <div><div class="lembrete-subtitulo">Por status</div>${montarBarras(dados.por_status, 'status', 'total')}</div>
      <div><div class="lembrete-subtitulo">Por prioridade</div>${montarBarras(dados.por_prioridade, 'prioridade', 'total')}</div>
    </div>

    ${dados.quem_atende.length > 0 ? `<div class="meta" style="margin-top: 20px;">Atendido por: ${dados.quem_atende.join(', ')}</div>` : ''}

    <div class="section-title" style="margin-top: 30px;">Chamados no período</div>
    ${
      dados.chamados.length > 0
        ? `<table class="table-list"><thead><tr><th>Data</th><th>Tipo</th><th>Prioridade</th><th>Status</th><th>Responsável</th><th>Descrição</th></tr></thead><tbody>${linhasChamados}</tbody></table>`
        : '<div class="empty-state">Nenhum chamado nesse período.</div>'
    }
  `;
}

function renderizarPorColaborador(dados) {
  const container = document.getElementById('relatorio-conteudo');

  const linhasEventos = dados.eventos
    .map((e) => `<tr><td>${formatarDataBR(e.data)}</td><td>${e.tipo}</td><td>${e.descricao}</td><td>${e.registrado_por}</td></tr>`)
    .join('');

  container.innerHTML = `
    <div class="meta" style="margin-bottom: 8px;">Período: ${formatarDataBR(dados.periodo.inicio)} até ${formatarDataBR(dados.periodo.fim)}</div>
    <h2 style="margin: 0 0 4px;">${dados.colaborador.nome}</h2>
    <div class="meta" style="margin-bottom: 20px;">${dados.colaborador.cargo || 'Cargo não informado'} · ${dados.colaborador.empresa_nome}</div>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total de registros</div><div class="value">${dados.total_eventos}</div></div>
    </div>

    <div style="margin-top: 24px;">
      <div class="lembrete-subtitulo">Por tipo de registro</div>
      ${montarBarras(dados.por_tipo, 'tipo', 'total')}
    </div>

    <div class="section-title" style="margin-top: 30px;">Registros no período</div>
    ${
      dados.eventos.length > 0
        ? `<table class="table-list"><thead><tr><th>Data</th><th>Tipo</th><th>Descrição</th><th>Registrado por</th></tr></thead><tbody>${linhasEventos}</tbody></table>`
        : '<div class="empty-state">Nenhum registro nesse período.</div>'
    }
  `;
}

function renderizarHorasTrabalhadas(dados) {
  const container = document.getElementById('relatorio-conteudo');

  const linhasColaborador = dados.por_colaborador
    .map((c) => `<tr><td>${c.colaborador_nome}</td><td>${c.empresa_nome}</td><td><strong>${c.horas_totais}h</strong></td></tr>`)
    .join('');

  const linhasCliente = dados.por_cliente
    .map((c) => `<tr><td>${c.cliente_nome}</td><td>${c.empresa_nome}</td><td><strong>${c.horas_totais}h</strong></td></tr>`)
    .join('');

  const linhasDetalhe = dados.por_colaborador_cliente
    .map((p) => {
      const subDetalhe = p.detalhes
        .map((d) => `${d.dia_semana} ${d.hora_inicio}-${d.hora_fim} (${d.horas_no_periodo}h)`)
        .join(' · ');
      return `
        <tr>
          <td>${p.colaborador_nome}</td>
          <td>${p.cliente_nome}</td>
          <td><strong>${p.horas_totais}h</strong></td>
          <td class="meta" style="font-size: 12px;">${subDetalhe}</td>
        </tr>
      `;
    })
    .join('');

  container.innerHTML = `
    <div class="meta" style="margin-bottom: 20px;">Período: ${formatarDataBR(dados.periodo.inicio)} até ${formatarDataBR(dados.periodo.fim)}</div>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total de horas no período</div><div class="value">${dados.total_horas}h</div></div>
      <div class="kpi-card"><div class="label">colaboradores com registro</div><div class="value">${dados.por_colaborador.length}</div></div>
      <div class="kpi-card"><div class="label">clientes atendidos</div><div class="value">${dados.por_cliente.length}</div></div>
    </div>

    <div class="section-title" style="margin-top: 30px;">Por colaborador</div>
    ${
      dados.por_colaborador.length > 0
        ? `<table class="table-list"><thead><tr><th>Colaborador</th><th>Empresa</th><th>Horas no período</th></tr></thead><tbody>${linhasColaborador}</tbody></table>`
        : '<div class="empty-state">Sem dados no período.</div>'
    }

    <div class="section-title" style="margin-top: 30px;">Por cliente</div>
    ${
      dados.por_cliente.length > 0
        ? `<table class="table-list"><thead><tr><th>Cliente</th><th>Empresa</th><th>Horas no período</th></tr></thead><tbody>${linhasCliente}</tbody></table>`
        : '<div class="empty-state">Sem dados no período.</div>'
    }

    <div class="section-title" style="margin-top: 30px;">Detalhamento colaborador × cliente</div>
    ${
      dados.por_colaborador_cliente.length > 0
        ? `<table class="table-list"><thead><tr><th>Colaborador</th><th>Cliente</th><th>Horas</th><th>Detalhe (dia/turno)</th></tr></thead><tbody>${linhasDetalhe}</tbody></table>`
        : '<div class="empty-state">Sem dados no período.</div>'
    }
  `;
}

function renderizarFaltasAtestados(dados) {
  const container = document.getElementById('relatorio-conteudo');

  const gruposHtml = dados.por_colaborador
    .map((g) => {
      const linhasEventos = g.eventos
        .map(
          (e) => `
          <tr>
            <td>${formatarDataBR(e.data)}</td>
            <td>${e.tipo}</td>
            <td>${e.descricao}</td>
            <td>${e.registrado_por}</td>
          </tr>
        `
        )
        .join('');

      return `
        <div style="margin-bottom: 28px; break-inside: avoid;">
          <div style="display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 8px;">
            <strong style="font-size: 15px;">${g.colaborador_nome}</strong>
            <span class="meta">${g.cargo || 'Cargo não informado'} · ${g.empresa_nome}</span>
            <span class="meta" style="margin-left: auto;">Faltas: <strong>${g.total_faltas}</strong> · Atestados: <strong>${g.total_atestados}</strong></span>
          </div>
          <table class="table-list">
            <thead><tr><th>Data</th><th>Tipo</th><th>Descrição</th><th>Registrado por</th></tr></thead>
            <tbody>${linhasEventos}</tbody>
          </table>
        </div>
      `;
    })
    .join('');

  container.innerHTML = `
    <div class="meta" style="margin-bottom: 20px;">Período: ${formatarDataBR(dados.periodo.inicio)} até ${formatarDataBR(dados.periodo.fim)}</div>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="label">total de faltas</div><div class="value">${dados.total_faltas}</div></div>
      <div class="kpi-card"><div class="label">total de atestados</div><div class="value">${dados.total_atestados}</div></div>
      <div class="kpi-card"><div class="label">colaboradores com ocorrência</div><div class="value">${dados.colaboradores_com_ocorrencia}</div></div>
    </div>

    <div class="section-title" style="margin-top: 30px;">Detalhamento por colaborador</div>
    ${dados.por_colaborador.length > 0 ? gruposHtml : '<div class="empty-state">Nenhuma falta ou atestado registrado nesse período.</div>'}
  `;
}

async function carregarRelatorio() {
  const container = document.getElementById('relatorio-conteudo');
  container.innerHTML = '<div class="loading-state">Carregando...</div>';

  const dataInicio = document.getElementById('filtro-data-inicio').value;
  const dataFim = document.getElementById('filtro-data-fim').value;
  const params = new URLSearchParams();
  if (dataInicio) params.set('data_inicio', dataInicio);
  if (dataFim) params.set('data_fim', dataFim);

  try {
    if (abaAtual === 'geral') {
      const dados = await Shell.chamarApi(`/relatorios-dados?${params.toString()}`);
      if (dados === null) return;
      dadosAtuais = dados;
      renderizarGeral(dados);
    } else if (abaAtual === 'cliente') {
      await carregarListasSelect();
      const clienteId = document.getElementById('filtro-cliente').value;
      if (!clienteId) {
        container.innerHTML = '<div class="empty-state">Selecione um cliente.</div>';
        return;
      }
      const dados = await Shell.chamarApi(`/relatorios-dados/cliente/${clienteId}?${params.toString()}`);
      if (dados === null) return;
      dadosAtuais = dados;
      renderizarPorCliente(dados);
    } else if (abaAtual === 'colaborador') {
      await carregarListasSelect();
      const colaboradorId = document.getElementById('filtro-colaborador').value;
      if (!colaboradorId) {
        container.innerHTML = '<div class="empty-state">Selecione um colaborador.</div>';
        return;
      }
      const dados = await Shell.chamarApi(`/relatorios-dados/colaborador/${colaboradorId}?${params.toString()}`);
      if (dados === null) return;
      dadosAtuais = dados;
      renderizarPorColaborador(dados);
    } else if (abaAtual === 'faltas') {
      await carregarListasSelect();
      const colaboradorId = document.getElementById('filtro-colaborador').value;
      if (colaboradorId) params.set('colaborador_id', colaboradorId);
      const dados = await Shell.chamarApi(`/relatorios-dados/faltas-atestados?${params.toString()}`);
      if (dados === null) return;
      dadosAtuais = dados;
      renderizarFaltasAtestados(dados);
    } else if (abaAtual === 'horas') {
      await carregarListasSelect();
      const colaboradorId = document.getElementById('filtro-colaborador').value;
      const clienteId = document.getElementById('filtro-cliente').value;
      if (colaboradorId) params.set('colaborador_id', colaboradorId);
      if (clienteId) params.set('cliente_id', clienteId);
      const dados = await Shell.chamarApi(`/relatorios-dados/horas-trabalhadas?${params.toString()}`);
      if (dados === null) return;
      dadosAtuais = dados;
      renderizarHorasTrabalhadas(dados);
    }
  } catch (erro) {
    if (erro.status === 403) {
      container.innerHTML = '<div class="empty-state">Esta área é restrita à equipe do escritório.</div>';
      return;
    }
    container.innerHTML = '<div class="empty-state">Não foi possível carregar o relatório agora.</div>';
  }
}

function baixarCSV(nomeArquivo, cabecalhos, linhas) {
  const escapar = (valor) => `"${String(valor ?? '').replace(/"/g, '""')}"`;
  const conteudo = [cabecalhos.map(escapar).join(';'), ...linhas.map((linha) => linha.map(escapar).join(';'))].join('\r\n');
  const blob = new Blob(['\uFEFF' + conteudo], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nomeArquivo;
  link.click();
  URL.revokeObjectURL(url);
}

function exportarCSV() {
  if (!dadosAtuais) return;

  if (abaAtual === 'geral') {
    const linhas = [
      ['Chamados abertos no período', dadosAtuais.chamados.total_abertos],
      ['Chamados finalizados no período', dadosAtuais.chamados.total_finalizados],
      ['Tempo médio de resolução (h)', dadosAtuais.chamados.tempo_medio_horas ?? '—'],
      ['Colaboradores ativos', dadosAtuais.colaboradores.total_ativos],
      ['Admissões no período', dadosAtuais.colaboradores.admissoes_periodo],
      ['Faltas no período', dadosAtuais.colaboradores.faltas_periodo],
      ['Advertências no período', dadosAtuais.colaboradores.advertencias_periodo],
      ['ASOs vencidos agora', dadosAtuais.colaboradores.asos_vencidos_atual],
      ['Custo total de manutenção no período', formatarMoeda(dadosAtuais.veiculos.custo_total_periodo)],
      ['Clientes ativos', dadosAtuais.clientes.total_ativos],
      ['Novos clientes no período', dadosAtuais.clientes.novos_periodo],
    ];
    baixarCSV('relatorio-geral.csv', ['Indicador', 'Valor'], linhas);
  } else if (abaAtual === 'cliente') {
    const linhas = dadosAtuais.chamados.map((c) => [c.data, c.tipo, c.prioridade, c.status, c.responsavel, c.descricao]);
    baixarCSV(
      `relatorio-${dadosAtuais.cliente.nome}.csv`,
      ['Data', 'Tipo', 'Prioridade', 'Status', 'Responsável', 'Descrição'],
      linhas
    );
  } else if (abaAtual === 'colaborador') {
    const linhas = dadosAtuais.eventos.map((e) => [e.data, e.tipo, e.descricao, e.registrado_por]);
    baixarCSV(`relatorio-${dadosAtuais.colaborador.nome}.csv`, ['Data', 'Tipo', 'Descrição', 'Registrado por'], linhas);
  } else if (abaAtual === 'faltas') {
    const linhas = [];
    dadosAtuais.por_colaborador.forEach((g) => {
      g.eventos.forEach((e) => {
        linhas.push([g.colaborador_nome, g.empresa_nome, e.data, e.tipo, e.descricao, e.registrado_por]);
      });
    });
    baixarCSV(
      'relatorio-faltas-e-atestados.csv',
      ['Colaborador', 'Empresa', 'Data', 'Tipo', 'Descrição', 'Registrado por'],
      linhas
    );
  } else if (abaAtual === 'horas') {
    const linhas = dadosAtuais.por_colaborador_cliente.map((p) => [p.colaborador_nome, p.cliente_nome, p.horas_totais]);
    baixarCSV('relatorio-horas-trabalhadas.csv', ['Colaborador', 'Cliente', 'Horas no período'], linhas);
  }
}

document.querySelectorAll('.tab-relatorio').forEach((botao) => {
  botao.addEventListener('click', () => trocarAba(botao.dataset.aba));
});
document.querySelectorAll('.periodo-preset').forEach((botao) => {
  botao.addEventListener('click', () => aplicarPreset(botao.dataset.preset));
});
document.getElementById('btn-aplicar-periodo').addEventListener('click', carregarRelatorio);
document.getElementById('filtro-cliente').addEventListener('change', carregarRelatorio);
document.getElementById('filtro-colaborador').addEventListener('change', carregarRelatorio);
document.getElementById('btn-exportar-pdf').addEventListener('click', () => window.print());
document.getElementById('btn-exportar-csv').addEventListener('click', exportarCSV);

aplicarPreset('mes-atual');
