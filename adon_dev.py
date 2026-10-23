#!/usr/bin/env python3
# Adon Dev — prepara o ambiente de programação depois de instalar o Linux.
import subprocess
import threading
import time
from math import pi
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

import motor as M  # noqa: E402

APP_ID = "com.adonay.dev"
APP_NAME = "Adon Dev"
VERSION = "0.1.0"
LOGS = Path(GLib.get_user_cache_dir()) / "adon-dev"
GITHUB_SSH = "https://github.com/settings/ssh/new"

# perfis: atalhos para marcar várias receitas de uma vez (só entram as que existem no catálogo)
PERFIS = [
    ("Front-end", "Sites e apps com JavaScript", ["git", "node", "vscode"]),
    ("Web com PHP", "Laravel, WordPress e afins", ["git", "php", "node", "docker", "vscode"]),
    ("Python", "Automação, dados e back-end", ["git", "python", "vscode"]),
    ("Tudo", "Marca tudo o que o Adon Dev sabe instalar", None),
]

CSS = """
.adon-titulo { font-size: 1.6em; font-weight: 800; }
.adon-desc { opacity: 0.75; }
.adon-perfil { padding: 12px 14px; border-radius: 14px; }
.adon-perfil .titulo { font-weight: 700; }
.adon-perfil .sub { font-size: 0.85em; opacity: 0.7; }
.adon-chave { font-family: monospace; font-size: 0.85em; padding: 10px; border-radius: 10px; }
.adon-ok { color: @success_color; }
.adon-erro { color: @error_color; }
"""


class Spinner(Gtk.DrawingArea):
    """Arco girando na cor de destaque (o Gtk.Spinner muda de cara conforme o tema de ícones)."""

    def __init__(self, size=22):
        super().__init__(content_width=size, content_height=size, valign=Gtk.Align.CENTER)
        self._angle, self._tick = 0.0, None
        self.set_draw_func(self._draw)

    def start(self):
        if self._tick is None:
            self._tick = self.add_tick_callback(self._step)

    def stop(self):
        if self._tick is not None:
            self.remove_tick_callback(self._tick)
            self._tick = None

    def _step(self, _w, clock):
        self._angle = (clock.get_frame_time() / 1e6 * 2 * pi * 1.2) % (2 * pi)
        self.queue_draw()
        return True

    def _draw(self, _a, cr, w, h):
        ok, acc = False, None
        try:
            ok, acc = self.get_style_context().lookup_color("accent_bg_color")
        except (AttributeError, TypeError):
            pass
        r, g, b = (acc.red, acc.green, acc.blue) if ok else (0.65, 0.89, 0.63)
        cr.set_line_width(3)
        cr.set_source_rgba(r, g, b, .22)
        cr.arc(w / 2, h / 2, min(w, h) / 2 - 2, 0, 2 * pi)
        cr.stroke()
        cr.set_source_rgba(r, g, b, 1)
        cr.set_line_cap(1)
        cr.arc(w / 2, h / 2, min(w, h) / 2 - 2, self._angle, self._angle + pi * 1.4)
        cr.stroke()


def entry_row(title, text="", placeholder=""):
    """Campo de texto numa linha (o Adw.EntryRow só existe a partir da libadwaita 1.2)."""
    row = Adw.ActionRow(title=title)
    entry = Gtk.Entry(text=text, placeholder_text=placeholder, valign=Gtk.Align.CENTER, hexpand=True,
                      width_chars=28)
    row.add_suffix(entry)
    return row, entry


