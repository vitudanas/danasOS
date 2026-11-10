#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
saida=$(realpath -m -- "${1:?Informe a pasta de saída}")
mkdir -p "$saida"
nome=danasOS-0.3-amd64-mint-hwe
test "$(id -u)" = 0
test ! -e "$saida/$nome.iso"
base=linuxmint-22.3-xfce-64bit-hwe-7.0.iso
tmp=$(mktemp -d)
base_dir=${2:-$tmp}
raiz="$tmp/root"
midia="$tmp/iso"
montagens=()
limpar() {
    local i
    for ((i=${#montagens[@]}-1; i>=0; i--)); do
        umount "${montagens[i]}" || return
    done
    rm -rf -- "$tmp"
}
trap limpar EXIT
bash "$repo/scripts/baixar-mint.sh" "$base_dir"
xorriso -osirrox on -indev "$base_dir/$base" -extract / "$midia"
chmod -R u+rwX "$midia"
unsquashfs -no-progress -d "$raiz" "$midia/casper/filesystem.squashfs"
rm -- "$midia/casper/filesystem.squashfs"
chroot "$raiz" grep -qx 'ID=linuxmint' /etc/os-release
chroot "$raiz" grep -qx 'UBUNTU_CODENAME=noble' /etc/os-release

overlay="$repo/config/includes.chroot"
mkdir -p "$raiz/etc/danasos" "$raiz/etc/X11/xorg.conf.d" "$raiz/etc/lightdm/lightdm-gtk-greeter.conf.d"
touch "$raiz/etc/danasos/base-mint"
release="$raiz$(chroot "$raiz" realpath /etc/os-release)"
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="danasOS 0.3 (Linux Mint 22.3 Xfce)"/' "$release"
for app in danasos-visual danasos-diagnostico danasos-canal-github; do
    install -m 0755 "$overlay/usr/local/bin/$app" "$raiz/usr/local/bin/$app"
done
install -m 0644 "$overlay/etc/xdg/autostart/danasos-visual.desktop" "$raiz/etc/xdg/autostart/"
install -m 0644 "$overlay/etc/lightdm/lightdm-gtk-greeter.conf.d/90-danasos.conf" \
    "$raiz/etc/lightdm/lightdm-gtk-greeter.conf.d/"
python3 "$repo/publicar.py" --versao 0.2-2 --saida "$tmp"
install -m 0644 "$tmp/danasos-experience_0.2-2_all.deb" "$raiz/tmp/"

cat > "$raiz/etc/X11/xorg.conf.d/90-danasos-nvidia.conf" <<'XORG'
Section "OutputClass"
    Identifier "danasOS NVIDIA"
    MatchDriver "nvidia-drm"
    Option "PrimaryGPU" "yes"
EndSection
XORG
cat > "$raiz/etc/default/keyboard" <<'KBD'
XKBMODEL="abnt2"
XKBLAYOUT="br"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
KBD
printf '%s\n' vmd nvme nvme_core >> "$raiz/etc/initramfs-tools/modules"

for ponto in dev proc sys; do
    mount --bind "/$ponto" "$raiz/$ponto"
    montagens+=("$raiz/$ponto")
done
cp -a -- "$raiz/etc/resolv.conf" "$tmp/resolv.conf"
rm -- "$raiz/etc/resolv.conf"
cp -L /etc/resolv.conf "$raiz/etc/resolv.conf"
if test -e "$raiz/usr/sbin/policy-rc.d"; then
    mv "$raiz/usr/sbin/policy-rc.d" "$tmp/policy-rc.d"
fi
printf '#!/bin/sh\nexit 101\n' > "$raiz/usr/sbin/policy-rc.d"
chmod 0755 "$raiz/usr/sbin/policy-rc.d"
no_mint() { chroot "$raiz" env DEBIAN_FRONTEND=noninteractive LC_ALL=C "$@"; }
apt_mint() { no_mint apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=2 "$@"; }

echo 'Instalando kernel Ubuntu 7.3 assinado com o suporte VMD Arrow Lake'
# Evita as transferências lentas de firmware pelo endpoint HTTP da imagem base.
sed -i \
    -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
    -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' \
    "$raiz/etc/apt/sources.list.d/official-package-repositories.list"
# O Ubuntu HWE 7.0 rejeita o offset 3 do Acer. Limita a origem mais nova
# aos pacotes de kernel deste teste e usa o restante do Mint/Noble.
abi=7.3.0-10-generic
driver=615
cat > "$raiz/etc/apt/sources.list.d/danasos-kernel-teste.list" <<'APT'
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu stonking main restricted
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu stonking-updates main restricted
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://security.ubuntu.com/ubuntu stonking-security main restricted
APT
cat > "$raiz/etc/apt/preferences.d/danasos-kernel-teste" <<APT
Package: linux-image-$abi linux-modules-$abi linux-main-modules-v4l2loopback-$abi linux-main-modules-zfs-$abi linux-modules-nvidia-$driver-open-$abi
Pin: release n=stonking
Pin-Priority: 500

Package: *
Pin: release n=stonking
Pin-Priority: -1
APT
apt_mint -o APT::Update::Error-Mode=any update
apt_mint install -y --no-install-recommends \
    "linux-image-$abi" "linux-modules-nvidia-$driver-open-$abi" \
    "libnvidia-gl-$driver" "nvidia-utils-$driver" "xserver-xorg-video-nvidia-$driver" \
    /tmp/danasos-experience_0.2-2_all.deb gnome-software-plugin-flatpak \
    papirus-icon-theme gamemode vulkan-tools mokutil
rm -- "$raiz/etc/apt/sources.list.d/danasos-kernel-teste.list" "$raiz/etc/apt/preferences.d/danasos-kernel-teste"
test -s "$raiz/boot/vmlinuz-$abi"
for modulo in nvidia nvidia_modeset nvidia_drm nvidia_uvm; do
    assinante=$(no_mint modinfo -k "$abi" -F signer "$modulo")
    test -n "$assinante"
    printf '%s %s: %s\n' "$abi" "$modulo" "$assinante"
done
nvidia=$(no_mint modinfo -k "$abi" -F version nvidia)
test "${nvidia%%.*}" = "$driver"
test "$(no_mint dpkg-query -W -f='${Version}' "nvidia-utils-$driver" | cut -d- -f1)" = "$nvidia"
if no_mint dpkg-query -W -f='${db:Status-Status}' "nvidia-dkms-$driver-open" 2>/dev/null | grep -qx installed; then
    echo 'A instalação puxou DKMS em vez de usar apenas os módulos assinados.' >&2
    exit 1
fi
for antigo in "$raiz"/boot/vmlinuz-*; do
    antigo=${antigo##*/vmlinuz-}
    if [[ "$antigo" != "$abi" && "$antigo" =~ ^[0-9.]+-[0-9]+-generic$ ]]; then
        mapfile -t pacotes < <(no_mint dpkg-query -W -f='${binary:Package}\n' "linux-*-${antigo%-generic}*" || true)
        if (("${#pacotes[@]}")); then apt_mint purge -y "${pacotes[@]}"; fi
    fi
done
no_mint flatpak --system remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
for aplicativo in org.gnome.Software gnome-software-service mintwelcome; do
    entrada="/etc/xdg/autostart/$aplicativo.desktop"
    if test -f "$raiz$entrada"; then
        no_mint dpkg-divert --local --rename --add "$entrada"
    fi
done
no_mint localedef -i pt_BR -f UTF-8 pt_BR.UTF-8
no_mint setupcon --save-only
no_mint update-initramfs -u -k "$abi"
lsinitramfs "$raiz/boot/initrd.img-$abi" > "$tmp/initrd-files"
for modulo in vmd nvme nvme-core; do
    grep -E "/${modulo}\.ko(\.(zst|xz|gz))?$" "$tmp/initrd-files"
done
sbverify --list "$raiz/boot/vmlinuz-$abi"

sed '/^ConditionVirtualization=/a ConditionKernelCommandLine=boot=casper' \
    "$repo/scripts/danasos-verificar-vm.service" > "$raiz/etc/systemd/system/danasos-verificar-vm.service"
mkdir -p "$raiz/etc/systemd/system/graphical.target.wants"
ln -s ../danasos-verificar-vm.service "$raiz/etc/systemd/system/graphical.target.wants/"
no_mint apt-get clean
find "$raiz/var/lib/apt/lists" -maxdepth 1 -type f -delete
rm -- "$raiz/tmp/danasos-experience_0.2-2_all.deb" "$raiz/usr/sbin/policy-rc.d" "$raiz/etc/resolv.conf"
mv "$tmp/resolv.conf" "$raiz/etc/resolv.conf"
if test -e "$tmp/policy-rc.d"; then mv "$tmp/policy-rc.d" "$raiz/usr/sbin/policy-rc.d"; fi
for ((i=${#montagens[@]}-1; i>=0; i--)); do umount "${montagens[i]}"; done
montagens=()

echo 'Empacotando a sessão Live do danasOS'
cp "$raiz/boot/vmlinuz-$abi" "$midia/casper/vmlinuz"
cp "$raiz/boot/initrd.img-$abi" "$midia/casper/initrd.lz"
no_mint dpkg-query -W -f='${db:Status-Abbrev}\t${binary:Package}\t${Version}\n' | \
    awk '$1 == "ii" {print $2 "\t" $3}' > "$midia/casper/filesystem.manifest"
du -sx --block-size=1 "$raiz" | cut -f1 > "$midia/casper/filesystem.size"
compactar() {
    mksquashfs "$raiz" "$midia/casper/filesystem.squashfs" -noappend \
        -b 1M -no-progress -processors 4 "$@"
}
compactar -comp zstd -Xcompression-level 15
if (("$(du -sb "$midia" | cut -f1)" > 4250000000)); then
    echo 'Recompactando em XZ para o DANASLIVE de 4 GiB'
    compactar -comp xz
fi
test "$(du -sb "$midia" | cut -f1)" -le 4250000000
python3 "$repo/scripts/midia-mint.py" "$midia"
mapear=()
for arquivo in casper/vmlinuz casper/initrd.lz casper/filesystem.squashfs \
    casper/filesystem.manifest casper/filesystem.size boot/grub/grub.cfg \
    isolinux/txt.cfg md5sum.txt; do
    if test -f "$midia/$arquivo"; then
        mapear+=(-map "$midia/$arquivo" "/$arquivo")
    fi
done
xorriso -indev "$base_dir/$base" -outdev "$saida/$nome.iso" -boot_image any replay "${mapear[@]}"
chmod 0644 "$saida/$nome.iso"
(cd "$saida" && sha256sum "$nome.iso" > "$nome.sha256")
printf 'Kernel=%s\nNVIDIA=%s\nVMD_Acer=validacao_fisica_pendente\n' \
    "$abi" "$nvidia" > "$saida/$nome.info"
