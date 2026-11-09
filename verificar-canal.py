#!/usr/bin/env python3
"""Prepara o canal APT para o Pages depois de verificar assinatura e conteúdo."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

from publicar import CAMINHOS, PACOTE


def sha256(arquivo):
    with arquivo.open("rb") as fluxo:
        return hashlib.file_digest(fluxo, "sha256").hexdigest()


def verificar_assinatura(publicacao, fingerprint):
    chave = publicacao / "danasos-publica.asc"
    if chave.is_symlink() or not chave.read_bytes().startswith(b"-----BEGIN PGP PUBLIC KEY BLOCK-----"):
        raise ValueError("Forneça apenas a chave pública.")
    fingerprint = fingerprint.upper()
    if not re.fullmatch(r"(?:[A-F0-9]{40}|[A-F0-9]{64})", fingerprint):
        raise ValueError("Fingerprint público ausente ou inválido.")
    with tempfile.TemporaryDirectory(prefix="danasos-verificar-") as pasta:
        metadados = subprocess.check_output(
            ["gpg", "--homedir", pasta, "--batch", "--with-colons", "--show-keys", str(chave)],
            text=True,
        ).splitlines()
        if sum(linha.startswith("pub:") for linha in metadados) != 1:
            raise ValueError("O arquivo de chave precisa conter um único certificado.")
        fpr = next((linha.split(":")[9] for linha in metadados if linha.startswith("fpr:")), None)
        if fpr != fingerprint:
            raise ValueError("Fingerprint da chave pública não confere.")
        keyring = str(Path(pasta) / "publica.gpg")
        subprocess.run(["gpg", "--homedir", pasta, "--batch", "--dearmor", "--output", keyring,
                        str(chave)], check=True)
        assinado = subprocess.check_output(
            ["gpgv", "--homedir", pasta, "--keyring", keyring, "--output", "-",
             str(publicacao / "apt/InRelease")],
        )
    if assinado != (publicacao / "apt/Release").read_bytes():
        raise ValueError("Release diverge do texto assinado.")


def membros(arquivo, opcao, permitidos, diretorios):
    proc = subprocess.Popen(["dpkg-deb", opcao, str(arquivo)], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            lista = set()
            for item in tar:
                nome = PurePosixPath(item.name)
                if nome.is_absolute() or ".." in nome.parts:
                    raise ValueError("Caminho inseguro dentro do pacote.")
                if item.isdir():
                    if nome.parts and (not diretorios or
                                       not any(nome in PurePosixPath(p).parents for p in permitidos)):
                        raise ValueError("Diretório fora da lista de publicação.")
                    continue
                caminho = nome.as_posix()
                if not item.isfile() or caminho not in permitidos or caminho in lista:
                    raise ValueError("Arquivo fora da lista de publicação.")
                lista.add(caminho)
        if proc.wait():
            raise ValueError("O pacote não pôde ser lido.")
        return lista
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def verificar_pacote(arquivo):
    if membros(arquivo, "--fsys-tarfile", set(CAMINHOS), True) != set(CAMINHOS):
        raise ValueError("O pacote não contém exatamente os arquivos esperados.")
    controle = membros(arquivo, "--ctrl-tarfile", {"control", "md5sums"}, False)
    if "control" not in controle:
        raise ValueError("Pacote sem metadados de controle.")


def preparar(publicacao, destino, fingerprint):
    apt = publicacao / "apt"
    if publicacao.is_symlink() or apt.is_symlink():
        raise ValueError("Use pastas reais para publicar.")
    arquivos = list(apt.iterdir())
    pacotes = [p for p in arquivos if re.fullmatch(r"danasos-experience_\d+(?:\.\d+)+-\d+_all\.deb", p.name)]
    if (len(pacotes) != 1 or len(arquivos) != 4 or
            {p.name for p in arquivos} != {"Release", "InRelease", "Packages", pacotes[0].name} or
            any(p.is_symlink() or not p.is_file() for p in arquivos)):
        raise ValueError("O canal deve ter somente um .deb e seus três índices.")
    verificar_assinatura(publicacao, fingerprint)
    release = (apt / "Release").read_text(encoding="utf-8")
    sha256_section = re.search(r"(?m)^SHA256:\n((?:[ \t].*\n)+)", release)
    if not sha256_section:
        raise ValueError("Índice assinado sem SHA-256.")
    campos = [l.split() for l in sha256_section[1].splitlines()]
    indice = apt / "Packages"
    if [sha256(indice), str(indice.stat().st_size), "Packages"] not in campos:
        raise ValueError("Checksum de Packages incorreto.")
    controle = dict(l.split(": ", 1) for l in indice.read_text(encoding="utf-8").splitlines()
                    if re.match(r"^[A-Za-z0-9-]+: ", l))
    arquivo = pacotes[0]
    if (controle.get("Package") != PACOTE or
            controle.get("Filename") not in (arquivo.name, "./" + arquivo.name) or
            controle.get("SHA256") != sha256(arquivo) or
            controle.get("Size") != str(arquivo.stat().st_size)):
        raise ValueError("O pacote diverge do índice assinado.")
    verificar_pacote(arquivo)
    destino.mkdir(parents=True)
    for arquivo in arquivos:
        shutil.copyfile(arquivo, destino / arquivo.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publicacao", type=Path)
    parser.add_argument("destino", type=Path)
    parser.add_argument("fingerprint")
    args = parser.parse_args()
    try:
        preparar(args.publicacao, args.destino, args.fingerprint)
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError) as erro:
        parser.exit(1, f"Canal recusado. {erro}\n")
