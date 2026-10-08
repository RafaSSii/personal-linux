# linux-env

Portable Linux environment backup, synchronization and restore tool.

O objetivo é transformar um ambiente Linux em um manifesto declarativo que possa ser restaurado em outra instalação, sem tentar clonar o sistema operacional inteiro.

## v0.3.0 — Ubuntu + Apply

A primeira implementação específica para Ubuntu inclui:

- APT com pacotes explicitamente instalados via `apt-mark showmanual`;
- restauração APT com `apt-get update` + `apt-get install`;
- detecção de PPAs do Launchpad;
- Snap com canal e suporte a `--classic`;
- Flatpak com identificação do remote;
- backup dos dotfiles suportados;
- manifesto YAML schema 2;
- proteção contra restaurar um manifesto Ubuntu em uma distro diferente;
- `restore --dry-run` para revisar os comandos antes de executá-los.

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

Na máquina de destino:

```bash
linux-env restore ./meu-ubuntu --dry-run
linux-env restore ./meu-ubuntu
```

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

## O que é salvo no Ubuntu

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

- PPAs são capturados, mas fontes APT arbitrárias de terceiros ainda não são migradas automaticamente.
- Equivalência entre nomes de pacotes Ubuntu e outras distribuições ainda não é automática.
- O restore/apply Ubuntu exige que o destino também seja Ubuntu.
- O conjunto de dotfiles ainda é fixo; configuração personalizada será adicionada posteriormente.
- Chaves SSH/GPG, tokens, cookies e senhas não são copiados automaticamente.

## Próximos passos

- providers para GNOME e KDE;
- VS Code, Firefox, Steam e Docker;
- configuração declarativa de dotfiles;
- camada segura para secrets;
- sincronização via Git;
- testes em containers/VMs;
- TUI e GUI.

## Licença

MIT.
