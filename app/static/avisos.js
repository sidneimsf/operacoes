const auth = Shell.montar('avisos', 'Avisos');

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

function montarModalAviso() {
  const html = `
    <div class="modal-overlay" id="aviso-modal-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Cadastrar aviso</h3>
          <button class="modal-close" id="aviso-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="aviso-form">
          <div class="field">
            <label for="aviso-mensagem">Mensagem</label>
            <textarea id="aviso-mensagem" rows="4" required placeholder="Ex: Flavio solicitou reunião com todos no dia 04/09"></textarea>
          </div>
          <div class="field">
            <label>Enviar para</label>
            <div class="radio-group">
              <label><input type="radio" name="aviso-destino" value="todos" checked> Todos</label>
              <label><input type="radio" name="aviso-destino" value="pessoa"> Pessoas específicas</label>
            </div>
          </div>
          <div class="field" id="campo-destinatario" hidden>
            <label>Quem? (marque uma ou mais)</label>
            <div id="aviso-lista-destinatarios" class="lista-checkboxes"></div>
          </div>
          <div class="error-message" id="aviso-modal-erro"></div>
          <button type="submit" class="btn-primary" id="aviso-modal-enviar">Publicar aviso</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('aviso-modal-fechar').addEventListener('click', fecharModalAviso);
  document.getElementById('aviso-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'aviso-modal-overlay') fecharModalAviso();
  });

  document.querySelectorAll('input[name="aviso-destino"]').forEach((radio) => {
    radio.addEventListener('change', (evento) => {
      document.getElementById('campo-destinatario').hidden = evento.target.value !== 'pessoa';
    });
  });

  document.getElementById('aviso-form').addEventListener('submit', enviarAviso);
}

async function abrirModalAviso() {
  document.getElementById('aviso-form').reset();
  document.getElementById('campo-destinatario').hidden = true;
  document.getElementById('aviso-modal-erro').classList.remove('visible');

  const pessoas = await Shell.chamarApi('/pessoas');
  const listaDestinatarios = document.getElementById('aviso-lista-destinatarios');
  listaDestinatarios.innerHTML =
    `<label class="checkbox-linha"><input type="checkbox" value="${auth.id}"> Eu mesmo (lembrete pessoal)</label>` +
    pessoas
      .filter((p) => p.id !== auth.id)
      .map((p) => `<label class="checkbox-linha"><input type="checkbox" value="${p.id}"> ${p.nome} (${p.papel})</label>`)
      .join('');

  document.getElementById('aviso-modal-overlay').hidden = false;
}

function fecharModalAviso() {
  document.getElementById('aviso-modal-overlay').hidden = true;
}

async function enviarAviso(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('aviso-modal-erro');
  const botao = document.getElementById('aviso-modal-enviar');
  erroBox.classList.remove('visible');

  const destino = document.querySelector('input[name="aviso-destino"]:checked').value;

  let destinatarioIds = null;
  if (destino === 'pessoa') {
    destinatarioIds = Array.from(document.querySelectorAll('#aviso-lista-destinatarios input:checked')).map((c) => Number(c.value));
    if (destinatarioIds.length === 0) {
      erroBox.textContent = 'Marque ao menos uma pessoa.';
      erroBox.classList.add('visible');
      return;
    }
  }

  const corpo = {
    mensagem: document.getElementById('aviso-mensagem').value,
    destinatario_ids: destinatarioIds,
  };

  botao.disabled = true;
  botao.textContent = 'Publicando...';

  try {
    await Shell.chamarApi('/avisos-dados', { method: 'POST', body: corpo });
    fecharModalAviso();
    carregarAvisos();
  } catch (erro) {
    erroBox.textContent = erro.detalhe || 'Não foi possível publicar o aviso agora.';
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Publicar aviso';
  }
}

function formatarData(isoString) {
  const data = new Date(isoString);
  const dataFormatada = data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  const horaFormatada = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${dataFormatada} · ${horaFormatada}`;
}

