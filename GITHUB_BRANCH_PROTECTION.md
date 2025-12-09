# GitHub Branch Protection Rules - Guia Visual

## Como Adicionar Regras de Proteção de Branch

### Passo 1: Acessar Settings
1. No seu repositório `dannysitouwu/tears` no GitHub
2. Clique na aba **Settings** (ícone de engrenagem, última aba no menu superior)

### Passo 2: Navegar para Branches
1. No menu lateral esquerdo, em **Code and automation**, clique em **Branches**
2. Você verá a seção "Branch protection rules"

### Passo 3: Adicionar Regra
1. Clique no botão **Add branch protection rule** (ou **Add classic branch protection rule**)
2. No campo **Branch name pattern**, digite: `main`

### Passo 4: Configurar Proteções para `main`
Marque as seguintes opções:

#### ✅ Require a pull request before merging
- ✅ **Require approvals**: 1 (mínimo de 1 aprovação)
- ✅ **Dismiss stale pull request approvals when new commits are pushed**
- ✅ **Require review from Code Owners** (opcional)

#### ✅ Require status checks to pass before merging
- ✅ **Require branches to be up to date before merging**
- Na caixa de busca "Search for status checks", adicione:
  - `backend-tests` (do workflow backend-ci.yml)
  - `frontend-tests` (do workflow frontend-ci.yml)
  - `build` (do workflow backend-ci.yml)

#### ✅ Require conversation resolution before merging
- Força resolver todos os comentários antes de merge

#### ✅ Do not allow bypassing the above settings
- Nem administradores podem ignorar as regras

#### ❌ NÃO marque "Require linear history" 
- Pode causar problemas com merges

### Passo 5: Salvar
1. Role até o final da página
2. Clique em **Create** (ou **Save changes**)

### Passo 6: Repetir para `develop`
1. Clique novamente em **Add branch protection rule**
2. No **Branch name pattern**, digite: `develop`
3. Configure as MESMAS opções que configurou para `main`
4. Clique em **Create**

---

## Como Verificar se Está Funcionando

### Teste 1: Tentar Push Direto (deve falhar)
```bash
git checkout main
echo "test" >> README.md
git add README.md
git commit -m "test direct push"
git push
# ❌ Deve retornar erro: "protected branch hook declined"
```

### Teste 2: Criar PR (deve funcionar)
```bash
git checkout -b feature/test-protection
echo "test" >> README.md
git add README.md
git commit -m "test via PR"
git push -u origin feature/test-protection
# ✅ Depois crie PR no GitHub UI
```

---

## Configuração dos GitHub Secrets (para CI/CD)

Para que os workflows de **CD** (deployment) funcionem, configure os secrets:

### 📍 ONDE ENCONTRAR: Passo a Passo Visual

#### 1️⃣ No seu repositório GitHub
```
https://github.com/dannysitouwu/tears
```

#### 2️⃣ Clique na aba "Settings" ⚙️
- É a ÚLTIMA aba no menu horizontal superior
- Ícone de engrenagem
- **IMPORTANTE**: Você precisa ser owner/admin do repositório

#### 3️⃣ No menu lateral ESQUERDO
```
Settings
  └─ Security (seção)
      └─ Secrets and variables  ◄─── CLIQUE AQUI
           └─ Actions  ◄─── CLIQUE AQUI
```

#### 4️⃣ Você verá 3 abas:
- **Secrets** ← Use esta
- Variables
- Environments

#### 5️⃣ Clique no botão verde "New repository secret"
- Fica no canto superior direito
- Cor verde

---

### 🔑 Secrets para Adicionar

#### ❓ Como Descobrir as Informações do Servidor Hetzner

Antes de adicionar os secrets, você precisa saber:

##### 1. **IP do Servidor (HETZNER_HOST)**

**Opção A: Painel Hetzner Cloud**
1. Vá para https://console.hetzner.cloud
2. Faça login
3. Selecione seu projeto
4. Clique no servidor
5. Procure por **"IPv4"** → Este é seu IP
   ```
   Exemplo: 123.45.67.89
   ```

