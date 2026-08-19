const form = document.getElementById('login-form');
const errorBox = document.getElementById('error-message');
const btnEntrar = document.getElementById('btn-entrar');

function mostrarErro(mensagem) {
  errorBox.textContent = mensagem;
  errorBox.classList.add('visible');
}

function esconderErro() {
  errorBox.classList.remove('visible');
}

// Se já existe uma sessão válida guardada, pula direto pro painel.
if (localStorage.getItem('operacoes_auth')) {
  window.location.href = '/dashboard';
}

// Preenche o pequeno painel de status com dados publicos (sem exigir login).
fetch('/stats')
  .then((r) => r.json())
  .then((dados) => {
    document.getElementById('stat-empresas').textContent = dados.empresas;
    document.getElementById('stat-clientes').textContent = dados.clientes;
  })
  .catch(() => {
    // Se falhar, os tracinhos "—" continuam ali, sem quebrar a tela.
  });

form.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  esconderErro();

  const email = document.getElementById('email').value.trim();
  const senha = document.getElementById('senha').value;

  btnEntrar.disabled = true;
  btnEntrar.textContent = 'Entrando...';

  try {
    const resposta = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, senha }),
    });

    if (resposta.status === 401) {
      mostrarErro('E-mail ou senha inválidos.');
      return;
    }

    if (!resposta.ok) {
      mostrarErro('Não foi possível entrar. Tente novamente em instantes.');
      return;
    }

    const dados = await resposta.json();
    localStorage.setItem('operacoes_auth', JSON.stringify(dados));
    window.location.href = '/dashboard';
  } catch (erro) {
    mostrarErro('Sem conexão com o servidor. Verifique sua internet.');
  } finally {
    btnEntrar.disabled = false;
    btnEntrar.textContent = 'Entrar';
  }
});
