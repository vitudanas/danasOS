import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build import conferir_boot


class TestBoot(unittest.TestCase):
    abi = "6.12.117+deb13-amd64"

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.trabalho = Path(pasta.name)
        boot = self.trabalho / "chroot/boot"
        boot.mkdir(parents=True)
        (boot / f"vmlinuz-{self.abi}").touch()
        self.iso = self.trabalho / "danasos.iso"

    def listar_modulos(self, abi=None):
        abi = abi or self.abi
        return "\n".join((
            f"usr/lib/modules/{abi}/kernel/drivers/pci/controller/vmd.ko.xz",
            f"usr/lib/modules/{abi}/kernel/drivers/nvme/host/nvme.ko",
            f"lib/modules/{abi}/kernel/drivers/nvme/host/nvme-core.ko.zst",
        ))

    @patch("build.subprocess.run")
    @patch("build.subprocess.check_output")
    def test_confere_arquivos_extraidos_da_iso(self, saida, rodar):
        saida.side_effect = ["UEFI", self.listar_modulos()]
        conferir_boot(self.trabalho, self.iso)
        self.assertIn(f"/live/vmlinuz-{self.abi}", rodar.call_args_list[0].args[0])
        self.assertIn(f"/live/initrd.img-{self.abi}", rodar.call_args_list[0].args[0])
        self.assertEqual(rodar.call_args_list[1].args[0][:2], ["sbverify", "--list"])

    @patch("build.subprocess.run")
    @patch("build.subprocess.check_output")
    def test_rejeita_initramfs_sem_nvme_core(self, saida, _rodar):
        saida.side_effect = ["UEFI", "\n".join(self.listar_modulos().splitlines()[:2])]
        with self.assertRaisesRegex(RuntimeError, "Módulos ausentes.*nvme-core"):
            conferir_boot(self.trabalho, self.iso)

    @patch("build.subprocess.run")
    @patch("build.subprocess.check_output")
    def test_rejeita_initramfs_de_outra_abi(self, saida, _rodar):
        saida.side_effect = ["UEFI", self.listar_modulos("6.12.116+deb13-amd64")]
        with self.assertRaisesRegex(RuntimeError, "Módulos ausentes.*vmd"):
            conferir_boot(self.trabalho, self.iso)

    @patch("build.subprocess.run")
    @patch("build.subprocess.check_output", return_value="UEFI")
    def test_interrompe_se_sbverify_falhar(self, saida, rodar):
        rodar.side_effect = [None, subprocess.CalledProcessError(1, "sbverify")]
        with self.assertRaises(subprocess.CalledProcessError):
            conferir_boot(self.trabalho, self.iso)
        saida.assert_called_once()
