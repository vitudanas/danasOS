# Mudanças do danasOS

## 0.4-1 — pacote de experiência

**Implementado**

- **A:** fonte oficial com fingerprint fixado, verificação APT, versão e estado na Central, tamanho do download, changelog, instalação manual e timer diário. O updater limita a operação ao próprio pacote.
- **A:** arquivo anterior autenticado em cache para recuperação quando disponível. Assinatura ou integridade inválida interrompe a instalação. Há trava entre operações do updater.
- **A:** configurações agrupadas, acesso ao módulo de aplicativos padrão do Xfce, comandos de diagnóstico e perfis de energia anunciados pelo sistema.
- **A:** catálogo por finalidade, ferramentas avançadas agrupadas, detecção de Flatpaks de usuário e sistema e de launchers nativos conhecidos, atualização por app, saída de progresso do Flatpak e cancelamento.
- **A/B:** presets de DPI para fontes e ação de aplicar o tema GTK3. Alguns aplicativos carregam tema e DPI na próxima abertura ou sessão. Consultar [Noite em Neon](DESIGN.md).
- **D para mídia nova:** a receita da ISO passa a instalar a mesma versão do pacote que chega à instalação existente.

**Corrigido**

- O cadastro legado verifica os mesmos bytes da chave que instala.
- O fluxo oficial deixa de depender do cadastro manual da URL na instalação que já recebeu o pacote 0.4-1.
- Os cartões consultam novamente a instalação depois de alterações e distinguem falha de consulta de aplicativo ausente.

**Já existia e foi validado**

- O boot da ISO Mint anterior com Secure Boot, NVMe em FAT32, Xfce e ABNT2 foi validado em QEMU. O usuário confirmou o uso normal dessa base no Acer.
- O pacote preserva o kernel assinado, o driver, os dados, os launchers existentes e as configurações de boot. As melhorias de desktop e updater são instaláveis sem nova ISO.

**Parcial**

- O módulo Xfce controla resolução, monitores, escala e Hz. A Central oferece ajuste de fonte independente. A combinação com 240 Hz e DPI misto continua sem validação no Acer.
- O progresso de launchers é a saída real do Flatpak. Dependendo da versão e da origem, o CLI pode oferecer somente eventos por etapa.
- O tema cobre GTK3, incluindo a Central, além da configuração LightDM existente na imagem. Aplicativos Qt, GTK4/libadwaita, Flatpaks e decorações do Xfwm podem manter sua aparência.

**Não implementado**

- Troca automática de modo Intel/NVIDIA, tema próprio de Xfwm/cursores/Qt e gestão integrada de runtimes de terceiros. A receita não impõe sysctl, zram, governor, latência PipeWire ou parâmetros de rede.
- A versão do kernel experimental continua uma decisão de base (**C**). Atualizá-la requer validação de VMD e NVIDIA na mesma ABI antes de oferecer a troca.

**Precisa de teste no hardware**

- Tela interna a 240 Hz, monitor externo, reversão do modo, primário, suspensão, VRR e modo híbrido. Verificar assinatura NVIDIA carregada, Vulkan/OpenGL/VA-API, controles, autonomia, RAM ociosa e 1% lows com cenários reproduzíveis.
