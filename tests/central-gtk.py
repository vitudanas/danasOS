"""Testa a janela GTK e as ações do catálogo sem instalar jogos na CI."""

import subprocess
import unittest
from unittest.mock import patch

from central import Central, Gtk

STEAM = "com.valvesoftware.Steam"
HEROIC = "com.heroicgameslauncher.hgl"
LUTRIS = "net.lutris.Lutris"


class CentralGTK(unittest.TestCase):
    def setUp(self):
        self.app = Central()
        self.app.show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.addCleanup(self.app.destroy)

    def listar(self, sistema="", usuario="", lutris=False):
        with patch("central.subprocess.check_output", side_effect=[sistema, usuario]), patch(
            "central.shutil.which", side_effect=lambda cmd: "/usr/bin/lutris" if cmd == "lutris" and lutris else None
        ):
            self.app.refazer_catalogo()

    def test_catalogo_detecta_app_e_escolhe_a_instalacao(self):
        self.assertEqual(len(self.app.apps), 6)
        self.listar(sistema=STEAM, usuario=HEROIC, lutris=True)
        with patch.object(self.app, "abrir") as abrir, patch.object(self.app, "operacao") as operar:
            self.app.apps[STEAM]["principal"].clicked()
            abrir.assert_called_once_with(["flatpak", "--system", "run", STEAM])
            self.app.apps[LUTRIS]["principal"].clicked()
            self.assertEqual(abrir.call_args.args[0], ["lutris"])
            self.app.apps[HEROIC]["atualizar"].clicked()
            self.assertEqual(operar.call_args.args[0], ["flatpak", "--user", "update",
                                                       "--app", "--noninteractive", "-y", HEROIC])

    def test_detecta_instalacao_apos_atualizar_catalogo(self):
        self.listar()
        cartao = self.app.apps[STEAM]
        self.assertEqual(cartao["principal"].get_label(), "Instalar")
        self.listar(sistema=STEAM)
        self.assertEqual(cartao["principal"].get_label(), "Abrir")
        self.assertTrue(cartao["atualizar"].get_visible())

    def test_falha_de_consulta_nao_oferece_instalacao(self):
        with patch("central.subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "flatpak")), patch(
            "central.shutil.which", return_value=None
        ):
            self.app.refazer_catalogo()
        self.assertFalse(self.app.apps[STEAM]["principal"].get_sensitive())
        self.assertIn("Erro", self.app.catalogo_status.get_text())

    def test_tema_gtk_carrega(self):
        tema = Gtk.CssProvider()
        tema.load_from_path("config/includes.chroot/usr/share/themes/danasOS/gtk-3.0/gtk.css")


if __name__ == "__main__":
    unittest.main()
