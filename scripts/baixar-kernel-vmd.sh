#!/bin/sh
set -eu

saida=${1:?Informe a pasta de saída}
abi=7.3.3+deb14-amd64
repo=https://deb.debian.org/debian/pool/main/l
mkdir -p "$saida"

# SHA-256 dos índices amd64 autenticados pelos InRelease de sid e trixie-backports.
baixar() {
    curl --proto '=https' --proto-redir '=https' -fLsS --retry 3 "$repo/$1/$2" -o "$saida/$2"
    printf '%s  %s\n' "$3" "$saida/$2" | sha256sum -c -
}
baixar linux "linux-base-${abi}_7.3.3-1_amd64.deb" 8ea48e0c7aeb709c895c13699f09676de9a236183a17124572bc695d70b23cb1
baixar linux "linux-modules-${abi}_7.3.3-1_amd64.deb" 40073c12c078013c2127fe43e8510c1fa6c73b15fe2411fa18dff72dd84fead3
baixar linux-signed-amd64 "linux-binary-${abi}_7.3.3-1_amd64.deb" bf17f1f217b3af4195128febf01ca2fc0cdb0163bf4a7c64f6bf5d2d5362bb43
if [ "${2:-}" = --live ]; then
    baixar linux-signed-amd64 "linux-image-${abi}_7.3.3-1_amd64.deb" 5211308b72db8fea1bfdcf7a927cf79795d8789e66b8f609c1e29b3183d8e7bd
    baixar linux-base 'linux-base_4.17~bpo13+1_all.deb' 9c1a30ccf8d94672d8a89425fe419d954096718527155fd58974bd1a1043c55f
fi
