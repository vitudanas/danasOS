#!/bin/sh
# Quando o painel está ligado à iGPU, encaminha a imagem da NVIDIA para ele.
export LC_ALL=C
provedores=$(timeout 4 xrandr --listproviders) || exit 0
if printf '%s\n' "$provedores" | grep -Eq 'Source Output.*name:NVIDIA-0$' &&
   printf '%s\n' "$provedores" | grep -Eq 'Sink Output.*name:modesetting$'; then
    if timeout 4 xrandr --setprovideroutputsource modesetting NVIDIA-0; then
        timeout 4 xrandr --auto
    fi
fi
# Uma configuração de tela sem PRIME não deve impedir o LightDM de subir.
exit 0
