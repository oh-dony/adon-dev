# Instruções para agentes

O adon dev prepara o ambiente de programação de quem acabou de instalar o Linux: a pessoa
marca o que vai usar (Git, Node, PHP, Docker…) e o app instala e configura tudo.

- [motor.py](motor.py): receitas e quem as executa. **Sem GTK**: testável sozinho.
- Interface (GTK4/libadwaita): em construção.

## Regra nº 1: todo bug vira teste automatizado

Encontrou um bug, seja reportado pelo usuário, visto num screenshot, num log ou
enquanto você trabalhava em outra coisa? Ele **só está resolvido quando existe um
teste que falharia sem a correção**.

1. **Reproduza com um teste que falha.** Rode e confirme que está vermelho pelo motivo certo.
2. **Corrija.**
3. **Rode o teste de novo** e depois `./dev test` inteiro.
4. **No docstring do teste, um parágrafo `Regressão:`** com o sintoma real e a causa.

Se for inviável automatizar, diga isso ao usuário, explique por quê e registre em
"Não automatizado" no fim deste arquivo.

### Onde cada teste vai

| Tipo de bug | Onde | Como rodar |
|---|---|---|
| Lógica do motor: ordem, senha, falhas, cancelamento, aspas | `tests/test_motor.py` (receitas de mentira, sem root nem internet) | `./dev test` |
| Uma receita não instala ou não funciona num Ubuntu de verdade | `tests/docker/` (instala de verdade como usuário comum) | `./dev docker git,node` |

## Regras das receitas

- **Toda receita é idempotente.** Rodar duas vezes não pode quebrar nem duplicar nada
  (`[ -f ... ] ||`, `no_terminal` com marcadores, `apt_instalar`).
- **`sistema` roda como root, num roteiro só** (a senha é pedida uma vez). `usuario` e `teste`
  rodam como a pessoa. Nada de `sudo` dentro de receita.
- **Dados da pessoa entram só por variável de ambiente** (`CAMPOS` → `ADON_*`, com
  `shlex.quote`). Nunca formate texto digitado dentro do shell.
- **Configuração de terminal só com `no_terminal <id> '<linha com @SHELL@>'`**: vale para
  bash e zsh e não duplica.
- **`teste` confere como a pessoa vai usar**: o `tests/docker` abre um terminal novo
  (`bash -ic`) e roda o comando de verdade.
- **Precisa funcionar no Ubuntu 22.04 e 24.04** (Zorin 17/18, Pop!_OS 22.04, Mint 21/22).
  Receita nova só entra com `./dev docker <id>` passando nos dois.

## Antes de dizer que terminou

- `./dev test` passa.
- Mexeu numa receita? `./dev docker <ids>` passa no 22.04 e no 24.04.
- Relate o que foi testado e o que não foi. Se algo falhou, mostre a saída.

## Não automatizado

- **Janela de senha (pkexec)**: no Docker usamos `sudo -n` (`ADON_DEV_ROOT_CMD`). A janela
  do polkit só aparece numa sessão gráfica de verdade.
