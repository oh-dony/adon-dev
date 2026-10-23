# Percorre o assistente com receitas de mentira (sem root, sem internet). Pulado sem tela.
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib  # noqa: E402

import adon_dev as D  # noqa: E402
import motor as M  # noqa: E402

TEM_TELA = Gdk.Display.get_default() is not None


def esperar(cond, segundos=20):
    fim = GLib.get_monotonic_time() + segundos * 1_000_000
    ctx = GLib.MainContext.default()
    while not cond() and GLib.get_monotonic_time() < fim:
        ctx.iteration(True)
    return cond()


def rotulos(widget):
    out, filho = [], widget.get_first_child()
    if hasattr(widget, "get_label") and isinstance(widget.get_label(), str):
        out.append(widget.get_label())
    while filho:
        out += rotulos(filho)
        filho = filho.get_next_sibling()
    return out


@unittest.skipUnless(TEM_TELA, "precisa de tela (sessão gráfica ou xvfb-run)")
class Assistente(unittest.TestCase):
    def setUp(self):
        Adw.init()
        self.tmp = tempfile.mkdtemp(prefix="adon-dev-ui-")
        D.LOGS = Path(self.tmp) / "logs"
        self.cat = [
            M.Receita("boa", "Boa", "funciona", "Grupo", instalado="false", sistema="true",
                      usuario=f"touch {self.tmp}/boa"),
            M.Receita("ruim", "Ruim", "quebra", "Grupo", instalado="false", sistema="echo motivo do erro; false"),
        ]
        os.environ["ADON_DEV_ROOT_CMD"] = "bash"
        self.win = D.Janela(None, self.cat)

    def tearDown(self):
        os.environ.pop("ADON_DEV_ROOT_CMD", None)
        self.win.destroy()

    def preparar(self, *ids):
        for i in ids:
            self.win.chaves[i].set_active(True)
        self.win._depois_inicio()
        self.assertEqual(self.win.pilha.get_visible_child_name(), "resumo")
        self.win._preparar()
        self.assertTrue(esperar(lambda: not self.win.rodando), "a instalação não terminou")

    def test_sem_nada_marcado_nao_avanca(self):
        self.win._depois_inicio()
        self.assertEqual(self.win.pilha.get_visible_child_name(), "inicio")

    def test_tudo_certo_chega_na_tela_final(self):
        self.preparar("boa")
        self.assertEqual(self.win.pilha.get_visible_child_name(), "pronto")
        self.assertTrue(Path(self.tmp, "boa").exists())

    def test_falha_mostra_detalhes_e_tentar_de_novo(self):
        self.preparar("boa", "ruim")
        self.assertEqual(self.win.pilha.get_visible_child_name(), "progresso")
        row, estado, _spin, detalhes = self.win.linhas["ruim"]
        self.assertEqual(estado.get_visible_child_name(), "falhou")
        self.assertTrue(detalhes.get_visible())
        self.assertTrue(self.win.pg_progresso.botao.get_visible(), "botão de tentar de novo")
        self.assertEqual(self.win.falhas, ["ruim"])
        self.assertEqual(self.win.linhas["boa"][1].get_visible_child_name(), "ok")

    def test_senha_cancelada(self):
        os.environ["ADON_DEV_ROOT_CMD"] = "false"
        self.preparar("boa")
        row = self.win.linhas["boa"][0]
        self.assertIn("Cancelado", row.get_subtitle())
        self.assertTrue(self.win.pg_progresso.botao.get_visible())

    def test_avisa_quando_precisa_sair_e_entrar_de_novo(self):
        """O Docker só funciona sem sudo depois de um novo login (o grupo vale a partir da sessão)."""
        self.cat.append(M.Receita("docker", "Docker", "", "Grupo", instalado="false", sistema="true"))
        self.win.destroy()
        self.win = D.Janela(None, self.cat)
        self.preparar("docker")
        self.assertEqual(self.win.pilha.get_visible_child_name(), "pronto")
        textos = rotulos(self.win.pilha.get_child_by_name("pronto"))
        self.assertTrue(any("saia e entre de novo" in t for t in textos), textos)

    def test_perfil_tudo_marca_todas(self):
        self.win._perfil(None)
        self.assertTrue(all(self.win.escolha.values()))


if __name__ == "__main__":
    unittest.main()
