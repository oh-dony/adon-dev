# Próximos passos

Situação em 23/10/2026: o assistente e as 7 receitas funcionam e passam nos testes (motor,
telas e instalação real no Ubuntu 22.04 e 24.04). Falta empacotar e polir para lançar.

## Para lançar (nesta ordem)

1. **Pacote `.deb` e primeira Release no GitHub**, como no adon studio: dependências
   `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`, `policykit-1` (pkexec), atalho no menu,
   ícone e ficha para a loja de aplicativos (metainfo). Rodar a interface no Docker com
   `xvfb-run`, como o studio faz.
2. **Janela de senha com mensagem própria.** Hoje o pkexec mostra o texto genérico
   "autenticação necessária para executar /usr/bin/bash". Com um arquivo de política do
   polkit (`/usr/share/polkit-1/actions/com.adonay.dev.policy`) e um ajudante fixo em
   `/usr/libexec/adon-dev/`, a janela passa a dizer "O Adon Dev precisa da sua senha para
   instalar as ferramentas".
3. **Entrar no GitHub pelo app.** Botão na tela final: `gh auth login --web --git-protocol ssh`
   (mostra o código e abre o navegador) e depois `gh ssh-key add` envia a chave sozinho,
   sem copiar e colar.

## Ideias para depois

- Mais receitas: Cursor, Java (SDKMAN), Go, Rust (rustup), bancos de dados em Docker
  (PostgreSQL, MySQL, Redis), terminal caprichado (zsh + fonte com ícones).
- Reabrir o app depois para "adicionar uma linguagem" ou "conferir se está tudo funcionando".
- Remix/ISO "adon" com o adon dev (e o adon studio) já dentro, se o app ganhar usuários.

## Conhecido

- O Docker só funciona sem `sudo` depois de sair e entrar de novo na sessão (a tela final avisa).
- A janela do pkexec não é testada automaticamente (no Docker usamos `sudo -n`); ver AGENTS.md.
