# Motor do Adon Dev: receitas de instalação e quem as executa. Não depende de GTK (testável sozinho).
import os
import shlex
import subprocess
from dataclasses import dataclass, field


@dataclass
class Receita:
    id: str
    titulo: str
    resumo: str
    grupo: str
    instalado: str            # shell como usuário; sai 0 se já está instalado (só para mostrar na tela)
    sistema: str = ""         # shell como root: pacotes do sistema, repositórios
    usuario: str = ""         # shell como a pessoa: configurações, versões de linguagem
    teste: str = ""           # shell como a pessoa; sai 0 se está funcionando
    precisa: tuple = ()       # ids de outras receitas que vêm antes
    pergunta: tuple = ()      # dados que a tela precisa pedir (ver CAMPOS)


# dados pedidos na tela -> variável de ambiente usada pelas receitas
CAMPOS = {"git_nome": "ADON_GIT_NOME", "git_email": "ADON_GIT_EMAIL"}

RECEITAS = [
    Receita(
        id="git", titulo="Git", grupo="Essenciais",
        resumo="Controle de versão, já configurado com seu nome, e-mail e uma chave SSH",
        instalado="command -v git >/dev/null",
        sistema="apt_instalar git openssh-client",
        usuario="""
if [ -n "${ADON_GIT_NOME:-}" ]; then git config --global user.name "$ADON_GIT_NOME"; fi
if [ -n "${ADON_GIT_EMAIL:-}" ]; then git config --global user.email "$ADON_GIT_EMAIL"; fi
git config --global init.defaultBranch main
mkdir -p ~/.ssh && chmod 700 ~/.ssh
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -q -t ed25519 -N "" -C "${ADON_GIT_EMAIL:-$USER}" -f ~/.ssh/id_ed25519
""",
        teste="""
git --version
[ -z "${ADON_GIT_EMAIL:-}" ] || [ "$(git config --global user.email)" = "$ADON_GIT_EMAIL" ]
[ -f ~/.ssh/id_ed25519.pub ]
""",
        pergunta=("git_nome", "git_email"),
    ),
    Receita(
        id="node", titulo="Node.js", grupo="Linguagens",
        resumo="JavaScript fora do navegador, na versão LTS, com o fnm para trocar de versão por projeto",
        instalado="command -v node >/dev/null || [ -x ~/.local/share/fnm/fnm ]",
        sistema="apt_instalar curl unzip ca-certificates",
        usuario="""
D=~/.local/share/fnm
if [ ! -x "$D/fnm" ]; then
  case "$(uname -m)" in aarch64|arm64) Z=fnm-arm64.zip ;; *) Z=fnm-linux.zip ;; esac
  T=$(mktemp -d)
  curl -fsSL -o "$T/fnm.zip" "https://github.com/Schniz/fnm/releases/latest/download/$Z"
  mkdir -p "$D" && unzip -q -o "$T/fnm.zip" -d "$D" && chmod +x "$D/fnm"
  rm -rf "$T"
fi
no_terminal node 'export PATH="$HOME/.local/share/fnm:$PATH"; eval "$(fnm env --use-on-cd --shell @SHELL@)"'
"$D/fnm" install --lts
"$D/fnm" default lts-latest
""",
        teste="""
export PATH="$HOME/.local/share/fnm:$PATH"; eval "$(fnm env --shell bash)"
node --version && npm --version
""",
    ),
]
POR_ID = {r.id: r for r in RECEITAS}

# funções disponíveis dentro das receitas
PRELUDIO_SISTEMA = r"""
export DEBIAN_FRONTEND=noninteractive
apt_instalar() {
  # um apt-get update por execução, mesmo com várias receitas
  if [ ! -f "$ADON_APT_ATUALIZADO" ]; then apt-get update -q && touch "$ADON_APT_ATUALIZADO"; fi
  apt-get install -y -q "$@"
}
"""
PRELUDIO_USUARIO = r"""
no_terminal() {
  # adiciona a configuração ao .bashrc (e ao .zshrc, se existir) uma vez só, entre marcadores
  local id=$1 modelo=$2 rc sh
  [ -f ~/.bashrc ] || touch ~/.bashrc
  for rc in ~/.bashrc ~/.zshrc; do
    [ -f "$rc" ] || continue
    grep -q ">>> adon-dev $id >>>" "$rc" && continue
    sh=bash; [ "$rc" = ~/.zshrc ] && sh=zsh
    printf '\n# >>> adon-dev %s >>>\n%s\n# <<< adon-dev %s <<<\n' "$id" "${modelo//@SHELL@/$sh}" "$id" >> "$rc"
  done
}
"""


