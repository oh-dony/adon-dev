<p align="center"><img src="icons/hicolor/scalable/apps/com.adonay.dev.svg" alt="adon dev" height="120"></p>

# adon dev · seu ambiente de programação pronto depois de instalar o Linux

Acabou de instalar o Linux e precisa preparar o computador para programar? Marque o que você
vai usar e o adon dev instala e configura tudo, sem terminal. A senha de administrador é
pedida uma vez só.

> **Em desenvolvimento:** ainda sem pacote para baixar. Veja [docs/PROXIMOS-PASSOS.md](docs/PROXIMOS-PASSOS.md).

## Como funciona

1. **O que você vai usar?** Escolha um perfil (Front-end, Web com PHP, Python, Tudo) ou marque item por item.
2. **Seus dados do Git:** nome e e-mail (já preenchidos se o Git estiver configurado).
3. **Resumo** do que vai ser instalado.
4. **Progresso:** cada item ganha ✓ ou ✗; se algo falha, "Ver detalhes" mostra o motivo e dá para tentar de novo só o que falhou.
5. **Pronto:** sua chave SSH com botão de copiar e o link para colar no GitHub.

## O que ele instala

| Item | O que fica pronto | De onde vem |
|---|---|---|
| Git | Nome, e-mail, branch padrão `main` e chave SSH | Ubuntu |
| GitHub CLI | Comando `gh` | Repositório oficial do GitHub |
| Visual Studio Code | Editor, com atualizações automáticas | Repositório oficial da Microsoft |
| Node.js | Versão LTS + npm, com o **fnm** para trocar de versão por projeto | Releases oficiais do fnm |
| PHP + Composer | PHP com as extensões que Laravel e WordPress pedem | Ubuntu + instalador oficial do Composer (assinatura conferida) |
| Python + uv | Python com o **uv** (ambientes, pacotes e outras versões em segundos) | Ubuntu + releases oficiais do uv |
| Docker | Docker e Docker Compose, liberado para usar **sem sudo** | Repositório oficial do Docker |

Testado em instalação real no **Ubuntu 22.04 e 24.04**, que também cobre Zorin OS 17/18,
Pop!_OS 22.04 e Linux Mint 21/22. (O Pop!_OS 24.04 usa o COSMIC e não foi testado.)

## Desenvolvimento

```bash
./dev run                 # abre o app direto do código
./dev test                # testes rápidos (motor e telas, sem root nem internet)
./dev docker git,node     # instala de verdade num Ubuntu 22.04 e 24.04 limpos
```

- [motor.py](motor.py): as receitas e quem as executa (sem GTK, testável sozinho).
- [adon_dev.py](adon_dev.py): o assistente (GTK4/libadwaita).
- Regras do projeto, como "todo bug vira teste" e como escrever uma receita: [AGENTS.md](AGENTS.md).

## Licença

GPL-3.0