**Opção B: Email de Boas-Vindas**
- Quando criou o servidor, Hetzner enviou email com:
  - Subject: "Your new Cloud Server"
  - Contém o IP do servidor

**Opção C: Via Terminal (se já conectou antes)**
```bash
# Liste servidores salvos no ~/.ssh/config
cat ~/.ssh/config | grep -A 5 "hetzner"

# Ou veja histórico de conexões SSH
history | grep "ssh"
```

---

##### 2. **Nome do Usuário SSH (HETZNER_USERNAME)**

**Geralmente é `root`** (padrão do Hetzner)

Para confirmar:
```bash
# Se já conectou antes, veja no histórico:
history | grep "ssh.*@"

# Você verá algo como:
# ssh root@123.45.67.89  ← "root" é o username
```

**Se criou usuário customizado:**
- Será o nome que você definiu (ex: `deploy`, `ubuntu`, `admin`)

---

##### 3. **Chave SSH (SSH_PRIVATE_KEY)**

**Descobrir qual chave usar:**

```bash
# 1. Liste suas chaves SSH
ls -la ~/.ssh/

# Você verá arquivos como:
# id_rsa          ← Chave privada (RSA)
# id_rsa.pub      ← Chave pública
# id_ed25519      ← Chave privada (ED25519)
# id_ed25519.pub  ← Chave pública
```

**Qual usar?**
- Use a chave **SEM** `.pub` no final
- Geralmente: `~/.ssh/id_rsa` ou `~/.ssh/id_ed25519`

**Copiar o conteúdo:**
```bash
# Para RSA:
cat ~/.ssh/id_rsa

# Para ED25519:
cat ~/.ssh/id_ed25519

# Se não tem certeza qual usar:
cat ~/.ssh/id_rsa 2>/dev/null || cat ~/.ssh/id_ed25519
```

**⚠️ Importante:** 
- Se aparecer "No such file or directory", você precisa criar uma chave:
  ```bash
  # Criar nova chave SSH
  ssh-keygen -t ed25519 -C "seu-email@example.com"
  
  # Depois, adicione a chave PÚBLICA ao servidor Hetzner:
  cat ~/.ssh/id_ed25519.pub
  # Copie esse conteúdo e adicione em:
  # Hetzner Console → Security → SSH Keys → Add SSH Key
  ```

---

##### 4. **Testar Conexão SSH**

Antes de configurar os secrets, teste se consegue conectar:

```bash
# Substitua com suas informações:
ssh root@SEU_IP_AQUI

# Exemplo:
ssh root@123.45.67.89

# Se conectou com sucesso ✅ → Suas informações estão corretas!
# Se deu erro ❌ → Verifique IP, username ou chave SSH
```

**Problemas comuns:**
```bash
# ❌ "Permission denied (publickey)"
# Solução: Sua chave SSH não está autorizada no servidor
# Adicione a chave pública no Hetzner Console

# ❌ "Connection refused"
# Solução: IP incorreto ou firewall bloqueando porta 22

# ❌ "Host key verification failed"
# Solução: Execute:
ssh-keygen -R SEU_IP_AQUI
```

---

#### Secret 1: `HETZNER_HOST`
1. Clique em **New repository secret**
2. **Name**: `HETZNER_HOST` (copie exatamente assim)
3. **Secret**: Cole o IP do seu servidor
   ```
   Exemplo: 123.45.67.89
   ou
   Exemplo: seu-servidor.hetzner.cloud
   ```
4. Clique em **Add secret** (botão verde)

---

#### Secret 2: `HETZNER_USERNAME`
1. Clique em **New repository secret**
2. **Name**: `HETZNER_USERNAME`
3. **Secret**: Nome do usuário SSH
   ```
   Geralmente: root
   ou
   Se criou usuário deploy: deploy
   ```
4. Clique em **Add secret**

---

