"""Painel gráfico local do danasOS. Abre somente pelo menu do Xfce."""

from collections import deque
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from catalogo import APLICATIVOS
from configuracoes import APPS_NATIVOS, MODULOS, PERFIS_ENERGIA, PERFIS_TEXTO

PASTA = Path(__file__).resolve().parent
STATUS = Path("/var/lib/danasos-auto-update/status.json")
CANAL = "https://vitudanas.github.io/danasOS/apt/"
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
.cartao, button.acao {
  background-image: none; background-color: #21172d; color: #f6efff;
  border: 1px solid #422c57; border-radius: 10px; padding: 11px 13px;
  box-shadow: none; text-shadow: none;
}
button.acao:hover, button.acao:focus { background-color: #342347; border-color: #a775df; }
button.acao:disabled { opacity: 0.58; }
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
        self.apps = {}
        self.transacao = False
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
        texto.pack_start(rotulo(f"Central de jogos e sistema · {self.versao()}", "detalhe"), False, False, 0)
        cabecalho.pack_start(texto, True, True, 0)
        conteudo.pack_start(cabecalho, False, False, 0)

        acoes = Gtk.FlowBox(column_spacing=8, row_spacing=8, homogeneous=True)
        acoes.set_selection_mode(Gtk.SelectionMode.NONE)
        for titulo, acao in (
            ("Configurações danasOS", self.configuracoes),
            ("Atualizações", self.atualizacoes),
            ("Loja de aplicativos", lambda _: self.abrir(["gnome-software"])),
            ("Sobre", self.sobre),
        ):
            botao = Gtk.Button(label=titulo)
            botao.get_style_context().add_class("acao")
            botao.connect("clicked", acao)
            acoes.add(botao)
        conteudo.pack_start(acoes, False, False, 0)

        principais = {"Steam", "Heroic", "Prism Launcher", "Faugus"}
        for titulo, principal in (("Escolha por biblioteca ou jogo", True), ("Ferramentas avançadas", False)):
            conteudo.pack_start(rotulo(titulo, "secao"), False, False, 0)
            grade = Gtk.FlowBox(column_spacing=8, row_spacing=8, homogeneous=True)
            grade.set_min_children_per_line(1)
            grade.set_max_children_per_line(2)
            grade.set_selection_mode(Gtk.SelectionMode.NONE)
            for nome, descricao, app in APLICATIVOS:
                if (nome in principais) == principal:
                    grade.add(self.cartao(nome, descricao, app))
            conteudo.pack_start(grade, False, False, 0)
        self.catalogo_status = rotulo("", "detalhe")
        conteudo.pack_start(self.catalogo_status, False, False, 0)
        conteudo.pack_start(Gtk.LinkButton(uri="https://www.protondb.com/", label="Compatibilidade no ProtonDB"),
                            False, False, 0)
        conteudo.pack_start(
            rotulo("Proton e os clientes podem baixar componentes quando abrem pela primeira vez.", "rodape"),
            False, False, 0,
        )
        self.refazer_catalogo()

    @staticmethod
    def versao():
        try:
            return subprocess.check_output(
                ["dpkg-query", "-W", "-f=${Version}", "danasos-experience"],
                text=True, stderr=subprocess.DEVNULL, timeout=3,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            return "versão indisponível"

    def cartao(self, nome, descricao, app):
        linhas = caixa(6)
        linhas.get_style_context().add_class("cartao")
        linhas.pack_start(rotulo(nome, "secao"), False, False, 0)
        linhas.pack_start(rotulo(descricao, "detalhe"), True, True, 0)
        estado = rotulo("Consultando…", "rodape")
        linhas.pack_start(estado, False, False, 0)
        acoes = Gtk.Box(spacing=6)
        principal = Gtk.Button(label="Instalar")
        principal.set_sensitive(False)
        principal.connect("clicked", self.acao_app, app, False)
        atualizar = Gtk.Button(label="Atualizar")
        atualizar.set_no_show_all(True)
        atualizar.connect("clicked", self.acao_app, app, True)
        acoes.pack_start(principal, False, False, 0)
        acoes.pack_start(atualizar, False, False, 0)
        linhas.pack_start(acoes, False, False, 0)
        self.apps[app] = {"estado": estado, "principal": principal, "atualizar": atualizar}
        return linhas

    def refazer_catalogo(self, mensagem=""):
        try:
            instalacoes = {}
            for escopo in ("--system", "--user"):
                saida = subprocess.check_output(
                    ["flatpak", escopo, "list", "--app", "--columns=application"],
                    text=True, stderr=subprocess.PIPE, timeout=3,
                )
                instalacoes.update((app, escopo) for app in saida.split())
        except (OSError, subprocess.SubprocessError):
            instalacoes = None
            mensagem = mensagem or "Erro ao consultar os Flatpaks. Abra a loja para conferir."
        self.catalogo_status.set_text(mensagem)
        for app, cartao in self.apps.items():
            nativo = next((c for c in APPS_NATIVOS.get(app, ()) if shutil.which(c)), None)
            escopo = (instalacoes or {}).get(app)
            cartao.update(nativo=nativo, escopo=escopo)
            cartao["principal"].set_label("Abrir" if escopo or nativo else "Instalar")
            cartao["principal"].set_sensitive(bool(nativo or instalacoes is not None))
            cartao["atualizar"].set_visible(bool(escopo))
            situacao = ("Instalado · Flatpak" if escopo else "Instalado · sistema" if nativo
                        else "Disponível no Flathub" if instalacoes is not None else "Estado indisponível")
            cartao["estado"].set_text(situacao)

    def acao_app(self, _, app, atualizar):
        cartao = self.apps[app]
        escopo = cartao["escopo"]
        if not atualizar and (escopo or cartao["nativo"]):
            self.abrir(["flatpak", escopo, "run", app] if escopo else [cartao["nativo"]])
            return
        comando = ["flatpak", escopo or "--system"]
        if atualizar:
            comando += ["update", "--app", "--noninteractive", "-y", app]
        else:
            comando += ["install", "--app", "--noninteractive", "-y", "flathub", app]
        cartao["estado"].set_text("Atualizando…" if atualizar else "Instalando…")
        self.operacao(comando, "Atualizando aplicativo" if atualizar else "Instalando aplicativo",
                      cancelar=True, ao_terminar=self.refazer_catalogo)

    def aviso(self, titulo, texto, tipo=Gtk.MessageType.ERROR):
        dialogo = Gtk.MessageDialog(transient_for=self, modal=True, message_type=tipo,
                                    buttons=Gtk.ButtonsType.CLOSE, text=titulo)
        dialogo.format_secondary_text(texto)
        dialogo.run()
        dialogo.destroy()

    def operacao(self, comando, titulo, cancelar=False, ao_terminar=None):
        if self.transacao:
            self.aviso("Operação em andamento", "Espere a tarefa atual terminar.")
            return
        self.transacao = True
        dialogo = Gtk.Dialog(title=titulo, transient_for=self, modal=True)
        dialogo.set_default_size(560, 115)
        detalhe = rotulo("Preparando…", "detalhe")
        detalhe.set_margin_start(14)
        detalhe.set_margin_end(14)
        detalhe.set_margin_top(14)
        detalhe.set_margin_bottom(14)
        dialogo.get_content_area().add(detalhe)
        dialogo.connect("delete-event", lambda *_: True)
        parar = threading.Event()
        if cancelar:
            dialogo.add_button("Cancelar", Gtk.ResponseType.CANCEL)
            dialogo.connect("response", lambda *_: parar.set())

        def terminar(codigo, saida):
            self.transacao = False
            dialogo.destroy()
            mensagem = "Operação cancelada." if parar.is_set() else (
                "Operação concluída." if codigo == 0 else "A operação falhou."
            )
            if ao_terminar:
                ao_terminar(mensagem)
            if codigo != 0 and not parar.is_set():
                self.aviso(mensagem, saida or "Verifique a rede ou a autorização e tente de novo.")
            elif codigo == 0 and not cancelar:
                self.aviso(mensagem, saida or "Estado atualizado na Central.", Gtk.MessageType.INFO)
            return False

        def trabalhador():
            import signal
            import time

            ultimas = deque(maxlen=14)
            try:
                ambiente = dict(os.environ, TERM="dumb")
                with subprocess.Popen(comando, env=ambiente, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, errors="replace") as processo:
                    def vigiar():
                        while processo.poll() is None:
                            if parar.wait(0.3):
                                if processo.poll() is None:
                                    processo.send_signal(signal.SIGINT)
                                    time.sleep(3)
                                    if processo.poll() is None:
                                        processo.terminate()
                                break

                    if cancelar:
                        threading.Thread(target=vigiar, daemon=True).start()
                    for linha in processo.stdout:
                        linha = linha.strip()
                        if linha:
                            ultimas.append(linha)
                            GLib.idle_add(detalhe.set_text, linha[:250])
                    codigo = processo.wait()
            except OSError as erro:
                ultimas.append(str(erro))
                codigo = 1
            GLib.idle_add(terminar, codigo, "\n".join(ultimas))

        dialogo.show_all()
        threading.Thread(target=trabalhador, daemon=True).start()

    def sobre(self, _):
        self.aviso("Sobre o danasOS",
                   f"Pacote de experiência {self.versao()}\n"
                   "Noite em Neon · jogos e configurações.\n\n"
                   "Projetos da base: Linux Mint, Ubuntu, Debian, Xfce, kernel Linux e Flatpak. "
                   "Drivers e aplicativos mantêm autoria e licenças dos seus projetos.",
                   Gtk.MessageType.INFO)

    def configuracoes(self, _):
        dialogo = Gtk.Dialog(title="Configurações danasOS", transient_for=self, modal=True)
        dialogo.set_default_size(650, 610)
        dialogo.add_button("Fechar", Gtk.ResponseType.CLOSE)
        rolagem = Gtk.ScrolledWindow()
        dialogo.get_content_area().pack_start(rolagem, True, True, 0)
        corpo = caixa(10)
        corpo.set_border_width(16)
        rolagem.add(corpo)
        corpo.pack_start(rotulo("Tamanho do texto", "secao"), False, False, 0)
        corpo.pack_start(rotulo("Aumente as fontes sem alterar resolução, escala de saída ou taxa de atualização.",
                                "detalhe"), False, False, 0)
        linha = Gtk.Box(spacing=8)
        for nome, dpi in PERFIS_TEXTO:
            botao = Gtk.Button(label=nome)
            botao.connect("clicked", lambda _, valor=dpi: self.operacao(
                ["xfconf-query", "-c", "xsettings", "-p", "/Xft/DPI", "-n", "-t", "int", "-s", str(valor)],
                "Ajustando tamanho do texto"))
            linha.pack_start(botao, False, False, 0)
        corpo.pack_start(linha, False, False, 0)
        tema = Gtk.Button(label="Aplicar tema danasOS para aplicativos GTK")
        tema.connect("clicked", lambda _: self.operacao(
            ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-n", "-t", "string", "-s", "danasOS"],
            "Aplicando tema danasOS"))
        corpo.pack_start(tema, False, False, 0)
        for titulo, modulos in MODULOS:
            corpo.pack_start(rotulo(titulo, "secao"), False, False, 0)
            for nome, candidatos in modulos:
                comando = next((c for c in candidatos if shutil.which(c[0])), None)
                if not comando:
                    continue
                botao = Gtk.Button(label=nome)
                botao.connect("clicked", lambda _, cmd=comando: self.abrir(cmd))
                corpo.pack_start(botao, False, False, 0)
        corpo.pack_start(rotulo("Gaming e diagnóstico", "secao"), False, False, 0)
        self.adicionar_energia(corpo)
        for nome, comando in (
            ("Diagnóstico de hardware, Secure Boot e jogos",
             ["xfce4-terminal", "--hold", "--execute", "/usr/bin/danasos-diagnostico"]),
            ("Atualizações do danasOS", None),
        ):
            botao = Gtk.Button(label=nome)
            if comando:
                botao.connect("clicked", lambda _, cmd=comando: self.abrir(cmd))
            else:
                botao.connect("clicked", self.atualizacoes)
            corpo.pack_start(botao, False, False, 0)
        dialogo.show_all()
        dialogo.run()
        dialogo.destroy()

    def adicionar_energia(self, corpo):
        try:
            perfis = subprocess.check_output(["powerprofilesctl", "list"], text=True,
                                             stderr=subprocess.DEVNULL, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return
        linha = Gtk.Box(spacing=8)
        for nome, perfil in PERFIS_ENERGIA:
            if f"{perfil}:" not in perfis:
                continue
            botao = Gtk.Button(label=nome)
            botao.connect("clicked", lambda _, valor=perfil: self.operacao(
                ["powerprofilesctl", "set", valor], "Ajustando perfil de energia"))
            linha.pack_start(botao, False, False, 0)
        corpo.pack_start(linha, False, False, 0)

    def atualizacoes(self, _):
        try:
            info = json.loads(STATUS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        ultima = info.get("ultima_verificacao")
        ultima = datetime.fromisoformat(ultima).astimezone().strftime("%d/%m/%Y %H:%M") if ultima else "Ainda não feita"
        ativo = Path("/etc/danasos/auto-update").is_file()
        nova = info.get("disponivel")
        pendente = f'{nova["versao"]} · {nova["tamanho"] / 1024:.0f} KiB' if nova else "Nenhuma detectada"
        texto = (
            f"Versão instalada: {self.versao()}\n"
            f"Automática: {'Ativada' if ativo else 'Desativada'}\n"
            f"Canal: {CANAL}\n"
            f"Última verificação: {ultima}\n"
            f"Assinatura: {info.get('assinatura', 'Ainda não verificada')}\n"
            f"Atualização disponível: {pendente}"
        )
        if nova and nova.get("mudancas"):
            texto += "\n" + nova["mudancas"]
        if info.get("erro"):
            texto += "\n\nÚltima falha: " + info["erro"]
        dialogo = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                                    buttons=Gtk.ButtonsType.NONE, text="Atualizações do danasOS")
        dialogo.format_secondary_text(texto)
        dialogo.add_button("Fechar", Gtk.ResponseType.CLOSE)
        dialogo.add_button("Mudanças da versão", 1)
        dialogo.add_button("Verificar", 2)
        dialogo.add_button("Desativar automática" if ativo else "Ativar automática", 3)
        if nova:
            dialogo.add_button("Instalar atualização", 4)
        if info.get("recuperacao") and info["recuperacao"]["versao"] != self.versao():
            dialogo.add_button("Recuperar versão anterior", 5)
        resposta = dialogo.run()
        dialogo.destroy()
        if resposta == 1:
            self.aviso("Mudanças da versão", (PASTA / "CHANGELOG.md").read_text(encoding="utf-8"),
                       Gtk.MessageType.INFO)
        elif resposta in {2, 3, 4, 5}:
            acao = {2: "verificar", 3: "desativar" if ativo else "ativar", 4: "instalar", 5: "rollback"}[resposta]
            if acao == "rollback":
                confirmar = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK_CANCEL,
                                              text="Voltar à versão anterior do danasOS?")
                confirmar.format_secondary_text("A atualização automática será desativada.")
                manter = confirmar.run() == Gtk.ResponseType.OK
                confirmar.destroy()
                if not manter:
                    return
            self.operacao(["pkexec", "/usr/bin/danasos-auto-update", acao], "Atualizações do danasOS")

    def abrir(self, comando):
        try:
            subprocess.Popen(comando)
        except OSError as erro:
            self.aviso("Não deu para abrir o aplicativo.", str(erro))


if __name__ == "__main__":
    janela = Central()
    janela.show_all()
    Gtk.main()
