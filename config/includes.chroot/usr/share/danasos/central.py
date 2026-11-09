"""Painel gráfico local do danasOS. Abre somente pelo menu do Xfce."""

from pathlib import Path
import subprocess
import webbrowser

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from catalogo import APLICATIVOS

PASTA = Path(__file__).resolve().parent
CSS = b"""
window { background-color: #100c19; color: #f6efff; }
label { color: #f6efff; }
.cabecalho {
  background-image: linear-gradient(125deg, #332049, #1c142a 64%, #17241d);
  border: 1px solid #53396e; border-radius: 14px; padding: 21px;
}
.marca { color: #b7fb6b; font-weight: bold; font-size: 12px; letter-spacing: 2px; }
.titulo { font-size: 36px; font-weight: bold; }
.secao { font-size: 17px; font-weight: bold; }
.detalhe { color: #d2c2e2; font-size: 12px; }
.rodape { color: #b7fb6b; font-size: 12px; }
button.cartao, button.acao {
  background-image: none; background-color: #21172d; color: #f6efff;
  border: 1px solid #422c57; border-radius: 10px; padding: 11px 13px;
  box-shadow: none; text-shadow: none;
}
button.cartao:hover, button.acao:hover { background-color: #342347; border-color: #a775df; }
button.cartao:disabled { opacity: 0.58; }
button.acao label { color: #b7fb6b; font-weight: bold; }
scrolledwindow, viewport { background-color: #100c19; }
"""


def rotulo(texto, classe=None):
    label = Gtk.Label(label=texto, xalign=0)
    label.set_line_wrap(True)
    label.set_max_width_chars(44)
    if classe:
        label.get_style_context().add_class(classe)
    return label


def caixa(espaco=0):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=espaco)


class Central(Gtk.Window):
    def __init__(self):
        super().__init__(title="Central danasOS")
        self.set_default_size(880, 650)
        self.set_icon_from_file(str(PASTA / "danasos.svg"))
        self.connect("destroy", Gtk.main_quit)
        estilo = Gtk.CssProvider()
        estilo.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), estilo, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        rolagem = Gtk.ScrolledWindow()
        rolagem.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(rolagem)
        conteudo = caixa(15)
        conteudo.set_border_width(22)
        rolagem.add(conteudo)

        cabecalho = Gtk.Box(spacing=18)
        cabecalho.get_style_context().add_class("cabecalho")
        cabecalho.pack_start(Gtk.Image.new_from_file(str(PASTA / "danasos.svg")), False, False, 0)
        texto = caixa(2)
        texto.pack_start(rotulo("EDIÇÃO NOITE EM NEON", "marca"), False, False, 0)
        texto.pack_start(rotulo("danasOS", "titulo"), False, False, 0)
        texto.pack_start(rotulo("Xfce · Central de jogos e sistema", "detalhe"), False, False, 0)
        cabecalho.pack_start(texto, True, True, 0)
        conteudo.pack_start(cabecalho, False, False, 0)

        acoes = Gtk.FlowBox(column_spacing=8, row_spacing=8, homogeneous=True)
        acoes.set_selection_mode(Gtk.SelectionMode.NONE)
        for titulo, argumentos in (
            ("Loja de aplicativos", ["gnome-software"]),
            ("Atualizações", None),
            ("Driver NVIDIA", ["xfce4-terminal", "--hold", "--execute", "sudo", "danasos-driver-nvidia"]),
            ("Diagnóstico", ["xfce4-terminal", "--hold", "--execute", "danasos-diagnostico"]),
            ("Configurações", ["xfce4-settings-manager"]),
        ):
            botao = Gtk.Button(label=titulo)
            botao.get_style_context().add_class("acao")
            if argumentos:
                botao.connect("clicked", lambda _, cmd=argumentos: self.abrir(cmd))
            else:
                botao.connect("clicked", self.atualizacoes)
            acoes.add(botao)
        conteudo.pack_start(acoes, False, False, 0)

        conteudo.pack_start(rotulo("Launchers", "secao"), False, False, 0)
        grade = Gtk.FlowBox(column_spacing=8, row_spacing=8, homogeneous=True)
        grade.set_min_children_per_line(1)
        grade.set_max_children_per_line(2)
        grade.set_selection_mode(Gtk.SelectionMode.NONE)
        instalados = self.listar_flatpaks()
        for nome, descricao, flatpak in APLICATIVOS:
            comando = ["flatpak", "run", flatpak]
            instalado = flatpak in instalados
            botao = Gtk.Button()
            botao.get_style_context().add_class("cartao")
            linhas = caixa(3)
            linhas.pack_start(rotulo(nome, "secao"), False, False, 0)
            linhas.pack_start(rotulo(descricao, "detalhe"), False, False, 0)
            linhas.pack_start(rotulo("ABRIR" if instalado else "PENDENTE", "rodape"), False, False, 0)
            botao.add(linhas)
            botao.set_sensitive(instalado)
            botao.connect("clicked", lambda _, cmd=comando: self.abrir(cmd))
            grade.add(botao)
        conteudo.pack_start(grade, False, False, 0)

        links = Gtk.Box(spacing=14)
        for nome, url in (
            ("Epic Games Launcher Preview", "https://launcher.epicgames.com/"),
            ("Consultar jogo no ProtonDB", "https://www.protondb.com/"),
        ):
            link = Gtk.LinkButton(uri=url, label=nome)
            link.connect("activate-link", self.abrir_link)
            links.pack_start(link, False, False, 0)
        conteudo.pack_start(links, False, False, 0)
        conteudo.pack_start(
            rotulo("Proton e os clientes podem baixar componentes quando abrem pela primeira vez.", "rodape"),
            False, False, 0,
        )

    @staticmethod
    def listar_flatpaks():
        try:
            saida = subprocess.check_output(
                ["flatpak", "list", "--app", "--columns=application"],
                text=True, stderr=subprocess.DEVNULL, timeout=4,
            )
            return set(saida.split())
        except (OSError, subprocess.SubprocessError):
            return set()

    @staticmethod
    def abrir_link(botao):
        webbrowser.open(botao.get_uri())
        return True

    def atualizacoes(self, _):
        ativo = Path("/etc/danasos/auto-update").is_file()
        painel = Gtk.MessageDialog(
            transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE, text="Atualizações do danasOS",
        )
        estado = "Ativada" if ativo else "Desativada"
        painel.format_secondary_text(
            f"Atualização automática: {estado}.\n\n"
            "Ao ativar, o danasOS instala versões assinadas da Central e do tema pelo canal cadastrado."
        )
        painel.add_button("Fechar", Gtk.ResponseType.CLOSE)
        painel.add_button("Abrir loja", 1)
        painel.add_button("Desativar automática" if ativo else "Ativar automática", 2)
        resposta = painel.run()
        painel.destroy()
        if resposta == 1:
            self.abrir(["gnome-software", "--mode=updates"])
        elif resposta == 2:
            self.abrir([
                "xfce4-terminal", "--hold", "--execute", "sudo", "/usr/bin/danasos-auto-update",
                "desativar" if ativo else "ativar",
            ])

    def abrir(self, comando):
        try:
            subprocess.Popen(comando)
        except OSError as erro:
            aviso = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE, text="Não deu para abrir o aplicativo.",
            )
            aviso.format_secondary_text(str(erro))
            aviso.run()
            aviso.destroy()


if __name__ == "__main__":
    janela = Central()
    janela.show_all()
    Gtk.main()
