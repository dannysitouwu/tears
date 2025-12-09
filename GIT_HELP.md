# Guia de Git - Solução para Problemas de Pull

## Problema Resolvido

O problema era que a configuração do Git estava limitada a apenas um branch, impedindo que você fizesse pull de outros branches do repositório.

### O que foi corrigido:

A configuração do remote foi atualizada de:
```
+refs/heads/copilot/help-with-pull-request:refs/remotes/origin/copilot/help-with-pull-request
```

Para:
```
+refs/heads/*:refs/remotes/origin/*
```

Isso permite que você faça fetch e pull de todos os branches do repositório.

## Como usar Git Pull agora

### Atualizar o branch atual:
```bash
git pull
```

### Fazer pull de um branch específico:
```bash
git pull origin main
git pull origin develop
```

### Ver todos os branches disponíveis:
```bash
# Branches locais
git branch

# Branches remotos
git branch -r

# Todos os branches
git branch -a
```

### Trocar de branch:
```bash
git checkout main
git checkout develop
```

### Criar um novo branch baseado em outro:
```bash
git checkout -b meu-novo-branch origin/main
```

## Branches Disponíveis no Repositório

- **main** - Branch principal
- **develop** - Branch de desenvolvimento
- **feature/test-protection** - Branch de funcionalidade
- **copilot/help-with-pull-request** - Branch atual de trabalho

## Comandos Úteis

### Atualizar referências do repositório remoto:
```bash
git fetch origin
```

### Ver o status do repositório:
```bash
git status
```

### Ver o histórico de commits:
```bash
git log --oneline
```

### Ver diferenças entre branches:
```bash
git diff main..develop
```

## Resolução de Conflitos

Se você encontrar conflitos ao fazer pull:

1. O Git irá informar quais arquivos têm conflitos
2. Abra os arquivos e resolva os conflitos manualmente
3. Depois de resolver:
```bash
git add .
git commit -m "Resolvido conflitos de merge"
```

## Mantendo seu branch atualizado

Para manter seu branch atualizado com o main:
```bash
git checkout seu-branch
git pull origin main
```

Ou usando rebase (para um histórico mais limpo):
```bash
git checkout seu-branch
git rebase origin/main
```
