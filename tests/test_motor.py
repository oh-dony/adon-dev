# Testes do motor sem root e sem internet: receitas de mentira e "root" = o próprio bash.
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import motor as M  # noqa: E402

R = M.Receita


def catalogo(tmp):
    return [
        R("base", "Base", "", "g", instalado="false", sistema=f"echo base >> {tmp}/ordem"),
        R("app", "App", "", "g", instalado="false", precisa=("base",),
          sistema=f"echo app >> {tmp}/ordem", usuario=f'echo "$ADON_GIT_NOME" > {tmp}/nome',
          teste=f"test -f {tmp}/nome"),
        R("quebra", "Quebra", "", "g", instalado="false", sistema="echo antes; false; echo depois"),
        R("so_usuario", "Só usuário", "", "g", instalado="false", usuario=f"touch {tmp}/usuario"),
    ]


class Motor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="adon-dev-teste-")
        self.cat = catalogo(self.tmp)
        self.avisos = []
        os.environ["ADON_DEV_ROOT_CMD"] = "bash"

    def tearDown(self):
        os.environ.pop("ADON_DEV_ROOT_CMD", None)

    def rodar(self, ids, respostas=None):
        return M.executar(ids, respostas or {}, lambda *a: self.avisos.append(a), f"{self.tmp}/logs", self.cat)

    def test_dependencia_vem_antes(self):
        self.assertEqual([r.id for r in M.plano(["app"], self.cat)], ["base", "app"])

    def test_root_roda_uma_vez_so_para_todas_as_receitas(self):
        """A senha de administrador é pedida uma vez: um único roteiro com a parte root de tudo."""
        chamadas = []
        real = M.subprocess.Popen
        M.subprocess.Popen = lambda cmd, **kw: (chamadas.append(cmd), real(cmd, **kw))[1]
        try:
            self.rodar(["app", "so_usuario"])
        finally:
            M.subprocess.Popen = real
        self.assertEqual(len([c for c in chamadas if str(c[-1]).endswith("sistema.sh")]), 1)
        self.assertEqual(Path(self.tmp, "ordem").read_text().split(), ["base", "app"])

    def test_tudo_certo(self):
        res = self.rodar(["app", "so_usuario"], {"git_nome": "Ana"})
        self.assertEqual(res, {"base": "ok", "app": "ok", "so_usuario": "ok"})
        self.assertEqual(Path(self.tmp, "nome").read_text().strip(), "Ana")
        self.assertIn(("app", "teste", "ok"), self.avisos)

    def test_falha_para_naquela_receita_e_guarda_o_registro(self):
        res = self.rodar(["quebra", "so_usuario"])
        self.assertEqual(res["quebra"], "falhou")
        self.assertEqual(res["so_usuario"], "ok", "uma receita quebrada não derruba as outras")
        log = Path(self.tmp, "logs", "quebra.log").read_text()
        self.assertIn("antes", log)
        self.assertNotIn("depois", log, "a receita para no primeiro erro (set -e)")

    def test_senha_cancelada(self):
        """Se a pessoa cancela a janela da senha, nada roda e todas ficam como 'cancelado'."""
        os.environ["ADON_DEV_ROOT_CMD"] = "false"
        res = self.rodar(["app", "so_usuario"])
        self.assertEqual(set(res.values()), {"cancelado"})
        self.assertFalse(Path(self.tmp, "usuario").exists())

    def test_nome_com_caracteres_especiais_nao_vira_comando(self):
        nome = "O'Brien $(touch /tmp/adon-dev-invadido) `id`"
        self.rodar(["app"], {"git_nome": nome})
        self.assertEqual(Path(self.tmp, "nome").read_text().strip(), nome)
        self.assertFalse(Path("/tmp/adon-dev-invadido").exists())


class NoTerminal(unittest.TestCase):
    """Configuração no .bashrc entra uma vez só, mesmo rodando a receita de novo."""

    def test_nao_duplica_no_bashrc(self):
        home = tempfile.mkdtemp(prefix="adon-dev-home-")
        env = {"HOME": home}
        script = "no_terminal x 'echo @SHELL@'"
        for _ in range(2):
            M._shell_usuario(script, env, f"{home}/log")
        rc = Path(home, ".bashrc").read_text()
        self.assertEqual(rc.count(">>> adon-dev x >>>"), 1)
        self.assertIn("echo bash", rc)


if __name__ == "__main__":
    unittest.main()