def git_config(chave):
    r = subprocess.run(["git", "config", "--global", chave], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


ETAPA_TEXTO = {
    ("sistema", "rodando"): "Instalando pacotes do sistema…",
    ("usuario", "rodando"): "Configurando…",
    ("teste", "rodando"): "Conferindo se funciona…",
}


class Janela(Adw.ApplicationWindow):
    def __init__(self, app, catalogo=None):
        super().__init__(application=app, title=APP_NAME, default_width=760, default_height=720)
        self.catalogo = catalogo or M.RECEITAS
        self.instalado = {r.id: M.ja_instalado(r) for r in self.catalogo}
        # o Git vem marcado mesmo se já instalado: a configuração (nome, e-mail, chave) vale de qualquer jeito
        self.escolha = {r.id: r.id == "git" for r in self.catalogo}
        self.historico = []
        self.rodando = False

        self.pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, vexpand=True)
        self.toasts = Adw.ToastOverlay(child=self.pilha)
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title=APP_NAME, subtitle="Seu ambiente de programação"))
        self.voltar = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Voltar", visible=False)
        self.voltar.connect("clicked", lambda _b: self._voltar())
        header.pack_start(self.voltar)
        corpo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        corpo.append(header)
        corpo.append(self.toasts)
        self.set_content(corpo)

        self.pilha.add_named(self._pg_inicio(), "inicio")
        self.pilha.add_named(self._pg_git(), "git")

    # --- navegação
    def _ir(self, nome, widget=None):
        if widget is not None:
            antiga = self.pilha.get_child_by_name(nome)
            if antiga:
                self.pilha.remove(antiga)
            self.pilha.add_named(widget, nome)
        self.historico.append(self.pilha.get_visible_child_name())
        self.pilha.set_visible_child_name(nome)
        self.voltar.set_visible(not self.rodando)

    def _voltar(self):
        if self.historico and not self.rodando:
            self.pilha.set_visible_child_name(self.historico.pop())
            self.voltar.set_visible(bool(self.historico))

    def toast(self, texto):
        self.toasts.add_toast(Adw.Toast(title=texto, timeout=3))

    @staticmethod
    def _pagina(titulo, descricao, conteudo, botao=None, ao_clicar=None):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=24, margin_bottom=24,
                        margin_start=18, margin_end=18)
        caixa.append(Gtk.Label(label=titulo, xalign=0, wrap=True, css_classes=["adon-titulo"]))
        if descricao:
            caixa.append(Gtk.Label(label=descricao, xalign=0, wrap=True, css_classes=["adon-desc"]))
        conteudo.set_margin_top(12)
        caixa.append(conteudo)
        pagina = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        pagina.append(Gtk.ScrolledWindow(child=Adw.Clamp(child=caixa, maximum_size=640), vexpand=True,
                                         hscrollbar_policy=Gtk.PolicyType.NEVER))
        pagina.botao = None
        if botao:
            barra = Gtk.Box(margin_top=10, margin_bottom=14, margin_start=18, margin_end=18, halign=Gtk.Align.END)
            pagina.botao = Gtk.Button(label=botao, css_classes=["suggested-action", "pill"])
            pagina.botao.connect("clicked", lambda _b: ao_clicar())
            barra.append(pagina.botao)
            pagina.append(Gtk.Separator())
            pagina.append(barra)
        return pagina

    # --- 1. o que vai usar
    def _pg_inicio(self):
        conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        perfis = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, max_children_per_line=4,
                             min_children_per_line=2, column_spacing=10, row_spacing=10)
        for titulo, sub, ids in PERFIS:
            caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            caixa.append(Gtk.Label(label=titulo, xalign=0, css_classes=["titulo"]))
            caixa.append(Gtk.Label(label=sub, xalign=0, wrap=True, max_width_chars=18, css_classes=["sub"]))
            b = Gtk.Button(child=caixa, css_classes=["card", "adon-perfil"])
            b.connect("clicked", lambda _b, ids=ids: self._perfil(ids))
            perfis.append(b)
        conteudo.append(Gtk.Label(label="Comece por um perfil ou marque item por item", xalign=0,
                                  css_classes=["heading"]))
        conteudo.append(perfis)

        self.chaves = {}
        grupos = {}
        for r in self.catalogo:
            if r.grupo not in grupos:
                grupos[r.grupo] = Adw.PreferencesGroup(title=r.grupo)
                conteudo.append(grupos[r.grupo])
            row = Adw.ActionRow(title=r.titulo, subtitle=r.resumo + (" · já instalado" if self.instalado[r.id] else ""))
            sw = Gtk.Switch(active=self.escolha[r.id], valign=Gtk.Align.CENTER)
            sw.connect("notify::active", lambda s, _p, i=r.id: self.escolha.__setitem__(i, s.get_active()))
            row.add_suffix(sw)
            row.set_activatable_widget(sw)
            self.chaves[r.id] = sw
            grupos[r.grupo].add(row)
        return self._pagina("O que você vai usar?",
                            "Marque o que precisa para trabalhar. O Adon Dev instala e já deixa configurado.",
                            conteudo, "Continuar", self._depois_inicio)

    def _perfil(self, ids):
        alvo = set(ids) if ids is not None else {r.id for r in self.catalogo}
        for i, sw in self.chaves.items():
            sw.set_active(i in alvo)

    def _depois_inicio(self):
        if not any(self.escolha.values()):
            self.toast("Marque pelo menos um item")
            return
        if self.escolha.get("git"):
            self._ir("git")
        else:
            self._ir("resumo", self._pg_resumo())

    # --- 2. dados do Git
    def _pg_git(self):
        grupo = Adw.PreferencesGroup(description="Vão aparecer nos seus commits. Use o mesmo e-mail da sua conta do GitHub.")
        row_n, self.git_nome = entry_row("Nome", git_config("user.name"), "Seu nome")
        row_e, self.git_email = entry_row("E-mail", git_config("user.email"), "voce@exemplo.com")
        grupo.add(row_n)
        grupo.add(row_e)
        return self._pagina("Seus dados do Git", None, grupo, "Continuar", self._depois_git)

    def _depois_git(self):
        email = self.git_email.get_text().strip()
        if not self.git_nome.get_text().strip() or "@" not in email or "." not in email.split("@")[-1]:
            self.toast("Preencha seu nome e um e-mail válido")
            return
        self._ir("resumo", self._pg_resumo())

    def respostas(self):
        if not self.escolha.get("git"):
            return {}
        return {"git_nome": self.git_nome.get_text().strip(), "git_email": self.git_email.get_text().strip()}

    # --- 3. resumo
    def _pg_resumo(self):
        grupo = Adw.PreferencesGroup()
        for r in M.plano([i for i, v in self.escolha.items() if v], self.catalogo):
            grupo.add(Adw.ActionRow(title=r.titulo, subtitle=r.resumo))
        return self._pagina("Tudo pronto para começar",
                            "O sistema vai pedir a sua senha uma vez, para instalar os programas. "
                            "Pode levar alguns minutos, dependendo da internet.",
                            grupo, "Preparar meu ambiente", self._preparar)

    # --- 4. progresso
    def _preparar(self, ids=None):
        ids = ids or [i for i, v in self.escolha.items() if v]
        receitas = M.plano(ids, self.catalogo)
        grupo = Adw.PreferencesGroup()
        self.linhas = {}
        for r in receitas:
            row = Adw.ActionRow(title=r.titulo, subtitle="Esperando a sua senha…")
            estado = Gtk.Stack(valign=Gtk.Align.CENTER)
            spin = Spinner()
            estado.add_named(spin, "rodando")
            estado.add_named(Gtk.Image(icon_name="object-select-symbolic", css_classes=["adon-ok"]), "ok")
            estado.add_named(Gtk.Image(icon_name="dialog-error-symbolic", css_classes=["adon-erro"]), "falhou")
            detalhes = Gtk.Button(label="Ver detalhes", css_classes=["flat"], valign=Gtk.Align.CENTER, visible=False)
            detalhes.connect("clicked", lambda _b, i=r.id: self._detalhes(i))
            row.add_suffix(detalhes)
            row.add_suffix(estado)
            spin.start()
            self.linhas[r.id] = (row, estado, spin, detalhes)
            grupo.add(row)
        pagina = self._pagina("Preparando seu ambiente", "Não feche o Adon Dev enquanto instala.", grupo,
                              "Tentar de novo os que falharam", lambda: self._preparar(self.falhas))
        pagina.botao.set_visible(False)
        self.pg_progresso = pagina
        self.rodando = True
        self._ir("progresso", pagina)
        self.pasta_logs = LOGS / time.strftime("%Y%m%d-%H%M%S")

        def avisar(rid, etapa, status):
            GLib.idle_add(self._status, rid, etapa, status)

        def trabalho():
            res = M.executar(ids, self.respostas(), avisar, str(self.pasta_logs), self.catalogo)
            GLib.idle_add(self._terminou, res)
        threading.Thread(target=trabalho, daemon=True).start()

    def _status(self, rid, etapa, status):
        row, estado, spin, detalhes = self.linhas[rid]
        if status == "rodando" and etapa == "sistema":
            # a senha foi aceita: quem ainda não começou está só esperando a vez
            for outra, (r, *_x) in self.linhas.items():
                if outra != rid and r.get_subtitle() == "Esperando a sua senha…":
                    r.set_subtitle("Na fila…")
        if status == "ok" and etapa == "sistema":
            row.set_subtitle("Pacotes instalados, falta configurar")
        elif status == "rodando":
            row.set_subtitle(ETAPA_TEXTO.get((etapa, status), "Trabalhando…"))
        elif status == "falhou":
            row.set_subtitle("Não deu certo")
            spin.stop()
            estado.set_visible_child_name("falhou")
            detalhes.set_visible(True)
        elif status == "cancelado":
            row.set_subtitle("Cancelado: a senha não foi confirmada")
            spin.stop()
            estado.set_visible_child_name("falhou")
        return False

    def _terminou(self, res):
        self.rodando = False
        for rid, status in res.items():
            row, estado, spin, _d = self.linhas[rid]
            if status == "ok":
                spin.stop()
                estado.set_visible_child_name("ok")
                row.set_subtitle("Pronto")
                self.instalado[rid] = True
        self.falhas = [i for i, s in res.items() if s != "ok"]
        self.resultado = res
        if not self.falhas:
            self._ir("pronto", self._pg_pronto())
            return False
        self.voltar.set_visible(True)
        self.pg_progresso.botao.set_visible(True)
        self.toast("Alguns itens não foram instalados" if any(s == "falhou" for s in res.values())
                   else "A senha não foi confirmada")
        return False

    def _detalhes(self, rid):
        log = self.pasta_logs / f"{rid}.log"
        texto = log.read_text(errors="ignore")[-4000:] if log.exists() else "Sem registro."
        view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                            top_margin=10, bottom_margin=10, left_margin=10, right_margin=10)
        view.get_buffer().set_text(texto)
        win = Adw.Window(transient_for=self, modal=True, default_width=640, default_height=460,
                         title=f"O que aconteceu: {self.linhas[rid][0].get_title()}")
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.append(Adw.HeaderBar())
        caixa.append(Gtk.ScrolledWindow(child=view, vexpand=True))
        win.set_content(caixa)
        win.present()

    # --- 5. pronto
    def _pg_pronto(self):
        conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        conteudo.append(Gtk.Label(label="Abra um terminal novo para usar o que foi instalado.", xalign=0, wrap=True))
        chave = Path.home() / ".ssh" / "id_ed25519.pub"
        if self.resultado.get("git") == "ok" and chave.exists():
            texto = chave.read_text().strip()
            grupo = Adw.PreferencesGroup(title="Sua chave SSH",
                                         description="Cole no GitHub para enviar código sem digitar senha.")
            rotulo = Gtk.Label(label=texto, wrap=True, wrap_mode=2, selectable=True, xalign=0,
                               css_classes=["card", "adon-chave"])
            grupo.add(rotulo)
            botoes = Gtk.Box(spacing=8, margin_top=8)
            copiar = Gtk.Button(label="Copiar chave", css_classes=["pill"])
            copiar.connect("clicked", lambda _b: (Gdk.Display.get_default().get_clipboard().set(texto),
                                                  self.toast("Chave copiada")))
            abrir = Gtk.Button(label="Abrir o GitHub", css_classes=["pill", "suggested-action"])
            abrir.connect("clicked", lambda _b: Gio.AppInfo.launch_default_for_uri(GITHUB_SSH, None))
            botoes.append(copiar)
            botoes.append(abrir)
            grupo.add(botoes)
            conteudo.append(grupo)
        fechar = self._pagina("Seu ambiente está pronto 🎉", None, conteudo, "Fechar", self.close)
        self.voltar.set_visible(False)
        return fechar


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=getattr(Gio.ApplicationFlags, "DEFAULT_FLAGS", Gio.ApplicationFlags.FLAGS_NONE))

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        if hasattr(css, "load_from_string"):
            css.load_from_string(CSS)
        else:
            css.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        icons = Path(__file__).resolve().parent / "icons"
        if icons.is_dir():
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(icons))

    def do_activate(self):
        (self.props.active_window or Janela(self)).present()


if __name__ == "__main__":
    import sys
    sys.exit(App().run(sys.argv))
