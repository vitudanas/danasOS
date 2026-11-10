#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

destino=$(realpath -m -- "${1:?Informe a pasta da ISO base}")
mkdir -p "$destino"
base=linuxmint-22.3-xfce-64bit-hwe-7.0.iso
origem=https://pub.linuxmint.io/hwe
espelho=https://mirror.cpsc.ucalgary.ca/mirror/linuxmint.com/releases/hwe
chave=27DEB15644C6B3CF3BD7D291300F846BA25BAE09
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

baixar() {
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 20 --max-time 60 --retry 2 --output "$2" "$1"
}
baixar "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$chave" "$tmp/mint.asc"
mkdir -m 700 "$tmp/gnupg"
gpg --homedir "$tmp/gnupg" --batch --import "$tmp/mint.asc"
gpg --homedir "$tmp/gnupg" --batch --export "$chave" > "$tmp/mint.gpg"
test -s "$tmp/mint.gpg"
for arquivo in sha256sum.txt sha256sum.txt.gpg; do
    baixar "$origem/$arquivo" "$tmp/$arquivo"
done
gpgv --keyring "$tmp/mint.gpg" "$tmp/sha256sum.txt.gpg" "$tmp/sha256sum.txt"
awk -v nome="*$base" '$2 == nome {print; n++} END {exit n != 1}' \
    "$tmp/sha256sum.txt" > "$tmp/iso.sha256"

cd "$destino"
if ! sha256sum --status -c "$tmp/iso.sha256"; then
    aria2c --no-conf --check-certificate=true --continue=true --allow-overwrite=true \
        --auto-file-renaming=false --file-allocation=none --max-connection-per-server=8 \
        --split=12 --min-split-size=16M --connect-timeout=20 --timeout=40 \
        --max-tries=5 --summary-interval=30 --checksum="sha-256=$(cut -d' ' -f1 "$tmp/iso.sha256")" \
        --out="$base" "$origem/$base" "$espelho/$base"
fi
sha256sum -c "$tmp/iso.sha256"
