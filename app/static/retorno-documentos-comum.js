// Pecas compartilhadas do Retorno de documentos: a etiqueta de cada documento
// (OK / F / X / pendente) e o modal de marcar. Usado pela tela do
// colaborador e pelo painel do mes (retorno-documentos.js). Carregar
// depois do shell.js.
const RetornoDoc = (() => {
  const SIGLAS = { ok: 'OK', faltando: 'F', nao_se_aplica: 'X' };
  const LABELS = { ok: 'Entregue', faltando: 'Faltando parte', nao_se_aplica: 'Não se aplica' };

  function escapar(texto) {
    const div = document.createElement('div');
    div.textContent = texto == null ? '' : String(texto);
    return div.innerHTML;
  }

  function dataHoraBR(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function dica(documentoLabel, celula) {
    const partes = [documentoLabel, celula.situacao ? LABELS[celula.situacao] : celula.em_falta ? 'Pendente (em falta)' : 'Pendente'];
    if (celula.observacao) partes.push(`Obs.: ${celula.observacao}`);
    if (celula.atualizado_por) partes.push(`Marcado por ${celula.atualizado_por} em ${dataHoraBR(celula.atualizado_em)}`);
    return partes.join(' · ');
  }

  // dados = atributos data-* que identificam a celula (colaborador, ano, mes, documento)
  function etiquetaHtml(documentoLabel, celula, dados, podeMarcar) {
    const situacao = celula.situacao || 'pendente';
    const classes = ['ret-chip', `ret-${situacao}`];
    if (celula.em_falta) classes.push('ret-em-falta');
    if (celula.observacao) classes.push('ret-com-obs');
    const atributos = Object.entries(dados)
      .map(([chave, valor]) => `data-${chave}="${escapar(valor)}"`)
      .join(' ');
    const texto = SIGLAS[celula.situacao] || (celula.em_falta ? '!' : '—');
    return `<button type="button" class="${classes.join(' ')}" ${atributos} title="${escapar(dica(documentoLabel, celula))}"${podeMarcar ? '' : ' disabled'}>${texto}</button>`;
  }

  let contexto = null;

  function montarModal() {
    if (document.getElementById('ret-modal-overlay')) return;
    const opcoes = [
      ['ok', 'OK', 'Entregue'],
      ['faltando', 'F', 'Faltando parte'],
      ['nao_se_aplica', 'X', 'Não se aplica neste mês'],
      ['', '—', 'Pendente (ainda não voltou)'],
    ]
      .map(
        ([valor, sigla, label]) => `
        <label class="ret-opcao">
          <input type="radio" name="ret-situacao" value="${valor}">
          <span class="ret-chip ret-${valor || 'pendente'}">${sigla}</span>
          <span>${label}</span>
        </label>`
      )
      .join('');
    document.body.insertAdjacentHTML(
      'beforeend',
      `
      <div class="modal-overlay" id="ret-modal-overlay" hidden>
        <div class="modal">
          <div class="modal-header">
            <h3 id="ret-modal-titulo">Documento</h3>
            <button class="modal-close" id="ret-modal-fechar" aria-label="Fechar">&times;</button>
          </div>
          <form id="ret-form">
            <div class="meta" id="ret-modal-colaborador" style="margin-bottom: 12px;"></div>
            <div class="ret-opcoes">${opcoes}</div>
            <div class="field">
              <label for="ret-observacao">Observação (o que está faltando, rasurado, não assinou...)</label>
              <input type="text" id="ret-observacao" maxlength="300">
            </div>
            <div class="meta" id="ret-modal-historico"></div>
            <div class="error-message" id="ret-modal-erro"></div>
            <button type="submit" class="btn-primary" id="ret-modal-enviar">Salvar</button>
          </form>
        </div>
      </div>`
    );
    const overlay = document.getElementById('ret-modal-overlay');
    document.getElementById('ret-modal-fechar').addEventListener('click', () => { overlay.hidden = true; });
    overlay.addEventListener('click', (evento) => {
      if (evento.target === overlay) overlay.hidden = true;
    });
    document.getElementById('ret-form').addEventListener('submit', salvar);
  }

  // info = { colaboradorId, colaboradorNome, ano, mes, documento, documentoLabel, celula }
  function abrir(info, aoSalvar) {
    montarModal();
    contexto = { info, aoSalvar };
    const { celula } = info;
    document.getElementById('ret-modal-titulo').textContent = info.documentoLabel;
    document.getElementById('ret-modal-colaborador').textContent = info.colaboradorNome || '';
    // abrindo um pendente, ja deixa "Entregue" escolhido: e o caso mais comum
    const marcada = celula.situacao || 'ok';
    document.querySelectorAll('input[name="ret-situacao"]').forEach((radio) => {
      radio.checked = radio.value === marcada;
    });
    document.getElementById('ret-observacao').value = celula.observacao || '';
    document.getElementById('ret-modal-historico').textContent = celula.atualizado_por
      ? `Última marcação: ${celula.atualizado_por}, ${dataHoraBR(celula.atualizado_em)}`
      : '';
    document.getElementById('ret-modal-erro').classList.remove('visible');
    document.getElementById('ret-modal-overlay').hidden = false;
  }

  async function salvar(evento) {
    evento.preventDefault();
    const { info, aoSalvar } = contexto;
    const erroBox = document.getElementById('ret-modal-erro');
    const botao = document.getElementById('ret-modal-enviar');
    const escolhida = document.querySelector('input[name="ret-situacao"]:checked');
    erroBox.classList.remove('visible');
    botao.disabled = true;
    botao.textContent = 'Salvando...';
    try {
      const resposta = await Shell.chamarApi('/retorno-documentos-dados/marcar', {
        method: 'PUT',
        body: {
          colaborador_id: Number(info.colaboradorId),
          ano: Number(info.ano),
          mes: Number(info.mes),
          documento: info.documento,
          situacao: escolhida && escolhida.value ? escolhida.value : null,
          observacao: document.getElementById('ret-observacao').value || null,
        },
      });
      if (resposta === null) return;
      document.getElementById('ret-modal-overlay').hidden = true;
      aoSalvar(resposta);
    } catch (erro) {
      erroBox.textContent = erro.detalhe || 'Não foi possível salvar agora.';
      erroBox.classList.add('visible');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Salvar';
    }
  }

  async function marcarTodos(colaboradorId, ano, mes) {
    return Shell.chamarApi('/retorno-documentos-dados/marcar-todos', {
      method: 'POST',
      body: { colaborador_id: Number(colaboradorId), ano: Number(ano), mes: Number(mes), situacao: 'ok' },
    });
  }

  return { escapar, etiquetaHtml, abrir, marcarTodos };
})();
