# linux-env

Portable Linux environment backup, synchronization and restore tool.

Transforma um ambiente Linux em um manifesto declarativo que pode ser restaurado em outra instalação.

## MVP 0.1.0

- detecção de distro, versão, arquitetura, desktop e gerenciadores;
- exportação de pacotes para apt, dnf, pacman e zypper;
- exportação de aplicativos Flatpak;
- backup de alguns dotfiles;
- manifesto YAML;
- restauração com --dry-run;
- arquitetura baseada em providers.

A primeira versão ainda não resolve automaticamente equivalência de nomes de pacotes entre distribuições.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso

```bash
linux-env detect
linux-env save ./meu-ambiente
linux-env restore ./meu-ambiente --dry-run
linux-env restore ./meu-ambiente
```

## Roadmap

- equivalência de pacotes entre distros;
- diff e apply;
- providers para GNOME, KDE, VS Code, Firefox, Steam e Docker;
- camada segura para secrets;
- sincronização via Git;
- testes em containers/VMs;
- TUI e GUI.

## Segurança

O MVP não copia automaticamente chaves SSH/GPG, tokens, cookies ou senhas.

## Licença

MIT.