def plano(ids, catalogo=None):
    """Receitas escolhidas mais as que elas precisam, na ordem do catálogo."""
    catalogo = catalogo or RECEITAS
    por_id = {r.id: r for r in catalogo}
    escolhidas = set()

    def incluir(i):
        if i not in escolhidas:
            escolhidas.add(i)
            for dep in por_id[i].precisa:
                incluir(dep)
    for i in ids:
        incluir(i)
    return [r for r in catalogo if r.id in escolhidas]


def ambiente(respostas):
    return {CAMPOS[k]: v for k, v in respostas.items() if k in CAMPOS and v}


def _exports(env):
    return "".join(f"export {k}={shlex.quote(v)}\n" for k, v in env.items())


def roteiro_sistema(receitas, env, marca_apt):
    """Um roteiro só com a parte root de todas as receitas (a senha é pedida uma vez).
    Cada receita roda num subshell com set -e e é anunciada com linhas '@@ <id> <status>'."""
    partes = ["#!/bin/bash", "set -u", _exports(env | {"ADON_APT_ATUALIZADO": marca_apt}), PRELUDIO_SISTEMA]
    for r in receitas:
        if r.sistema.strip():
            # o status vai numa linha separada: dentro de "( ... ) && ok || falhou" o bash ignora o
            # set -e, e uma receita quebrada no meio sairia como ok
            partes.append(f"echo '@@ {r.id} rodando'\n"
                          f"( set -e\n{r.sistema}\n) 2>&1\n"
                          f"if [ $? -eq 0 ]; then echo '@@ {r.id} ok'; else echo '@@ {r.id} falhou'; fi\n")
    return "\n".join(partes)


def comando_root():
    if "ADON_DEV_ROOT_CMD" in os.environ:  # testes: "sudo -n"
        return shlex.split(os.environ["ADON_DEV_ROOT_CMD"])
    return ["bash"] if os.geteuid() == 0 else ["pkexec", "bash"]


def _shell_usuario(script, env, log):
    corpo = "set -eu\n" + _exports(env) + PRELUDIO_USUARIO + script
    with open(log, "a") as out:
        r = subprocess.run(["bash", "-c", corpo], stdout=out, stderr=subprocess.STDOUT, env=os.environ | env)
    return r.returncode == 0


def executar(ids, respostas, avisar, pasta_logs, catalogo=None):
    """Instala as receitas. avisar(id, etapa, status) com etapa em sistema/usuario/teste e status em
    rodando/ok/falhou/cancelado. Devolve {id: 'ok'|'falhou'|'cancelado'}. Bloqueia: rode numa thread."""
    receitas, env = plano(ids, catalogo), ambiente(respostas)
    os.makedirs(pasta_logs, exist_ok=True)
    log = {r.id: os.path.join(pasta_logs, f"{r.id}.log") for r in receitas}
    resultado = {r.id: "ok" for r in receitas}

    com_sistema = [r for r in receitas if r.sistema.strip()]
    if com_sistema:
        script = os.path.join(pasta_logs, "sistema.sh")
        with open(script, "w") as f:
            f.write(roteiro_sistema(com_sistema, env, os.path.join(pasta_logs, ".apt-atualizado")))
        proc = subprocess.Popen(comando_root() + [script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        atual, vistos = None, set()
        for linha in proc.stdout:
            if linha.startswith("@@ "):
                _, rid, status = linha.split()
                atual = rid if status == "rodando" else None
                vistos.add(rid)
                if status == "falhou":
                    resultado[rid] = "falhou"
                avisar(rid, "sistema", status)
            elif atual:
                with open(log[atual], "a") as out:
                    out.write(linha)
        proc.wait()
        if not vistos:  # pkexec recusado ou senha cancelada: nada rodou
            for r in receitas:
                resultado[r.id] = "cancelado"
                avisar(r.id, "sistema", "cancelado")
            return resultado

    for r in receitas:
        if resultado[r.id] != "ok":
            continue
        for etapa, script in (("usuario", r.usuario), ("teste", r.teste)):
            if not script.strip():
                continue
            avisar(r.id, etapa, "rodando")
            ok = _shell_usuario(script, env, log[r.id])
            avisar(r.id, etapa, "ok" if ok else "falhou")
            if not ok:
                resultado[r.id] = "falhou"
                break
    return resultado


def ja_instalado(receita):
    return subprocess.run(["bash", "-c", receita.instalado], capture_output=True).returncode == 0
