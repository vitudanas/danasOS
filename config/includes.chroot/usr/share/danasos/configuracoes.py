"""Módulos nativos oferecidos pelo hub de configurações."""

MODULOS = (
    ("Tela e acessibilidade", (
        ("Monitores, resolução, escala e Hz", (("xfce4-display-settings",),)),
        ("Fontes, DPI, ícones e tema", (("xfce4-appearance-settings",),)),
        ("Tema das janelas", (("xfwm4-settings",),)),
        ("Wallpaper", (("xfdesktop-settings",),)),
        ("Painel", (("xfce4-panel", "--preferences"),)),
        ("Notificações", (("xfce4-notifyd-config",),)),
    )),
    ("Conexões e dispositivos", (
        ("Wi-Fi e rede", (("nm-connection-editor",),)),
        ("Bluetooth e controles", (("blueman-manager",),)),
        ("Áudio, microfone e saídas", (("pavucontrol",),)),
        ("Mouse e touchpad", (("xfce4-mouse-settings",),)),
        ("Teclado", (("xfce4-keyboard-settings",),)),
    )),
    ("Sistema", (
        ("Energia, bateria e suspensão", (("xfce4-power-manager-settings",),)),
        ("Aplicativos padrão e associações MIME", (("xfce4-mime-settings",), ("exo-preferred-applications",))),
        ("Sessão e inicialização automática", (("xfce4-session-settings",),)),
        ("Armazenamento", (("baobab",), ("thunar", "/media"))),
        ("Drivers", (("driver-manager",), ("mintdrivers",))),
        ("GPU NVIDIA", (("nvidia-settings",),)),
    )),
)

PERFIS_TEXTO = (("Padrão do Xfce", -1), ("100% · 96 DPI", 96), ("125% · 120 DPI", 120),
                ("150% · 144 DPI", 144), ("175% · 168 DPI", 168))
PERFIS_ENERGIA = (("Equilibrado", "balanced"), ("Bateria", "power-saver"),
                  ("Máximo desempenho", "performance"))

APPS_NATIVOS = {
    "com.valvesoftware.Steam": ("steam",),
    "com.heroicgameslauncher.hgl": ("heroic",),
    "net.lutris.Lutris": ("lutris",),
    "com.usebottles.bottles": ("bottles",),
    "org.prismlauncher.PrismLauncher": ("prismlauncher",),
    "io.github.Faugus.faugus-launcher": ("faugus-launcher",),
}