#### Secret 3: `SSH_PRIVATE_KEY`
1. **PRIMEIRO**: Copie sua chave privada SSH
   ```bash
   # No seu Mac, execute no terminal:
   cat ~/.ssh/id_rsa
   
   # Ou se usa chave ED25519:
   cat ~/.ssh/id_ed25519
   ```

2. **Copie TODO o conteúdo** que aparecer, incluindo:
   ```
   -----BEGIN OPENSSH PRIVATE KEY-----
   b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
   ... (muitas linhas) ...
   -----END OPENSSH PRIVATE KEY-----
   ```

3. Volte para GitHub → **New repository secret**
4. **Name**: `SSH_PRIVATE_KEY`
5. **Secret**: Cole TODO o conteúdo da chave (Ctrl+V / Cmd+V)
6. Clique em **Add secret**

---

#### Secret 4 (Opcional): `DOCKERHUB_USERNAME`
1. **Name**: `DOCKERHUB_USERNAME`
2. **Secret**: Seu username do Docker Hub
3. Clique em **Add secret**

---

#### Secret 5 (Opcional): `DOCKERHUB_TOKEN`
1. **Criar token no Docker Hub primeiro**:
   - Vá para https://hub.docker.com/settings/security
   - Clique em "New Access Token"
   - Nome: `github-actions`
   - Permissions: Read, Write
   - Copie o token gerado

2. No GitHub:
   - **Name**: `DOCKERHUB_TOKEN`
   - **Secret**: Cole o token do Docker Hub
   - Clique em **Add secret**

---

### ✅ Como Verificar se Está Correto

Depois de adicionar os secrets, você verá uma lista assim:

```
Secrets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCKERHUB_TOKEN          Updated 1 minute ago
DOCKERHUB_USERNAME       Updated 2 minutes ago  
HETZNER_HOST             Updated 3 minutes ago
HETZNER_USERNAME         Updated 4 minutes ago
SSH_PRIVATE_KEY          Updated 5 minutes ago
```

**IMPORTANTE**: 
- ❌ Você NÃO consegue ver o valor dos secrets depois de salvar
- ✅ Você só consegue atualizar ou deletar
- ✅ Se errou, delete e crie novamente

---

### 🧪 Testar se Funciona

1. Faça um commit e push:
   ```bash
   git checkout main
   git pull
   echo "test deploy" >> README.md
   git add README.md
   git commit -m "test: trigger CD workflow"
   git push
   ```

2. Vá para a aba **Actions** no GitHub
3. Você verá o workflow rodando
4. Se os secrets estiverem corretos, o deploy funcionará ✅
5. Se houver erro, clique no workflow para ver o log

---

## Troubleshooting

### "I don't see Add branch protection rule"
- **Causa**: Você pode estar em "Branch protection rules" mas não vê o botão
- **Solução**: Certifique-se que está em **Settings** → **Branches** (não **Rules**)

### "Status checks não aparecem na lista"
- **Causa**: Os workflows ainda não rodaram
- **Solução**: 
  1. Faça push de um commit para trigger os workflows
  2. Aguarde os workflows rodarem pelo menos uma vez
  3. Depois eles aparecerão na lista de status checks

### "Cannot push to protected branch"
- ✅ **CORRETO!** Isso significa que a proteção está funcionando
- Use Pull Requests para fazer mudanças em `main` ou `develop`

---

## GitFlow Workflow Resumo

```
feature/* ──PR──> develop ──PR──> main
                    ↓               ↓
                  Alpha           Production
                  (CI/CD)         (CI/CD)
```

### Fluxo de Trabalho:
1. **Criar feature**: `git checkout -b feature/nome-feature develop`
2. **Desenvolver**: Fazer commits na feature branch
3. **Push**: `git push -u origin feature/nome-feature`
4. **PR para develop**: Criar PR no GitHub
5. **Review**: Aguardar aprovação + CI passar
6. **Merge para develop**: Merge automático após aprovação
7. **PR para main**: Quando pronto para produção, PR de `develop` → `main`
8. **Deploy**: CD automático roda após merge em `main`

