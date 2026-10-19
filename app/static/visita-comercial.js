const auth = Shell.montar('visita-comercial', 'Visita Comercial');
const ehEscritorio = !!auth && auth.papel === 'escritorio';

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

function formatarDataBR(isoString) {
  if (!isoString) return '—';
  const [ano, mes, dia] = isoString.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarDataHoraBR(isoString) {
  return new Date(isoString).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarDuracao(segundos) {
  const total = Math.round(segundos || 0);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

function hojeIso() {
  const agora = new Date();
  agora.setMinutes(agora.getMinutes() - agora.getTimezoneOffset());
  return agora.toISOString().slice(0, 10);
}

let opcoesVisita = { origens: [], status: [], tipos_servico: [] };
let empresasCache = [];
let pessoasCache = [];
let supervisoresCache = [];
let podeConverterCliente = false;
let visitasCompletas = [];

// campo da visita -> id do input no formulario (usado tambem pra receber o que o audio preencheu)
const CAMPOS_FORMULARIO = {
  nome_local: 'vc-nome-local',
  bairro: 'vc-bairro',
  cidade: 'vc-cidade',
  data_visita: 'vc-data-visita',
  contato_nome: 'vc-contato-nome',
  contato_cargo: 'vc-contato-cargo',
  contato_telefone: 'vc-contato-telefone',
  contato_email: 'vc-contato-email',
  tipo_servico: 'vc-tipo-servico',
  qtd_postos: 'vc-qtd-postos',
  horarios: 'vc-horarios',
  valor_estimado: 'vc-valor',
  observacoes: 'vc-observacoes',
  proximo_passo: 'vc-proximo-passo',
  data_retorno: 'vc-data-retorno',
  motivo_perda: 'vc-motivo-perda',
};

const ROTULOS_CAMPOS = {
  nome_local: 'nome do local',
  bairro: 'bairro',
  cidade: 'cidade',
  contato_nome: 'contato',
  contato_cargo: 'cargo',
  contato_telefone: 'telefone',
  contato_email: 'e-mail',
  tipo_servico: 'tipo de serviço',
  qtd_postos: 'postos',
  horarios: 'horários',
  valor_estimado: 'valor',
  data_retorno: 'data de retorno',
};

function opcoesHtml(lista, valorVazio) {
  const vazio = valorVazio ? `<option value="">${valorVazio}</option>` : '';
  return vazio + lista.map((item) => `<option value="${item.chave}">${escaparHtml(item.label)}</option>`).join('');
}

function temAudioTranscrevendo(visita) {
  return visita.audios.some((a) => ['pendente', 'processando'].includes(a.status_transcricao));
}

// ---------------------------------------------------------------------------
// Resumo (funil) e filtros
// ---------------------------------------------------------------------------

function renderizarResumo() {
  const contar = (...status) => visitasCompletas.filter((v) => status.includes(v.status)).length;
  const emNegociacao = visitasCompletas.filter((v) => ['visitada', 'proposta_enviada'].includes(v.status));
  const valorEmNegociacao = emNegociacao.reduce((soma, v) => soma + (v.valor_estimado || 0), 0);

  const card = (label, valor) => `
    <div class="kpi-card"><div><div class="label">${label}</div><div class="value">${valor}</div></div></div>
  `;
  document.getElementById('vc-resumo').innerHTML = [
    card('solicitadas', contar('solicitada')),
    card('em negociação', emNegociacao.length),
    card('valor em negociação', formatarMoeda(valorEmNegociacao)),
    card('fechadas', contar('fechada')),
    card('perdidas', contar('perdida')),
  ].join('');
}

function preencherFiltros() {
  document.getElementById('vc-filtro-status').innerHTML = opcoesHtml(opcoesVisita.status, 'Todos');
  if (ehEscritorio) {
    document.getElementById('vc-filtro-responsavel').innerHTML =
      '<option value="">Todos</option>' +
      pessoasCache.map((p) => `<option value="${p.id}">${escaparHtml(p.nome)}</option>`).join('');
    document.getElementById('vc-campo-filtro-responsavel').hidden = false;
  }

  ['vc-filtro-busca', 'vc-filtro-status', 'vc-filtro-responsavel'].forEach((id) => {
    document.getElementById(id).addEventListener('input', aplicarFiltros);
  });
}

function aplicarFiltros() {
  const termo = document.getElementById('vc-filtro-busca').value.trim().toLowerCase();
  const statusFiltro = document.getElementById('vc-filtro-status').value;
  const responsavelFiltro = document.getElementById('vc-filtro-responsavel').value;

  const filtradas = visitasCompletas.filter((v) => {
    if (statusFiltro && v.status !== statusFiltro) return false;
    if (responsavelFiltro && v.responsavel_id !== Number(responsavelFiltro)) return false;
    if (termo) {
      const alvo = `${v.nome_local} ${v.cidade || ''} ${v.bairro || ''} ${v.contato_nome || ''}`.toLowerCase();
      if (!alvo.includes(termo)) return false;
    }
    return true;
  });
  renderizarVisitas(filtradas);
}

// ---------------------------------------------------------------------------
// Lista
// ---------------------------------------------------------------------------

let timerAtualizarLista = null;

async function carregarVisitas() {
  const container = document.getElementById('lista-visitas-comerciais');
  try {
    const visitas = await Shell.chamarApi('/visitas-comerciais-dados');
    if (visitas === null) return;
    visitasCompletas = visitas;
    renderizarResumo();
    aplicarFiltros();
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar as visitas agora.</div>';
    return;
  }

  // enquanto algum audio estiver sendo transcrito, a lista se atualiza sozinha
  clearTimeout(timerAtualizarLista);
  if (visitasCompletas.some(temAudioTranscrevendo)) {
    timerAtualizarLista = setTimeout(() => {
      const algumModalAberto = !document.getElementById('vc-modal-overlay').hidden
        || !document.getElementById('vc-converter-overlay').hidden;
      if (algumModalAberto) {
        timerAtualizarLista = setTimeout(carregarVisitas, 20000);
      } else {
        carregarVisitas();
      }
    }, 20000);
  }
}

function sinalizacoesHtml(v) {
  const sinais = [];
  if (temAudioTranscrevendo(v)) sinais.push('<span class="priority-badge normal">🎙 Transcrevendo áudio</span>');
  if (v.retorno_vencido) sinais.push('<span class="priority-badge urgente">Retorno vencido</span>');
  if (v.status === 'solicitada' && v.responsavel_id === auth.id && v.criado_por_id !== auth.id) {
    sinais.push('<span class="priority-badge urgente">Pendente pra você</span>');
  }
  return sinais.length ? `<div class="vc-sinais">${sinais.join('')}</div>` : '';
}

function renderizarVisitas(visitas) {
  const container = document.getElementById('lista-visitas-comerciais');
  if (visitas.length === 0) {
    container.innerHTML = visitasCompletas.length === 0
      ? '<div class="empty-state">Nenhuma visita comercial cadastrada ainda.</div>'
      : '<div class="empty-state">Nenhuma visita encontrada com esses filtros.</div>';
    return;
  }

  const linhas = visitas
    .map((v) => {
      const local = [v.bairro, v.cidade].filter(Boolean).join(' · ');
      const contato = v.contato_nome
        ? `${escaparHtml(v.contato_nome)}${v.contato_cargo ? ` <span class="meta">(${escaparHtml(v.contato_cargo)})</span>` : ''}`
        : '—';
      const telefone = v.contato_telefone
        ? `<div><a href="${Shell.linkWhatsApp(v.contato_telefone)}" target="_blank" rel="noopener">${escaparHtml(v.contato_telefone)}</a></div>`
        : '';
      const extras = [
        v.audios.length ? `🎙 ${v.audios.length}` : '',
        v.anexos.length ? `📎 ${v.anexos.length}` : '',
      ].filter(Boolean).join(' · ');
      const podeExcluir = ehEscritorio || v.criado_por_id === auth.id;
      const podeConverter = podeConverterCliente && !v.cliente_id && v.status !== 'perdida';
      return `
      <tr>
        <td>
          <strong>${escaparHtml(v.nome_local)}</strong>
          ${local ? `<div class="meta">${escaparHtml(local)}</div>` : ''}
          ${sinalizacoesHtml(v)}
        </td>
        <td><span class="vc-status ${v.status}">${escaparHtml(v.status_label)}</span></td>
        <td>${v.data_visita ? formatarDataBR(v.data_visita) : '<span class="meta">a visitar</span>'}</td>
        <td>${contato}${telefone}</td>
        <td>${escaparHtml(v.tipo_servico_label || '—')}${v.qtd_postos ? `<div class="meta">${v.qtd_postos} posto(s)</div>` : ''}</td>
        <td>${v.valor_estimado != null ? formatarMoeda(v.valor_estimado) : '—'}</td>
        <td>${escaparHtml(v.responsavel_nome)}${extras ? `<div class="meta">${extras}</div>` : ''}</td>
        <td class="celula-acoes-tabela">
          <button class="btn-ghost btn-editar-vc" data-id="${v.id}">Abrir</button>
          ${v.cliente_id ? `<a class="btn-ghost" href="/cliente-detalhe?id=${v.cliente_id}">Ver cliente</a>` : ''}
          ${podeConverter ? `<button class="btn-ghost btn-converter-vc" data-id="${v.id}" style="color: var(--success);">Converter em cliente</button>` : ''}
          ${podeExcluir ? `<button class="btn-ghost btn-excluir-vc" data-id="${v.id}" style="color: var(--danger);">Excluir</button>` : ''}
        </td>
      </tr>
    `;
    })
    .join('');

  container.innerHTML = `
    <div class="table-scroll-wrapper"><table class="table-list">
      <thead><tr><th>Local</th><th>Status</th><th>Visita</th><th>Contato</th><th>Serviço</th><th>Valor estimado</th><th>Responsável</th><th>Gerenciar</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table></div>
  `;

  const buscar = (id) => visitasCompletas.find((v) => v.id === Number(id));
  container.querySelectorAll('.btn-editar-vc').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalEditarVisita(buscar(botao.dataset.id)));
  });
  container.querySelectorAll('.btn-converter-vc').forEach((botao) => {
    botao.addEventListener('click', () => abrirModalConverter(buscar(botao.dataset.id)));
  });
  container.querySelectorAll('.btn-excluir-vc').forEach((botao) => {
    botao.addEventListener('click', async () => {
      if (!confirm('Excluir essa visita comercial, com áudios e anexos?')) return;
      try {
        await Shell.chamarApi(`/visitas-comerciais-dados/${botao.dataset.id}`, { method: 'DELETE' });
        carregarVisitas();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível excluir agora.');
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Gravador de audio
// ---------------------------------------------------------------------------

const LIMITE_GRAVACAO_SEGUNDOS = 10 * 60;
let gravador = null;
let pedacosAudio = [];
let audioGravado = null;
let urlAudioGravado = null;
let inicioGravacao = 0;
let timerGravacao = null;

function tipoAudioSuportado() {
  const tipos = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
  return tipos.find((tipo) => MediaRecorder.isTypeSupported(tipo)) || '';
}

function extensaoDoAudio(mime) {
  if (mime.includes('mp4') || mime.includes('aac')) return '.m4a';
  if (mime.includes('ogg')) return '.ogg';
  return '.webm';
}

function gravando() {
  return gravador !== null && gravador.state === 'recording';
}

function mostrarErroGravador(mensagem) {
  const erroBox = document.getElementById('vc-gravador-erro');
  erroBox.textContent = mensagem;
  erroBox.hidden = !mensagem;
}

async function iniciarGravacao() {
  mostrarErroGravador('');
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
    mostrarErroGravador('Este navegador não permite gravar áudio. Atualize o navegador ou use o Chrome.');
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (erro) {
    mostrarErroGravador('Não consegui acessar o microfone. Libere a permissão de microfone para este site e tente de novo.');
    return;
  }

  const tipo = tipoAudioSuportado();
  gravador = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined);
  pedacosAudio = [];
  gravador.addEventListener('dataavailable', (evento) => {
    if (evento.data.size > 0) pedacosAudio.push(evento.data);
  });
  gravador.addEventListener('stop', () => {
    stream.getTracks().forEach((trilha) => trilha.stop());
    clearInterval(timerGravacao);
    if (pedacosAudio.length === 0) {
      gravador = null;
      renderizarGravador();
      return;
    }
    audioGravado = new Blob(pedacosAudio, { type: gravador.mimeType || tipo || 'audio/webm' });
    urlAudioGravado = URL.createObjectURL(audioGravado);
    gravador = null;
    renderizarGravador();
  });

  gravador.start(1000);
  inicioGravacao = Date.now();
  timerGravacao = setInterval(() => {
    const segundos = (Date.now() - inicioGravacao) / 1000;
    const tempo = document.getElementById('vc-gravador-tempo');
    if (tempo) tempo.textContent = formatarDuracao(segundos);
    if (segundos >= LIMITE_GRAVACAO_SEGUNDOS) pararGravacao();
  }, 500);
  renderizarGravador();
}

function pararGravacao() {
  if (gravando()) gravador.stop();
}

function descartarAudioGravado() {
  if (urlAudioGravado) URL.revokeObjectURL(urlAudioGravado);
  audioGravado = null;
  urlAudioGravado = null;
  renderizarGravador();
}

function cancelarGravacao() {
  if (gravando()) {
    pedacosAudio = [];
    gravador.stop();
  }
  descartarAudioGravado();
}

function renderizarGravador() {
  const container = document.getElementById('vc-gravador');
  if (gravando()) {
    container.innerHTML = `
      <button type="button" class="vc-btn-gravar gravando" id="vc-btn-parar">■ Parar gravação</button>
      <span class="vc-gravando"><span class="vc-ponto-gravando"></span><span id="vc-gravador-tempo">0:00</span></span>
    `;
    document.getElementById('vc-btn-parar').addEventListener('click', pararGravacao);
  } else if (audioGravado) {
    container.innerHTML = `
      <audio controls src="${urlAudioGravado}" class="vc-player"></audio>
      <div class="vc-gravado-acoes">
        <span class="meta">Será enviado e transcrito ao salvar a visita.</span>
        <button type="button" class="btn-ghost" id="vc-btn-descartar" style="color: var(--danger);">Descartar e gravar de novo</button>
      </div>
    `;
    document.getElementById('vc-btn-descartar').addEventListener('click', descartarAudioGravado);
  } else {
    container.innerHTML = '<button type="button" class="vc-btn-gravar" id="vc-btn-gravar">🎙 Gravar áudio da visita</button>';
    document.getElementById('vc-btn-gravar').addEventListener('click', iniciarGravacao);
  }
}

// ---------------------------------------------------------------------------
// Audios ja enviados (transcricao, ouvir, excluir)
// ---------------------------------------------------------------------------

function renderizarAudios(audios) {
  const container = document.getElementById('vc-lista-audios');
  if (!audios || audios.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = audios
    .map((a) => {
      let corpo;
      if (a.status_transcricao === 'pendente' || a.status_transcricao === 'processando') {
        corpo = '<div class="meta">⏳ Transcrevendo… leva alguns minutos. Os campos vazios serão preenchidos sozinhos.</div>';
      } else if (a.status_transcricao === 'erro') {
        corpo = `
          <div class="vc-audio-erro">${escaparHtml(a.erro_transcricao || 'Não foi possível transcrever.')}</div>
          ${a.audio_disponivel ? `<button type="button" class="btn-ghost vc-retranscrever" data-audio-id="${a.id}">Tentar transcrever de novo</button>` : ''}
        `;
      } else {
        const preenchidos = a.campos_preenchidos.map((c) => ROTULOS_CAMPOS[c] || c);
        corpo = `
          <div class="vc-transcricao">${a.transcricao ? escaparHtml(a.transcricao) : '<span class="meta">Nenhuma fala reconhecida no áudio.</span>'}</div>
          ${preenchidos.length ? `<div class="vc-preenchidos">✓ Preenchido pelo áudio: ${escaparHtml(preenchidos.join(', '))}</div>` : ''}
        `;
      }
      const podeExcluir = ehEscritorio || a.enviado_por_id === auth.id;
      const player = a.audio_disponivel
        ? `<button type="button" class="btn-ghost vc-ouvir" data-audio-id="${a.id}">▶ Ouvir</button>`
        : '<span class="meta">Áudio apagado após 30 dias</span>';
      return `
        <div class="vc-audio" data-audio-id="${a.id}">
          <div class="vc-audio-topo">
            <span class="meta">🎙 ${escaparHtml(a.enviado_por_nome)} · ${formatarDataHoraBR(a.criado_em)}${a.duracao_segundos ? ` · ${formatarDuracao(a.duracao_segundos)}` : ''}</span>
            <span class="vc-audio-acoes">
              ${player}
              ${podeExcluir ? `<button type="button" class="btn-ghost vc-excluir-audio" data-audio-id="${a.id}" style="color: var(--danger);">Excluir</button>` : ''}
            </span>
          </div>
          ${corpo}
        </div>
      `;
    })
    .join('');
}

async function baixarComAutenticacao(caminho) {
  const autenticacao = Shell.autenticacao();
  if (!autenticacao) return null;
  const resposta = await fetch(caminho, { headers: { Authorization: `Bearer ${autenticacao.access_token}` } });
  if (resposta.status === 401) {
    Shell.sair();
    return null;
  }
  if (!resposta.ok) {
    const erro = new Error('Falha ao baixar');
    try {
      erro.detalhe = (await resposta.json()).detail;
    } catch (_) {
      // sem corpo JSON, sem problema
    }
    throw erro;
  }
  return resposta.blob();
}

async function tratarCliqueAudios(evento) {
  const botaoOuvir = evento.target.closest('.vc-ouvir');
  if (botaoOuvir) {
    botaoOuvir.disabled = true;
    botaoOuvir.textContent = 'Carregando…';
    try {
      const blob = await baixarComAutenticacao(`/visitas-comerciais-dados/audios/${botaoOuvir.dataset.audioId}`);
      if (!blob) return;
      const player = document.createElement('audio');
      player.controls = true;
      player.className = 'vc-player';
      player.src = URL.createObjectURL(blob);
      botaoOuvir.closest('.vc-audio').querySelector('.vc-audio-topo').after(player);
      botaoOuvir.remove();
      player.play().catch(() => {});
    } catch (erro) {
      alert(erro.detalhe || 'Não foi possível carregar o áudio agora.');
      botaoOuvir.disabled = false;
      botaoOuvir.textContent = '▶ Ouvir';
    }
    return;
  }

  const botaoExcluir = evento.target.closest('.vc-excluir-audio');
  if (botaoExcluir) {
    if (!confirm('Excluir esse áudio e a transcrição dele?')) return;
    try {
      await Shell.chamarApi(`/visitas-comerciais-dados/audios/${botaoExcluir.dataset.audioId}`, { method: 'DELETE' });
      await recarregarVisitaEmEdicao();
      carregarVisitas();
    } catch (erro) {
      alert(erro.detalhe || 'Não foi possível excluir o áudio agora.');
    }
    return;
  }

  const botaoRetranscrever = evento.target.closest('.vc-retranscrever');
  if (botaoRetranscrever) {
    try {
      const visita = await Shell.chamarApi(`/visitas-comerciais-dados/audios/${botaoRetranscrever.dataset.audioId}/transcrever-novamente`, { method: 'POST' });
      if (visita) aplicarAtualizacaoDaVisita(visita);
      carregarVisitas();
    } catch (erro) {
      alert(erro.detalhe || 'Não foi possível pedir a transcrição agora.');
    }
  }
}

// Enquanto o modal esta aberto e algum audio transcreve, busca a visita de
// novo de tempos em tempos e traz pro formulario os campos que o audio
// preencheu - so nos inputs que o usuario ainda deixou vazios.
let timerAcompanharTranscricao = null;

function aplicarAtualizacaoDaVisita(visita) {
  visitaEmEdicao = visita;
  Object.entries(CAMPOS_FORMULARIO).forEach(([campo, id]) => {
    const input = document.getElementById(id);
    if (input.value === '' && visita[campo] != null && visita[campo] !== '') {
      input.value = visita[campo];
    }
  });
  renderizarAudios(visita.audios);
  renderizarAnexos(visita.anexos);
  acompanharTranscricao();
}

async function recarregarVisitaEmEdicao() {
  if (!visitaEmEdicao) return;
  const visita = await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmEdicao.id}`);
  if (visita) aplicarAtualizacaoDaVisita(visita);
}

function acompanharTranscricao() {
  clearTimeout(timerAcompanharTranscricao);
  const modalAberto = !document.getElementById('vc-modal-overlay').hidden;
  if (!modalAberto || !visitaEmEdicao || !temAudioTranscrevendo(visitaEmEdicao)) return;
  timerAcompanharTranscricao = setTimeout(async () => {
    try {
      await recarregarVisitaEmEdicao();
    } catch (erro) {
      acompanharTranscricao();
    }
  }, 10000);
}

// ---------------------------------------------------------------------------
// Modal de cadastrar / editar visita
// ---------------------------------------------------------------------------

let visitaEmEdicao = null;

function montarModalVisita() {
  const campoResponsavel = ehEscritorio
    ? `
      <div class="field">
        <label for="vc-responsavel">Responsável pela visita</label>
        <select id="vc-responsavel"></select>
      </div>`
    : '';

  const html = `
    <div class="modal-overlay" id="vc-modal-overlay" hidden>
      <div class="modal vc-modal">
        <div class="modal-header">
          <h3 id="vc-modal-titulo">Nova visita comercial</h3>
          <button class="modal-close" id="vc-modal-fechar" aria-label="Fechar">&times;</button>
        </div>
        <form id="vc-form">
          <div class="field">
            <label for="vc-nome-local">Nome do local</label>
            <input type="text" id="vc-nome-local" maxlength="200" required placeholder="Ex: Condomínio Residencial Jardins">
          </div>
          ${campoResponsavel}
          <div class="vc-duas-colunas">
            <div class="field">
              <label for="vc-bairro">Bairro</label>
              <input type="text" id="vc-bairro" maxlength="100">
            </div>
            <div class="field">
              <label for="vc-cidade">Cidade</label>
              <input type="text" id="vc-cidade" maxlength="100">
            </div>
          </div>
          <div class="field">
            <label for="vc-data-visita">Data da visita</label>
            <input type="date" id="vc-data-visita">
          </div>

          <div class="vc-secao">Áudio da visita</div>
          <p class="meta vc-dica-audio">
            Fale sobre a visita: com quem falou e o cargo, telefone, e-mail, tipo de serviço, quantos postos,
            horários, valor e quando ficou de retornar. O sistema transcreve e preenche os campos vazios.
            Se for gravar a conversa com o cliente, avise antes que está gravando.
          </p>
          <div id="vc-gravador" class="vc-gravador"></div>
          <div class="vc-audio-erro" id="vc-gravador-erro" hidden></div>
          <div id="vc-lista-audios"></div>

          <div class="vc-secao">Fotos e documentos</div>
          <div class="field" id="vc-campo-anexos-existentes" hidden>
            <div id="vc-lista-anexos"></div>
          </div>
          <div class="field">
            <label for="vc-arquivos">Adicionar fotos ou PDFs (até 10MB cada)</label>
            <input type="file" id="vc-arquivos" accept="image/jpeg,image/png,application/pdf" multiple>
          </div>

          <details class="vc-mais-detalhes" id="vc-mais-detalhes">
            <summary>Mais detalhes: contato, serviço e andamento</summary>

            <div class="vc-secao">Contato no local</div>
            <div class="vc-duas-colunas">
              <div class="field">
                <label for="vc-contato-nome">Nome</label>
                <input type="text" id="vc-contato-nome" maxlength="150">
              </div>
              <div class="field">
                <label for="vc-contato-cargo">Cargo</label>
                <input type="text" id="vc-contato-cargo" maxlength="100" placeholder="Ex: Síndico, Gerente predial">
              </div>
              <div class="field">
                <label for="vc-contato-telefone">Telefone</label>
                <input type="tel" id="vc-contato-telefone" maxlength="50">
              </div>
              <div class="field">
                <label for="vc-contato-email">E-mail</label>
                <input type="email" id="vc-contato-email" maxlength="150">
              </div>
            </div>

            <div class="vc-secao">Serviço</div>
            <div class="vc-duas-colunas">
              <div class="field">
                <label for="vc-tipo-servico">Tipo de serviço</label>
                <select id="vc-tipo-servico"></select>
              </div>
              <div class="field">
                <label for="vc-qtd-postos">Qtd. de postos / colaboradores</label>
                <input type="number" id="vc-qtd-postos" min="0" step="1">
              </div>
              <div class="field">
                <label for="vc-horarios">Horários</label>
                <input type="text" id="vc-horarios" maxlength="300" placeholder="Ex: seg a sex, 7h às 16h">
              </div>
              <div class="field">
                <label for="vc-valor">Valor estimado / orçado (R$ por mês)</label>
                <input type="number" id="vc-valor" min="0" step="0.01">
              </div>
            </div>
            <div class="field">
              <label for="vc-observacoes">Observações do local</label>
              <textarea id="vc-observacoes" rows="3" maxlength="2000" placeholder="Necessidades do cliente, concorrente atual..."></textarea>
            </div>

            <div class="vc-secao">Andamento</div>
            <div class="vc-duas-colunas">
              <div class="field">
                <label for="vc-status">Status</label>
                <select id="vc-status"></select>
              </div>
              <div class="field">
                <label for="vc-data-retorno">Data de retorno</label>
                <input type="date" id="vc-data-retorno">
              </div>
            </div>
            <div class="field">
              <label for="vc-proximo-passo">Próximo passo</label>
              <input type="text" id="vc-proximo-passo" maxlength="500" placeholder="Ex: Enviar proposta, ligar pro síndico após a assembleia...">
            </div>
            <div class="field" id="vc-campo-motivo-perda" hidden>
              <label for="vc-motivo-perda">Motivo da perda</label>
              <textarea id="vc-motivo-perda" rows="2" maxlength="500" placeholder="Ex: Preço, ficou com o concorrente, desistiu da terceirização..."></textarea>
            </div>
          </details>

          <div class="error-message" id="vc-modal-erro"></div>
          <button type="submit" class="btn-primary" id="vc-modal-enviar">Salvar visita</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('vc-tipo-servico').innerHTML = opcoesHtml(opcoesVisita.tipos_servico, 'Não informado');
  if (ehEscritorio) {
    document.getElementById('vc-responsavel').innerHTML = pessoasCache
      .map((p) => `<option value="${p.id}">${escaparHtml(p.nome)}${p.papel === 'supervisor' ? '' : ' (escritório)'}</option>`)
      .join('');
  }

  document.getElementById('vc-modal-fechar').addEventListener('click', fecharModalVisita);
  document.getElementById('vc-modal-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'vc-modal-overlay') fecharModalVisita();
  });
  document.getElementById('vc-status').addEventListener('change', atualizarCampoMotivoPerda);
  document.getElementById('vc-data-visita').addEventListener('change', sincronizarStatusComDataVisita);
  document.getElementById('vc-form').addEventListener('submit', salvarVisita);
  document.getElementById('vc-lista-audios').addEventListener('click', tratarCliqueAudios);

  document.getElementById('vc-lista-anexos').addEventListener('click', async (evento) => {
    const link = evento.target.closest('.vc-link-anexo');
    if (link) {
      evento.preventDefault();
      verAnexo(link.dataset.anexoId);
      return;
    }
    const botaoRemover = evento.target.closest('.vc-remover-anexo');
    if (botaoRemover) {
      if (!confirm('Excluir esse anexo?')) return;
      try {
        await Shell.chamarApi(`/visitas-comerciais-dados/anexos/${botaoRemover.dataset.anexoId}`, { method: 'DELETE' });
        await recarregarVisitaEmEdicao();
        carregarVisitas();
      } catch (erro) {
        alert(erro.detalhe || 'Não foi possível excluir o anexo agora.');
      }
    }
  });
}

function preencherSelectStatus(statusAtual) {
  // "fechada" so acontece pelo botao "Converter em cliente"
  const lista = opcoesVisita.status.filter((s) => s.chave !== 'fechada' || statusAtual === 'fechada');
  const select = document.getElementById('vc-status');
  select.innerHTML = opcoesHtml(lista);
  select.value = statusAtual;
  select.disabled = statusAtual === 'fechada';
  atualizarCampoMotivoPerda();
}

function atualizarCampoMotivoPerda() {
  const perdida = document.getElementById('vc-status').value === 'perdida';
  document.getElementById('vc-campo-motivo-perda').hidden = !perdida;
  document.getElementById('vc-motivo-perda').required = perdida;
  if (perdida) document.getElementById('vc-mais-detalhes').open = true;
}

function sincronizarStatusComDataVisita() {
  const select = document.getElementById('vc-status');
  const temData = !!document.getElementById('vc-data-visita').value;
  if (temData && select.value === 'solicitada') select.value = 'visitada';
  if (!temData && select.value === 'visitada') select.value = 'solicitada';
  atualizarCampoMotivoPerda();
}

function renderizarAnexos(anexos) {
  const container = document.getElementById('vc-lista-anexos');
  document.getElementById('vc-campo-anexos-existentes').hidden = anexos.length === 0;
  container.innerHTML = anexos
    .map(
      (a) => `
      <div class="vc-anexo">
        <a href="#" class="vc-link-anexo" data-anexo-id="${a.id}">📎 ${escaparHtml(a.nome_original)}</a>
        <span class="meta">${escaparHtml(a.enviado_por_nome)} · ${formatarDataBR(a.criado_em)}</span>
        <button type="button" class="btn-ghost vc-remover-anexo" data-anexo-id="${a.id}">Excluir</button>
      </div>
    `
    )
    .join('');
}

function prepararModal(titulo) {
  cancelarGravacao();
  mostrarErroGravador('');
  document.getElementById('vc-modal-titulo').textContent = titulo;
  document.getElementById('vc-form').reset();
  document.getElementById('vc-modal-erro').classList.remove('visible');
}

function abrirModalNovaVisita() {
  visitaEmEdicao = null;
  prepararModal(ehEscritorio ? 'Solicitar / registrar visita' : 'Nova visita comercial');
  renderizarAudios([]);
  renderizarAnexos([]);
  document.getElementById('vc-mais-detalhes').open = false;

  // escritorio normalmente solicita a visita (ainda sem data); supervisor
  // normalmente registra uma visita que acabou de fazer
  if (ehEscritorio) {
    document.getElementById('vc-responsavel').value = auth.id;
    preencherSelectStatus('solicitada');
  } else {
    document.getElementById('vc-data-visita').value = hojeIso();
    preencherSelectStatus('visitada');
  }

  document.getElementById('vc-modal-overlay').hidden = false;
}

function abrirModalEditarVisita(visita) {
  if (!visita) return;
  visitaEmEdicao = visita;
  prepararModal(visita.nome_local);

  Object.entries(CAMPOS_FORMULARIO).forEach(([campo, id]) => {
    document.getElementById(id).value = visita[campo] ?? '';
  });
  if (ehEscritorio) document.getElementById('vc-responsavel').value = visita.responsavel_id;
  preencherSelectStatus(visita.status);
  renderizarAudios(visita.audios);
  renderizarAnexos(visita.anexos);
  document.getElementById('vc-mais-detalhes').open = true;

  document.getElementById('vc-modal-overlay').hidden = false;
  acompanharTranscricao();
}

function fecharModalVisita() {
  if (audioGravado || gravando()) {
    if (!confirm('O áudio gravado ainda não foi salvo. Fechar e descartar a gravação?')) return;
  }
  cancelarGravacao();
  clearTimeout(timerAcompanharTranscricao);
  document.getElementById('vc-modal-overlay').hidden = true;
}

function textoOuNulo(id) {
  return document.getElementById(id).value.trim() || null;
}

function numeroOuNulo(id) {
  const valor = document.getElementById(id).value;
  return valor === '' ? null : Number(valor);
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

async function salvarVisita(evento) {
  evento.preventDefault();
  const erroBox = document.getElementById('vc-modal-erro');
  const botao = document.getElementById('vc-modal-enviar');
  erroBox.classList.remove('visible');

  if (gravando()) {
    erroBox.textContent = 'Pare a gravação antes de salvar.';
    erroBox.classList.add('visible');
    return;
  }

  const statusSelect = document.getElementById('vc-status');
  const corpo = {
    nome_local: document.getElementById('vc-nome-local').value.trim(),
    bairro: textoOuNulo('vc-bairro'),
    cidade: textoOuNulo('vc-cidade'),
    contato_nome: textoOuNulo('vc-contato-nome'),
    contato_cargo: textoOuNulo('vc-contato-cargo'),
    contato_telefone: textoOuNulo('vc-contato-telefone'),
    contato_email: textoOuNulo('vc-contato-email'),
    data_visita: textoOuNulo('vc-data-visita'),
    tipo_servico: textoOuNulo('vc-tipo-servico'),
    qtd_postos: numeroOuNulo('vc-qtd-postos'),
    horarios: textoOuNulo('vc-horarios'),
    valor_estimado: numeroOuNulo('vc-valor'),
    observacoes: textoOuNulo('vc-observacoes'),
    proximo_passo: textoOuNulo('vc-proximo-passo'),
    data_retorno: textoOuNulo('vc-data-retorno'),
    motivo_perda: textoOuNulo('vc-motivo-perda'),
  };
  if (!statusSelect.disabled) corpo.status = statusSelect.value;
  const responsavelEscolhido = ehEscritorio ? document.getElementById('vc-responsavel').value : '';
  if (responsavelEscolhido) corpo.responsavel_id = Number(responsavelEscolhido);

  const arquivos = document.getElementById('vc-arquivos').files;

  botao.disabled = true;
  botao.textContent = 'Salvando...';
  let salva = null;
  try {
    salva = visitaEmEdicao
      ? await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmEdicao.id}`, { method: 'PATCH', body: corpo })
      : await Shell.chamarApi('/visitas-comerciais-dados', { method: 'POST', body: corpo });
    if (salva === null) return;

    if (audioGravado) {
      botao.textContent = 'Enviando áudio...';
      const formAudio = new FormData();
      formAudio.append('audio', audioGravado, `gravacao${extensaoDoAudio(audioGravado.type)}`);
      salva = (await enviarFormData(`/visitas-comerciais-dados/${salva.id}/audios`, formAudio)) || salva;
      descartarAudioGravado();
    }
    if (arquivos.length > 0) {
      botao.textContent = 'Enviando anexos...';
      const formAnexos = new FormData();
      Array.from(arquivos).forEach((arquivo) => formAnexos.append('arquivos', arquivo));
      await enviarFormData(`/visitas-comerciais-dados/${salva.id}/anexos`, formAnexos);
    }
    clearTimeout(timerAcompanharTranscricao);
    document.getElementById('vc-modal-overlay').hidden = true;
    carregarVisitas();
  } catch (erro) {
    if (salva) {
      // a visita foi salva, so o audio/anexos falharam - o audio gravado continua
      // no gravador pra tentar de novo, e o modal fica aberto em modo edicao
      const audioPendente = audioGravado;
      abrirModalEditarVisita(salva);
      if (audioPendente) {
        audioGravado = audioPendente;
        urlAudioGravado = URL.createObjectURL(audioPendente);
        renderizarGravador();
      }
      carregarVisitas();
      erroBox.textContent = `A visita foi salva, mas o envio falhou: ${erro.detalhe || 'tente salvar de novo.'}`;
    } else {
      erroBox.textContent = erro.detalhe || 'Não foi possível salvar a visita agora.';
    }
    erroBox.classList.add('visible');
  } finally {
    botao.disabled = false;
    botao.textContent = 'Salvar visita';
  }
}

async function verAnexo(anexoId) {
  try {
    const blob = await baixarComAutenticacao(`/visitas-comerciais-dados/anexos/${anexoId}`);
    if (blob) window.open(URL.createObjectURL(blob), '_blank');
  } catch (erro) {
    alert('Não foi possível abrir esse anexo agora.');
  }
}

// ---------------------------------------------------------------------------
// Converter em cliente
// ---------------------------------------------------------------------------

let visitaEmConversao = null;

function montarModalConverter() {
  const html = `
    <div class="modal-overlay" id="vc-converter-overlay" hidden>
      <div class="modal">
        <div class="modal-header">
          <h3>Converter em cliente</h3>
          <button class="modal-close" id="vc-converter-fechar" aria-label="Fechar">&times;</button>
        </div>
        <p class="meta" style="margin-top: 0;">Cria o cliente com o bairro, a cidade e o contato levantados na visita, e marca a visita como fechada.</p>
        <form id="vc-converter-form">
          <div class="field">
            <label for="vc-converter-nome">Nome do cliente</label>
            <input type="text" id="vc-converter-nome" maxlength="200" required>
          </div>
          <div class="field">
            <label for="vc-converter-empresa">Empresa</label>
            <select id="vc-converter-empresa" required></select>
          </div>
          <div class="field">
            <label for="vc-converter-supervisor">Supervisor do cliente</label>
            <select id="vc-converter-supervisor"></select>
          </div>
          <div class="error-message" id="vc-converter-erro"></div>
          <button type="submit" class="btn-primary" id="vc-converter-enviar">Criar cliente</button>
        </form>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  document.getElementById('vc-converter-empresa').innerHTML =
    '<option value="">Escolha a empresa</option>' +
    empresasCache.map((e) => `<option value="${e.id}">${escaparHtml(e.nome)}</option>`).join('');

  const fechar = () => { document.getElementById('vc-converter-overlay').hidden = true; };
  document.getElementById('vc-converter-fechar').addEventListener('click', fechar);
  document.getElementById('vc-converter-overlay').addEventListener('click', (evento) => {
    if (evento.target.id === 'vc-converter-overlay') fechar();
  });

  document.getElementById('vc-converter-form').addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const erroBox = document.getElementById('vc-converter-erro');
    const botao = document.getElementById('vc-converter-enviar');
    erroBox.classList.remove('visible');
    const supervisorId = document.getElementById('vc-converter-supervisor').value;
    botao.disabled = true;
    botao.textContent = 'Criando...';
    try {
      const visita = await Shell.chamarApi(`/visitas-comerciais-dados/${visitaEmConversao.id}/converter-cliente`, {
        method: 'POST',
        body: {
          nome: document.getElementById('vc-converter-nome').value.trim(),
          empresa_id: Number(document.getElementById('vc-converter-empresa').value),
          supervisor_id: supervisorId ? Number(supervisorId) : null,
        },
      });
      if (visita === null) return;
      fechar();
      carregarVisitas();
      if (confirm(`Cliente "${visita.cliente_nome}" criado. Abrir a ficha do cliente agora?`)) {
        window.location.href = `/cliente-detalhe?id=${visita.cliente_id}`;
      }
    } catch (erro) {
      erroBox.textContent = erro.detalhe || 'Não foi possível criar o cliente agora.';
      erroBox.classList.add('visible');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Criar cliente';
    }
  });
}

async function abrirModalConverter(visita) {
  if (!visita) return;
  visitaEmConversao = visita;
  document.getElementById('vc-converter-erro').classList.remove('visible');

  if (supervisoresCache.length === 0) {
    try {
      supervisoresCache = (await Shell.chamarApi('/supervisores')) || [];
    } catch (erro) {
      supervisoresCache = [];
    }
  }
  const selectSupervisor = document.getElementById('vc-converter-supervisor');
  selectSupervisor.innerHTML =
    '<option value="">Sem supervisor</option>' +
    supervisoresCache.map((s) => `<option value="${s.id}">${escaparHtml(s.nome)}</option>`).join('');
  selectSupervisor.value = supervisoresCache.some((s) => s.id === visita.responsavel_id) ? visita.responsavel_id : '';

  document.getElementById('vc-converter-nome').value = visita.nome_local;
  document.getElementById('vc-converter-empresa').value = visita.empresa_id ?? '';
  document.getElementById('vc-converter-overlay').hidden = false;
}

// ---------------------------------------------------------------------------
// Inicializacao
// ---------------------------------------------------------------------------

async function iniciar() {
  if (!auth) return;
  Shell.chamarApi('/visitas-comerciais-dados/marcar-vistas', { method: 'POST' })
    .then(() => Shell.atualizarBadgeVisitasComerciais())
    .catch(() => {});
  const container = document.getElementById('lista-visitas-comerciais');
  try {
    const [opcoes, empresas, permissoes, pessoas] = await Promise.all([
      Shell.chamarApi('/visitas-comerciais-opcoes'),
      Shell.chamarApi('/empresas'),
      Shell.chamarApi('/minhas-permissoes'),
      ehEscritorio ? Shell.chamarApi('/pessoas') : Promise.resolve([]),
    ]);
    if (opcoes === null) return;
    opcoesVisita = opcoes;
    empresasCache = empresas || [];
    podeConverterCliente = !!(permissoes && permissoes.criar_cliente);
    pessoasCache = pessoas || [];
  } catch (erro) {
    container.innerHTML = '<div class="empty-state">Não foi possível carregar a tela agora.</div>';
    return;
  }

  preencherFiltros();
  montarModalVisita();
  montarModalConverter();
  renderizarGravador();
  document.getElementById('btn-nova-visita-comercial').addEventListener('click', abrirModalNovaVisita);
  carregarVisitas();
}

iniciar();
