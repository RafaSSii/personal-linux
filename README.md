# linux-env

Portable Linux environment backup, synchronization and restore tool.

O objetivo é transformar um ambiente Linux em um manifesto declarativo que possa ser restaurado em outra instalação, sem tentar clonar o sistema operacional inteiro.

## v0.2.0 — Ubuntu

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

### Exemplo de manifesto

```yaml
schema: 2
system:
  distro: ubuntu
  version: "24.04"
  architecture: amd64

packages:
  apt:
    - curl
    - git
    - neovim
    - python3
    - build-essential

snap:
  - name: code
    channel: latest/stable
    classic: true

flatpaks:
  - app_id: org.mozilla.firefox
    remote: flathub

repositories:
  apt_ppas:
    - ppa:example/tool

dotfiles:
  - .bashrc
  - .gitconfig
```

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

Isso cria:

```text
meu-ubuntu/
├── manifest.yaml
└── dotfiles/
```

Na máquina de destino:

```bash
linux-env restore ./meu-ubuntu --dry-run
linux-env restore ./meu-ubuntu
```

O `--dry-run` apenas mostra os comandos. Sem ele, os comandos são executados.

## O que é salvo no Ubuntu

### APT

São salvos os pacotes marcados como instalação manual. Dependências instaladas automaticamente não entram no manifesto, deixando o backup mais limpo e portátil.

PPAs ativos do Launchpad são detectados quando aparecem nos arquivos de fontes do APT.

### Snap

Aplicativos Snap são salvos com o canal quando disponível e com a indicação de `classic` quando aplicável. Snaps de infraestrutura como `core`, `core20`, `core22`, `core24` e `snapd` são ignorados porque normalmente são gerenciados pelo próprio Snap.

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
- O restore Ubuntu exige que o destino também seja Ubuntu.
- O conjunto de dotfiles ainda é fixo; configuração personalizada será adicionada posteriormente.
- Chaves SSH/GPG, tokens, cookies e senhas não são copiados automaticamente.

## Próximos passos

- diff e apply;
- providers para GNOME e KDE;
- VS Code, Firefox, Steam e Docker;
- configuração declarativa de dotfiles;
- camada segura para secrets;
- sincronização via Git;
- testes em containers/VMs;
- TUI e GUI.

## Licença

MIT.
