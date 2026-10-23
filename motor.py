# Motor do Adon Dev: receitas de instalação e quem as executa. Não depende de GTK (testável sozinho).
import getpass
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
    Receita(
        id="gh", titulo="GitHub CLI", grupo="Essenciais",
        resumo="O comando gh: criar repositórios, abrir pull requests e entrar no GitHub pelo terminal",
        instalado="command -v gh >/dev/null",
        sistema="""
apt_instalar curl ca-certificates
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
chmod a+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list
apt_repositorio_novo
apt_instalar gh
""",
        teste="gh --version",
        precisa=("git",),
    ),
    Receita(
        id="vscode", titulo="Visual Studio Code", grupo="Editores",
        resumo="O editor de código mais usado, direto do repositório da Microsoft (recebe atualizações)",
        instalado="command -v code >/dev/null || flatpak info com.visualstudio.code >/dev/null 2>&1",
        sistema="""
apt_instalar curl gpg ca-certificates
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor --yes -o /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list
# o pacote pergunta se pode adicionar o repositório; já adicionamos acima
echo "code code/add-microsoft-repo boolean false" | debconf-set-selections
apt_repositorio_novo
apt_instalar code
""",
        teste="code --version",
    ),
    Receita(
        id="php", titulo="PHP + Composer", grupo="Linguagens",
        resumo="PHP com as extensões que Laravel e WordPress pedem, e o Composer para as dependências",
        instalado="command -v php >/dev/null",
        sistema="""
apt_instalar php-cli php-common php-mbstring php-xml php-curl php-zip php-mysql php-sqlite3 php-intl php-bcmath php-gd unzip curl
if [ ! -x /usr/local/bin/composer ]; then
  T=$(mktemp -d)
  curl -fsSL -o "$T/setup.php" https://getcomposer.org/installer
  ESPERADO=$(curl -fsSL https://composer.github.io/installer.sig)
  OBTIDO=$(php -r "echo hash_file('sha384', '$T/setup.php');")
  [ "$ESPERADO" = "$OBTIDO" ] || { echo "Instalador do Composer com assinatura inválida"; exit 1; }
  php "$T/setup.php" --quiet --install-dir=/usr/local/bin --filename=composer
  rm -rf "$T"
fi
""",
        teste="php --version && composer --version",
    ),
    Receita(
        id="python", titulo="Python + uv", grupo="Linguagens",
        resumo="Python com o uv, que cria ambientes, instala pacotes e outras versões do Python em segundos",
        instalado="command -v uv >/dev/null || [ -x ~/.local/bin/uv ]",
        sistema="apt_instalar python3 python3-venv python3-pip curl ca-certificates",
        usuario="""
if [ ! -x ~/.local/bin/uv ]; then
  case "$(uname -m)" in aarch64|arm64) A=aarch64 ;; *) A=x86_64 ;; esac
  T=$(mktemp -d)
  curl -fsSL -o "$T/uv.tar.gz" "https://github.com/astral-sh/uv/releases/latest/download/uv-$A-unknown-linux-gnu.tar.gz"
  tar -xzf "$T/uv.tar.gz" -C "$T"
  mkdir -p ~/.local/bin && install -m 0755 "$T"/uv-*/uv "$T"/uv-*/uvx ~/.local/bin/
  rm -rf "$T"
fi
no_terminal python 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
""",
        teste='export PATH="$HOME/.local/bin:$PATH"; python3 --version && uv --version',
    ),
    Receita(
        id="docker", titulo="Docker", grupo="Ferramentas",
        resumo="Containers e Docker Compose, do repositório oficial, já liberado para usar sem sudo",
        instalado="command -v docker >/dev/null",
        sistema="""
apt_instalar ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
# Zorin, Mint e Pop!_OS informam a versão do Ubuntu em que se baseiam em UBUNTU_CODENAME
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
apt_repositorio_novo
apt_instalar docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "$ADON_USUARIO"
systemctl enable --now docker 2>/dev/null || true
""",
        teste='docker --version && docker compose version && getent group docker | grep -qw "$USER"',
    ),
]
POR_ID = {r.id: r for r in RECEITAS}
# o que só passa a valer depois de sair e entrar de novo na sessão
PEDE_NOVO_LOGIN = {"docker": "Para usar o Docker sem sudo, saia e entre de novo na sua sessão."}

# funções disponíveis dentro das receitas
PRELUDIO_SISTEMA = r"""
export DEBIAN_FRONTEND=noninteractive
apt_instalar() {
  # um apt-get update por execução, mesmo com várias receitas
  if [ ! -f "$ADON_APT_ATUALIZADO" ]; then apt-get update -q && touch "$ADON_APT_ATUALIZADO"; fi
  apt-get install -y -q "$@"
}
apt_repositorio_novo() {
  # depois de adicionar um repositório, o próximo apt_instalar precisa atualizar a lista
  rm -f "$ADON_APT_ATUALIZADO"
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
    env = {CAMPOS[k]: v for k, v in respostas.items() if k in CAMPOS and v}
    env["ADON_USUARIO"] = getpass.getuser()  # o roteiro de sistema roda como root e precisa saber quem é a pessoa
    return env


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
        atual, vistos = None, set()
        with subprocess.Popen(comando_root() + [script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True) as proc:
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
