/*
 * Service worker minimo, focado em seguranca de dados: so cacheia
 * arquivos ESTATICOS (css, js, imagens, icones). Paginas HTML e
 * chamadas de API (chamados, clientes, colaboradores, etc.) NUNCA
 * passam por aqui - sempre vao direto pra rede, pra nunca mostrar uma
 * informacao desatualizada num sistema onde os dados mudam o tempo
 * todo.
 *
 * O objetivo aqui e so permitir que o navegador considere o site
 * "instalavel" (adicionar a tela inicial) e deixar os arquivos
 * estaticos carregando mais rapido - nao e sobre funcionar offline.
 */

const CACHE_NAME = 'operacoes-static-v1';

self.addEventListener('install', (evento) => {
  self.skipWaiting();
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(nomes.filter((nome) => nome !== CACHE_NAME).map((nome) => caches.delete(nome)))
    )
  );
  self.clients.claim();
});

function ehArquivoEstatico(url) {
  return url.pathname.startsWith('/static/') && /\.(css|js|png|jpg|jpeg|svg|ico|woff2?)$/i.test(url.pathname);
}

self.addEventListener('fetch', (evento) => {
  if (evento.request.method !== 'GET') return;

  const url = new URL(evento.request.url);
  if (!ehArquivoEstatico(url)) {
    return; // deixa passar direto pra rede - paginas e API nunca sao interceptadas
  }

  evento.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const respostaCache = await cache.match(evento.request);
      const buscarDaRede = fetch(evento.request)
        .then((respostaRede) => {
          cache.put(evento.request, respostaRede.clone());
          return respostaRede;
        })
        .catch(() => respostaCache);
      return respostaCache || buscarDaRede;
    })
  );
});
