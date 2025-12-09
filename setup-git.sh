#!/bin/bash

# Exit on any error
set -e

# Script para configurar o Git corretamente para este repositório
# This script configures Git to allow pulling from all branches

echo "Configurando Git para permitir pull de todos os branches..."
echo "Configuring Git to allow pulling from all branches..."

# Check if origin remote exists
if ! git remote | grep -q "^origin$"; then
    echo "Error: Remote 'origin' não existe / 'origin' remote does not exist"
    echo "Execute: git remote add origin https://github.com/dannysitouwu/tears"
    exit 1
fi

# Atualizar a configuração do remote para buscar todos os branches
# Update remote configuration to fetch all branches
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"

# Buscar todos os branches do repositório remoto
# Fetch all branches from remote repository
git fetch origin

echo ""
echo "✓ Configuração completa!"
echo "✓ Configuration complete!"
echo ""
echo "Branches disponíveis / Available branches:"
git branch -r
echo ""
echo "Agora você pode fazer pull de qualquer branch:"
echo "Now you can pull from any branch:"
echo "  git pull origin main"
echo "  git pull origin develop"
echo "  git pull"
