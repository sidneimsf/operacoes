/*
 * Service worker minimo, focado em seguranca de dados E em sempre
 * mostrar a versao mais recente: so cacheia arquivos ESTATICOS (css,
 * js, imagens, icones), e mesmo assim sempre tenta buscar a versao
 * nova da rede PRIMEIRO - o cache so entra em acao se o dispositivo
 * estiver genuinamente sem internet. Isso evita o problema classico
 * de PWA mostrando uma tela antiga depois de uma atualizacao.
 *
 * Paginas HTML e chamadas de API (chamados, clientes, colaboradores,
 * etc.) NUNCA passam por aqui - sempre vao direto pra rede, pra nunca
 * mostrar uma informacao desatualizada num sistema onde os dados
 * mudam o tempo todo.
 */

const CACHE_NAME = 'operacoes-static-v2';

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
    fetch(evento.request)
      .then((respostaRede) => {
        caches.open(CACHE_NAME).then((cache) => cache.put(evento.request, respostaRede.clone()));
        return respostaRede;
      })
      .catch(() => caches.open(CACHE_NAME).then((cache) => cache.match(evento.request)))
  );
});