function agruparAvisos(avisos) {
  // Ordena por mensagem+remetente+data, pra que avisos do mesmo "envio em lote"
  // fiquem em sequencia mesmo que o timestamp exato varie por alguns milissegundos
  const ordenados = [...avisos].sort((a, b) => {
    if (a.mensagem !== b.mensagem) return a.mensagem < b.mensagem ? -1 : 1;
    if (a.criado_por_id !== b.criado_por_id) return a.criado_por_id - b.criado_por_id;
    return new Date(a.criado_em) - new Date(b.criado_em);
  });

  const JANELA_MESMO_ENVIO_MS = 10000; // avisos criados a menos de 10s um do outro, com mesma mensagem/remetente, sao o mesmo envio
  const grupos = [];
  let grupoAtual = null;

  ordenados.forEach((a) => {
    const pertenceAoGrupoAtual =
      grupoAtual &&
      grupoAtual.mensagem === a.mensagem &&
      grupoAtual.criado_por_id === a.criado_por_id &&
      Math.abs(new Date(a.criado_em) - new Date(grupoAtual.ultimoCriadoEm)) <= JANELA_MESMO_ENVIO_MS;

    if (pertenceAoGrupoAtual) {
      grupoAtual.ids.push(a.id);
      if (a.destinatario_nome) grupoAtual.destinatarios.push(a.destinatario_nome);
      grupoAtual.ultimoCriadoEm = a.criado_em;
    } else {
      grupoAtual = {
        ids: [a.id],
        mensagem: a.mensagem,
        criado_por_nome: a.criado_por_nome,
        criado_por_id: a.criado_por_id,
        criado_em: a.criado_em,
        ultimoCriadoEm: a.criado_em,
        destinatarios: a.destinatario_nome ? [a.destinatario_nome] : [],
      };
      grupos.push(grupoAtual);
    }
  });

  // Reordena os grupos do mais recente pro mais antigo, pra manter a ordem esperada no mural
  grupos.sort((a, b) => new Date(b.criado_em) - new Date(a.criado_em));
  return grupos;
}

function renderizarMural(avisos) {
  const container = document.getElementById('mural');

  if (avisos.length === 0) {
    container.innerHTML = '<div class="empty-state">Nenhum aviso ainda. Seja o primeiro a publicar algo no mural.</div>';
    return;
  }

  const grupos = agruparAvisos(avisos);

  container.innerHTML = grupos
    .map((g) => {
      const podeExcluir = g.criado_por_id === auth.id || auth.papel === 'escritorio';
      const textoDestinatarios = g.destinatarios.length > 0 ? g.destinatarios.join(', ') : null;
      return `
      <div class="postit">
        <div class="pin"></div>
        ${podeExcluir ? `<button class="postit-excluir" data-aviso-ids="${g.ids.join(',')}" aria-label="Excluir aviso" title="Excluir">&times;</button>` : ''}
        <div class="mensagem">${escaparHtml(g.mensagem)}</div>
        <div class="rodape">
          <span>${g.criado_por_nome} · ${formatarData(g.criado_em)}</span>
          ${textoDestinatarios ? `<span class="destinatario-tag">Para: ${escaparHtml(textoDestinatarios)}</span>` : ''}
        </div>
      </div>
    `;
    })
    .join('');
}

async function excluirAviso(avisoIds) {
  if (!confirm('Excluir este aviso do mural?')) return;
  try {
    await Promise.all(avisoIds.map((id) => Shell.chamarApi(`/avisos-dados/${id}`, { method: 'DELETE' })));
    carregarAvisos();
  } catch (erro) {
    alert('Não foi possível excluir o aviso agora.');
  }
}

async function carregarAvisos() {
  const container = document.getElementById('mural');
  container.innerHTML = '<div class="loading-state">Carregando avisos...</div>';
  try {
    const avisos = await Shell.chamarApi('/avisos-dados');
    if (avisos === null) return;
    renderizarMural(avisos);
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar os avisos agora.</div>';
  }
}

async function marcarAvisosComoVistos() {
  try {
    await Shell.chamarApi('/avisos-dados/marcar-vistos', { method: 'POST' });
    Shell.atualizarBadgeAvisos();
  } catch (erro) {
    // silencioso - nao impede o uso da tela
  }
}

montarModalAviso();
document.getElementById('btn-novo-aviso').addEventListener('click', abrirModalAviso);

document.getElementById('mural').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.postit-excluir');
  if (!botao) return;
  excluirAviso(botao.dataset.avisoIds.split(',').map(Number));
});

carregarAvisos();
marcarAvisosComoVistos();
