const auth = Shell.montar('mapa-clientes', 'Mapa de Clientes');

// Uma cor por empresa, na ordem em que /empresas devolve
const CORES_EMPRESA = ['#1f6fb2', '#c0612b', '#2e8b57', '#8a4fbf', '#b8860b'];
const CENTRO_BRASIL = [-15.8, -47.9];

let empresas = [];
let clientes = [];
let mapa = null;
let camadaPinos = null;
const marcadores = new Map();
let clientePosicionando = null; // cliente esperando um clique no mapa para ganhar posicao
let clienteArrastando = null; // cliente com o pino liberado para arrastar

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

// Agrupa grafias diferentes do mesmo bairro ("Centro", "CENTRO", "Centro ") numa opcao so
function chaveBairro(bairro) {
  return (bairro || '').trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function temPosicao(cliente) {
  return cliente.latitude !== null && cliente.longitude !== null;
}

function corDaEmpresa(empresaId) {
  const indice = empresas.findIndex((e) => e.id === empresaId);
  return CORES_EMPRESA[(indice < 0 ? 0 : indice) % CORES_EMPRESA.length];
}

function nomeDaEmpresa(empresaId) {
  return empresas.find((e) => e.id === empresaId)?.nome || '';
}

function passaNosFiltros(cliente) {
  const empresa = document.getElementById('mapa-filtro-empresa').value;
  const bairro = document.getElementById('mapa-filtro-bairro').value;
  if (empresa && cliente.empresa_id !== Number(empresa)) return false;
  if (bairro && chaveBairro(cliente.bairro) !== bairro) return false;
  return true;
}

// ---------- Pinos ----------

function iconeDoCliente(cliente) {
  const aproximado = cliente.geo_precisao === 'bairro';
  return L.divIcon({
    className: 'mapa-pino-wrap',
    html: `<span class="mapa-pino${aproximado ? ' aproximado' : ''}" style="--cor-pino: ${corDaEmpresa(cliente.empresa_id)}"></span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -22],
  });
}

function conteudoPopup(cliente) {
  const endereco = [cliente.endereco, cliente.bairro, cliente.cidade].filter(Boolean).map(escaparHtml).join(' · ');
  let nota = '';
  if (cliente.geo_precisao === 'bairro') {
    nota = '<div class="mapa-popup-nota">Posição aproximada (centro do bairro). Use "Ajustar posição" para corrigir.</div>';
  } else if (cliente.geo_precisao === 'manual') {
    nota = '<div class="mapa-popup-nota">Posição ajustada manualmente.</div>';
  }
  const destino = `${cliente.latitude},${cliente.longitude}`;
  return `
    <div class="mapa-popup">
      <strong>${escaparHtml(cliente.nome)}</strong>
      <div class="mapa-popup-empresa">${escaparHtml(nomeDaEmpresa(cliente.empresa_id))}</div>
      <div>${endereco || 'Endereço não cadastrado'}</div>
      ${nota}
      <div class="mapa-popup-acoes">
        <a href="/cliente-detalhe?id=${cliente.id}">Abrir ficha</a>
        <a href="https://www.google.com/maps/dir/?api=1&destination=${destino}" target="_blank" rel="noopener">Como chegar</a>
        <button type="button" class="mapa-popup-ajustar">Ajustar posição</button>
      </div>
    </div>
  `;
}

function criarMarcador(cliente) {
  const marcador = L.marker([cliente.latitude, cliente.longitude], {
    icon: iconeDoCliente(cliente),
    title: cliente.nome,
  });
  marcador.bindPopup(() => conteudoPopup(cliente));
  // o Leaflet nao deixa o clique do popup subir ate o document, entao o botao e ligado aqui
  marcador.on('popupopen', (evento) => {
    evento.popup.getElement().querySelector('.mapa-popup-ajustar')
      .addEventListener('click', () => iniciarAjuste(cliente));
  });
  marcador.on('dragend', () => salvarPosicao(cliente, marcador.getLatLng()));
  return marcador;
}

function desenharPinos({ enquadrar }) {
  camadaPinos.clearLayers();
  marcadores.clear();
  const visiveis = [];
  clientes.filter(temPosicao).forEach((cliente) => {
    const marcador = criarMarcador(cliente);
    marcadores.set(cliente.id, marcador);
    if (passaNosFiltros(cliente)) {
      camadaPinos.addLayer(marcador);
      visiveis.push([cliente.latitude, cliente.longitude]);
    }
  });

  if (enquadrar) {
    if (visiveis.length > 0) {
      mapa.fitBounds(visiveis, { padding: [40, 40], maxZoom: 16 });
    } else {
      mapa.setView(CENTRO_BRASIL, 4);
    }
  }
  renderizarSemPosicao();
}

// ---------- Aviso de modo (posicionar/arrastar) ----------

function mostrarAviso(html) {
  const aviso = document.getElementById('mapa-aviso');
  aviso.innerHTML = html;
  aviso.hidden = false;
}

function esconderAviso() {
  document.getElementById('mapa-aviso').hidden = true;
}

function cancelarModos() {
  if (clienteArrastando) {
    const marcador = marcadores.get(clienteArrastando.id);
    if (marcador) {
      marcador.dragging.disable();
      marcador.setLatLng([clienteArrastando.latitude, clienteArrastando.longitude]);
    }
  }
  clienteArrastando = null;
  clientePosicionando = null;
  document.getElementById('mapa-clientes').classList.remove('posicionando');
  esconderAviso();
}

function iniciarAjuste(cliente) {
  cancelarModos();
  const marcador = marcadores.get(cliente.id);
  if (!marcador) return;
  marcador.closePopup();
  marcador.dragging.enable();
  clienteArrastando = cliente;
  mostrarAviso(`Arraste o pino de <strong>${escaparHtml(cliente.nome)}</strong> até o lugar certo e solte. <button type="button" class="btn-ghost" data-acao="cancelar">Cancelar</button>`);
}

function iniciarPosicionamento(cliente) {
  cancelarModos();
  clientePosicionando = cliente;
  document.getElementById('mapa-clientes').classList.add('posicionando');
  mostrarAviso(`Clique no mapa onde fica <strong>${escaparHtml(cliente.nome)}</strong>. <button type="button" class="btn-ghost" data-acao="cancelar">Cancelar</button>`);
  document.getElementById('mapa-clientes').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function salvarPosicao(cliente, latlng) {
  mostrarAviso(`Salvando a posição de <strong>${escaparHtml(cliente.nome)}</strong>...`);
  try {
    const atualizado = await Shell.chamarApi(`/clientes-dados/${cliente.id}`, {
      method: 'PATCH',
      body: { latitude: latlng.lat, longitude: latlng.lng },
    });
    cliente.latitude = atualizado.latitude;
    cliente.longitude = atualizado.longitude;
    cliente.geo_precisao = atualizado.geo_precisao;
    clienteArrastando = null;
    clientePosicionando = null;
    document.getElementById('mapa-clientes').classList.remove('posicionando');
    desenharPinos({ enquadrar: false });
    mostrarAviso(`Posição de <strong>${escaparHtml(cliente.nome)}</strong> salva.`);
    setTimeout(esconderAviso, 3000);
  } catch (erro) {
    cancelarModos();
    mostrarAviso(escaparHtml(erro.detalhe || 'Não foi possível salvar a posição agora.'));
  }
}

// ---------- Busca ----------

function focarCliente(cliente) {
  document.getElementById('mapa-busca-resultados').hidden = true;
  document.getElementById('mapa-busca').value = cliente.nome;

  if (!temPosicao(cliente)) {
    mostrarAviso(`<strong>${escaparHtml(cliente.nome)}</strong> ainda não tem posição no mapa. <button type="button" class="btn-ghost" data-acao="posicionar" data-id="${cliente.id}">Posicionar agora</button>`);
    return;
  }

  // se algum filtro esconde o cliente, limpa os filtros para ele aparecer
  if (!passaNosFiltros(cliente)) {
    document.getElementById('mapa-filtro-empresa').value = '';
    document.getElementById('mapa-filtro-bairro').value = '';
    desenharPinos({ enquadrar: false });
  }
  mapa.setView([cliente.latitude, cliente.longitude], 17);
  marcadores.get(cliente.id)?.openPopup();
}

function buscarClientes(termo) {
  const caixa = document.getElementById('mapa-busca-resultados');
  const termoLimpo = chaveBairro(termo);
  if (!termoLimpo) {
    caixa.hidden = true;
    return [];
  }
  const achados = clientes.filter((c) => chaveBairro(c.nome).includes(termoLimpo)).slice(0, 8);
  if (achados.length === 0) {
    caixa.innerHTML = '<div class="mapa-busca-vazio">Nenhum cliente encontrado.</div>';
  } else {
    caixa.innerHTML = achados
      .map((c) => `
        <button type="button" data-id="${c.id}">
          <span>${escaparHtml(c.nome)}</span>
          <small>${escaparHtml(c.bairro || '')}${temPosicao(c) ? '' : ' · sem posição'}</small>
        </button>
      `)
      .join('');
  }
  caixa.hidden = false;
  return achados;
}

// ---------- Filtros e lista de clientes sem posicao ----------

function renderizarFiltros() {
  document.getElementById('mapa-filtro-empresa').innerHTML = '<option value="">Todas</option>'
    + empresas.map((e) => `<option value="${e.id}">${escaparHtml(e.nome)}</option>`).join('');

  const bairros = new Map();
  clientes.forEach((c) => {
    const chave = chaveBairro(c.bairro);
    if (chave && !bairros.has(chave)) bairros.set(chave, c.bairro.trim());
  });
  const ordenados = [...bairros.entries()].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'));
  document.getElementById('mapa-filtro-bairro').innerHTML = '<option value="">Todos os bairros</option>'
    + ordenados.map(([chave, nome]) => `<option value="${chave}">${escaparHtml(nome)}</option>`).join('');

  const empresasComCliente = empresas.filter((e) => clientes.some((c) => c.empresa_id === e.id));
  document.getElementById('mapa-legenda').innerHTML = empresasComCliente
    .map((e) => `<span><i style="background: ${corDaEmpresa(e.id)}"></i>${escaparHtml(e.nome)}</span>`)
    .join('') + '<span><i class="aproximado"></i>Posição aproximada</span>';
}

function renderizarSemPosicao() {
  const semPosicao = clientes.filter((c) => !temPosicao(c));
  const bloco = document.getElementById('mapa-sem-posicao');
  if (semPosicao.length === 0) {
    bloco.hidden = true;
    return;
  }
  bloco.hidden = false;
  document.getElementById('mapa-sem-posicao-titulo').textContent = `Clientes sem posição no mapa · ${semPosicao.length}`;
  document.getElementById('mapa-sem-posicao-lista').innerHTML = semPosicao
    .map((c) => `
      <div class="cliente-row">
        <span>${escaparHtml(c.nome)} <span class="cliente-bairro">${escaparHtml([c.endereco, c.bairro].filter(Boolean).join(' · ') || 'sem endereço cadastrado')}</span></span>
        <button type="button" class="btn-ghost" data-acao="posicionar" data-id="${c.id}">Posicionar</button>
      </div>
    `)
    .join('');
}

// ---------- Eventos ----------

function clientePorId(id) {
  return clientes.find((c) => c.id === Number(id));
}

// botoes do aviso e da lista de sem posicao
document.addEventListener('click', (evento) => {
  const botao = evento.target.closest('[data-acao]');
  if (!botao) return;
  const cliente = clientePorId(botao.dataset.id);
  if (botao.dataset.acao === 'cancelar') cancelarModos();
  if (botao.dataset.acao === 'posicionar' && cliente) iniciarPosicionamento(cliente);
});

document.getElementById('mapa-busca').addEventListener('input', (evento) => buscarClientes(evento.target.value));
document.getElementById('mapa-busca').addEventListener('keydown', (evento) => {
  if (evento.key !== 'Enter') return;
  evento.preventDefault();
  const achados = buscarClientes(evento.target.value);
  if (achados.length > 0) focarCliente(achados[0]);
});
document.getElementById('mapa-busca-resultados').addEventListener('click', (evento) => {
  const botao = evento.target.closest('button[data-id]');
  if (botao) focarCliente(clientePorId(botao.dataset.id));
});
document.addEventListener('click', (evento) => {
  if (!evento.target.closest('.mapa-busca')) document.getElementById('mapa-busca-resultados').hidden = true;
});

document.getElementById('mapa-filtro-empresa').addEventListener('change', () => desenharPinos({ enquadrar: true }));
document.getElementById('mapa-filtro-bairro').addEventListener('change', () => desenharPinos({ enquadrar: true }));

// ---------- Inicio ----------

async function iniciar() {
  mapa = L.map('mapa-clientes').setView(CENTRO_BRASIL, 4);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
  }).addTo(mapa);
  camadaPinos = L.layerGroup().addTo(mapa);

  mapa.on('click', (evento) => {
    if (clientePosicionando) salvarPosicao(clientePosicionando, evento.latlng);
  });

  try {
    empresas = await Shell.chamarApi('/empresas');
    if (empresas === null) return;
    clientes = await Shell.chamarApi('/clientes-dados');
    if (clientes === null) return;
  } catch (erro) {
    mostrarAviso('Não foi possível carregar os clientes agora.');
    return;
  }

  renderizarFiltros();
  desenharPinos({ enquadrar: true });
  if (clientes.length === 0) {
    mostrarAviso('Nenhum cliente na sua carteira ainda.');
  }
}

if (auth) iniciar();
