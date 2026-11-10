#!/usr/bin/env bash
set -euo pipefail
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
test "$(id -u)" = 0
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
chmod 0755 "$tmp"
export GNUPGHOME="$tmp/gnupg"
mkdir -m 0700 "$GNUPGHOME"
gpg --batch --passphrase '' --quick-generate-key 'danasOS CI' ed25519 sign 1d
fingerprint=$(gpg --batch --with-colons --list-keys | awk -F: '$1=="fpr" {print $10; exit}')
gpg --batch --armor --export "$fingerprint" > "$tmp/teste.asc"
cat > "$tmp/teste.sources" <<EOF
Types: deb
URIs: file:$tmp/apt/
Suites: ./
Signed-By: $tmp/teste.asc $fingerprint
EOF

mkdir "$tmp/baseline"
git -c safe.directory="$repo" -C "$repo" archive 54ef0ea publicar.py config/includes.chroot |
    tar -x -C "$tmp/baseline"
python3 "$tmp/baseline/publicar.py" --versao 0.2-2 --saida "$tmp/base"
apt-get -y --no-install-recommends install "$tmp/base/danasos-experience_0.2-2_all.deb"

cat > "$tmp/runner.py" <<'PY'
import importlib.machinery
import importlib.util
from pathlib import Path
import sys

arquivo, pasta = sys.argv[1:3]
loader = importlib.machinery.SourceFileLoader("updater", arquivo)
updater = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(updater)
pasta = Path(pasta)
updater.FONTE = pasta / "teste.sources"
updater.CHAVE = pasta / "teste.asc"
updater.ESTADO = pasta / "estado"
updater.STATUS = updater.ESTADO / "status.json"
updater.INDICES = updater.ESTADO / "lists"
updater.CACHE = updater.ESTADO / "pacotes"
updater.MARCADOR = pasta / "automatico"
# O runner não usa o serviço instalado para o teste de recuperação.
updater.rodar_original = updater.rodar
updater.rodar = lambda *args, **kw: (
    "" if args[:4] == ("systemctl", "disable", "--now", updater.TIMER)
    else updater.rodar_original(*args, **kw)
)
sys.argv = [arquivo, *sys.argv[3:]]
updater.main()
PY

up() {
    python3 "$tmp/runner.py" "$repo/config/includes.chroot/usr/bin/danasos-auto-update" "$tmp" "$@"
}
publicar() {
    if test -d "$tmp/apt"; then mv "$tmp/apt" "$tmp/apt-anterior-$1"; fi
    python3 "$repo/publicar.py" --versao "$1" --saida "$tmp/apt" --fingerprint "$fingerprint"
    mkdir -p "$tmp/publicacao"
    cp "$tmp/teste.asc" "$tmp/publicacao/danasos-publica.asc"
    cp -a "$tmp/apt" "$tmp/publicacao/apt"
    python3 "$repo/verificar-canal.py" "$tmp/publicacao" "$tmp/verificado-$1" "$fingerprint"
    mv "$tmp/publicacao/apt" "$tmp/pacote-inspecionado-$1"
}
versao() {
    test "$(dpkg-query -W -f='${Version}' danasos-experience)" = "$1"
}

publicar 0.4-1
up verificar
up instalar
versao 0.4-1
up instalar
versao 0.4-1

publicar 0.4-2
cp "$tmp/apt/danasos-experience_0.4-2_all.deb" "$tmp/copia.deb"
printf x | dd of="$tmp/apt/danasos-experience_0.4-2_all.deb" bs=1 seek=25 conv=notrunc status=none
if up instalar; then echo 'Aceitou arquivo corrompido.' >&2; exit 1; fi
versao 0.4-1
cp "$tmp/copia.deb" "$tmp/apt/danasos-experience_0.4-2_all.deb"
up instalar
versao 0.4-2

mv "$tmp/apt/InRelease" "$tmp/InRelease"
printf 'Assinatura inválida\n' > "$tmp/apt/InRelease"
if up verificar; then echo 'Aceitou assinatura inválida.' >&2; exit 1; fi
mv "$tmp/InRelease" "$tmp/apt/InRelease"
mv "$tmp/apt" "$tmp/offline"
if up verificar; then echo 'Aceitou repositório inacessível.' >&2; exit 1; fi
up rollback
versao 0.4-1
mv "$tmp/apt-anterior-0.4-2" "$tmp/apt"
up instalar
versao 0.4-1
echo 'Upgrade assinado, repetição, corrupção, assinatura inválida, offline e recuperação verificados.'
