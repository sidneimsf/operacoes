const MODULOS = {
  '/avisos': {
    chave: 'avisos',
    titulo: 'Avisos',
    descricao: 'Um canal único de comunicação por assunto ou cliente, encerrando as conversas cruzadas entre escritório e supervisores sobre o mesmo assunto.',
  },
};

const modulo = MODULOS[window.location.pathname] || {
  chave: 'dashboard',
  titulo: 'Em construção',
  descricao: 'Este módulo ainda está sendo desenvolvido.',
};

const auth = Shell.montar(modulo.chave, modulo.titulo);

document.getElementById('modulo-icone').innerHTML = Shell.icone(modulo.chave);
document.getElementById('modulo-titulo').textContent = `${modulo.titulo} — em construção`;
document.getElementById('modulo-descricao').textContent = modulo.descricao;
