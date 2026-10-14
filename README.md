# linux-env

Portable Linux environment backup, synchronization and restore tool.

O objetivo é transformar um ambiente Linux em um manifesto declarativo que possa ser restaurado em outra instalação, sem tentar clonar o sistema operacional inteiro.

## Compatibilidade atual: Ubuntu, Linux Mint e Manjaro

A implementação atual cobre Ubuntu, Linux Mint baseado em Ubuntu (não LMDE) e Manjaro, incluindo:

- APT com pacotes explicitamente instalados via `apt-mark showmanual`;
- Pacman no Manjaro com pacotes explicitamente instalados via `pacman -Qqe`;
- KDE Plasma e GNOME como sessões de desktop detectadas; manifestos podem ser restaurados entre as edições Manjaro KDE e GNOME;
- restauração APT com `apt-get update` + `apt-get install`;
- detecção de PPAs do Launchpad;
- Snap com canal e suporte a `--classic`;
- Flatpak com identificação do remote;
- backup dos dotfiles suportados;
- manifesto YAML schema 2;
- validação de compatibilidade: Ubuntu e Linux Mint baseado em Ubuntu podem trocar manifestos; distros não compatíveis são bloqueadas;
- `restore --dry-run` para revisar os comandos antes de executá-los;
- instalação apenas dos pacotes portáveis que ainda não estão instalados;
- exclusão automática de pacotes de boot/kernel, hardware e específicos do Manjaro;
- resumo por categoria e proteção de dotfiles existentes com backup antes de substituição.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso

Na máquina de origem:

```bash
linux-env detect
linux-env save ./meu-ubuntu
```

Na máquina de destino, revise primeiro o plano:

```bash
linux-env restore ./meu-ubuntu --dry-run
```

O plano informa quantos pacotes serão instalados, quantos já existem e quais foram ignorados por segurança. Quando estiver pronto:

```bash
linux-env restore ./meu-ubuntu
```

Se houver dotfiles que já existem, o programa pede confirmação e salva cópias em `~/.local/share/linux-env/restore-backups/` antes de substituí-los. Use `--yes` para dispensar essa confirmação; o backup continua sendo criado.

## Diff

Compare o estado atual com um manifesto salvo:

```bash
linux-env diff ./meu-ubuntu
```

O comando verifica APT, Snap, Flatpak, PPAs e dotfiles. Para arquivos de configuração, compara o conteúdo usando SHA-256 e marca arquivos modificados com `~`.

## Apply

O `apply` transforma o manifesto em estado desejado e tenta reconciliar a máquina atual com ele:

```bash
linux-env apply ./meu-ubuntu --dry-run
linux-env apply ./meu-ubuntu
linux-env apply ./meu-ubuntu --yes
```

Por segurança, o primeiro comando apenas exibe o plano. Sem `--dry-run`, o CLI executa instalações normalmente, mas pede confirmação antes de operações destrutivas, como:

- remover pacotes APT;
- remover Snaps;
- remover Flatpaks;
- remover PPAs;
- sobrescrever dotfiles modificados.

`--yes` pula somente essa confirmação. Ele não altera o conteúdo do manifesto nem ignora a validação de distro.

## O que é salvo no Ubuntu, Linux Mint e Manjaro

### APT

São salvos os pacotes marcados como instalação manual. Dependências instaladas automaticamente não entram no manifesto.

PPAs ativos do Launchpad são detectados nos arquivos de fontes do APT.

### Snap

Aplicativos Snap são salvos com canal e indicação de `classic` quando aplicável. Snaps de infraestrutura como `core`, `core20`, `core22`, `core24` e `snapd` são ignorados.

### Flatpak

São salvos o ID do aplicativo e o remote de origem. Manifestos antigos que continham apenas IDs continuam sendo aceitos.

### Dotfiles

A versão atual faz backup de:

- `.bashrc`
- `.zshrc`
- `.gitconfig`
- `.config/nvim/init.lua`

## Limitações atuais

- O Linux Mint normalmente não vem com Snap habilitado. Se o manifesto contém Snaps, instale/habilite `snapd` no Mint antes de restaurar esses aplicativos; o `linux-env` não altera essa política automaticamente.

- PPAs são capturados, mas fontes APT arbitrárias de terceiros ainda não são migradas automaticamente.
- Equivalência entre nomes de pacotes APT e Pacman ainda não é automática; não é seguro restaurar um manifesto Ubuntu diretamente no Manjaro ou vice-versa.
- A troca de manifestos entre Ubuntu e Linux Mint só é aceita quando o Mint é baseado em Ubuntu; LMDE não é tratado como equivalente.
- KDE e GNOME são detectados, mas a exportação/restauração de todas as preferências específicas dos desktops ainda será implementada; o backup atual cobre apenas os dotfiles explicitamente permitidos.
- Chaves SSH/GPG, tokens, cookies e senhas não são copiados automaticamente.

## Próximos passos

- backup e restauração das preferências específicas do GNOME (dconf) e KDE Plasma;
- VS Code, Firefox, Steam e Docker;
- configuração declarativa de dotfiles;
- camada segura para secrets;
- sincronização via Git;
- testes em containers/VMs;
- TUI e GUI.

## Licença

MIT.
