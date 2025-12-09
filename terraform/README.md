# Terraform Infrastructure - Tears Application

Este diretório contém a configuração Terraform para provisionar a infraestrutura da aplicação Tears na Hetzner Cloud.

## 📋 Pré-requisitos

1. **Conta Hetzner Cloud**: [Criar conta](https://console.hetzner.cloud/)
2. **Terraform instalado**: `brew install terraform` (macOS) ou [Download](https://www.terraform.io/downloads)
3. **API Token da Hetzner**: Criar em Cloud Console → Security → API Tokens
4. **Par de chaves SSH**: `ssh-keygen -t rsa -b 4096 -C "seu-email@example.com"`

## 🚀 Setup Inicial

### 1. Configurar Variáveis

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edite `terraform.tfvars` com seus valores:

```hcl
hcloud_token    = "seu-token-aqui"
ssh_public_key  = "conteúdo-da-sua-chave-publica"
server_type     = "cx22"
location        = "nbg1"
```

### 2. Inicializar Terraform

```bash
terraform init
```

### 3. Revisar o Plano

```bash
terraform plan
```

### 4. Aplicar a Infraestrutura

```bash
terraform apply
```

Digite `yes` quando solicitado.

## 📦 O que é Provisionado?

### Recursos Criados:

1. **Servidor Hetzner (cx22)**
   - 2 vCPUs
   - 4GB RAM
   - 40GB SSD
   - Ubuntu 22.04

2. **Volume Persistente (10GB)**
   - Para dados do PostgreSQL
   - Backup automático disponível

3. **Firewall**
   - Porta 22 (SSH)
   - Porta 80 (HTTP)
   - Porta 443 (HTTPS)
   - Porta 8000 (API)
   - Porta 3000 (Grafana)
   - Porta 9090 (Prometheus)

4. **Configuração Automática (Cloud-Init)**
   - Docker e Docker Compose instalados
   - Repositório Git clonado
   - Serviços iniciados automaticamente
   - Nginx configurado como reverse proxy

### Opcional:
5. **Load Balancer** (desabilitado por padrão)
   - Health checks automáticos
   - Distribuição de carga

## 🔧 Comandos Úteis

### Ver Outputs
```bash
terraform output
```

### Ver IP do Servidor
```bash
terraform output backend_server_ip
```

### Conectar via SSH
```bash
ssh root@$(terraform output -raw backend_server_ip)
```

### Atualizar Infraestrutura
```bash
terraform plan
terraform apply
```

### Destruir Infraestrutura
```bash
terraform destroy
```

## 🔐 GitHub Secrets Necessários

Configure estes secrets no GitHub (Settings → Secrets and variables → Actions):

| Secret | Descrição |
|--------|-----------|
| `HCLOUD_TOKEN` | Token da API Hetzner Cloud |
| `SSH_PUBLIC_KEY` | Sua chave SSH pública |

## 🤖 CI/CD com Terraform

### Workflow de Plan (Pull Requests)
- Roda automaticamente em PRs
- Mostra o plano no comentário do PR
- Valida a configuração

### Workflow de Apply (Push to Main)
- Aplica mudanças automaticamente quando merge no `main`
- Salva outputs como artifacts
- Cria summary do deployment

### Manual Destroy
Vá em Actions → Terraform Apply → Run workflow → Escolha "destroy"

## 📊 Custos Estimados

| Recurso | Tipo | Custo Mensal (EUR) |
|---------|------|-------------------|
| Servidor | cx22 | ~€5.83 |
| Volume | 10GB | ~€0.50 |
| Load Balancer | lb11 (opcional) | ~€5.39 |
| **Total** | | **~€6.33/mês** |

## 🔄 Upgrades e Manutenção

### Upgrade do Servidor
```hcl
# terraform.tfvars
server_type = "cx32"  # 4 vCPU, 8GB RAM
```

```bash
terraform apply
```

### Aumentar Volume do PostgreSQL
```hcl
# terraform.tfvars
postgres_volume_size = 20  # GB
```

```bash
terraform apply
```

### Habilitar Load Balancer
```hcl
# terraform.tfvars
enable_load_balancer = true
```

```bash
terraform apply
```

## 🛡️ Segurança

### Recomendações:

1. **Restringir acesso ao Grafana/Prometheus**:
   ```hcl
   monitoring_allowed_ips = ["seu-ip-publico/32"]
   ```

2. **Usar SSH com chave, não senha**
   - Já configurado automaticamente

3. **Configurar SSL/TLS**:
   ```bash
   ssh root@SEU_IP
   certbot --nginx -d seudominio.com
   ```

4. **Backups automáticos**:
   - Habilitar na console Hetzner
   - Ou usar snapshots programados

## 📝 Troubleshooting

### Erro: "Token inválido"
```bash
export HCLOUD_TOKEN="seu-token"
terraform plan
```

### Servidor não responde
```bash
# Ver logs do cloud-init
ssh root@$(terraform output -raw backend_server_ip)
cat /var/log/cloud-init-output.log
```

### Verificar status dos containers
```bash
ssh root@$(terraform output -raw backend_server_ip)
cd /opt/tears/api && docker-compose ps
```

## 🔗 Links Úteis

- [Documentação Hetzner Provider](https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Hetzner Cloud Console](https://console.hetzner.cloud/)

## 📞 Próximos Passos Após Deploy

1. **Configurar DNS**:
   - Apontar `A record` para o IP do servidor
   - Ex: `tears.seudominio.com → IP_DO_SERVIDOR`

2. **Configurar SSL**:
   ```bash
   ssh root@IP_SERVIDOR
   certbot --nginx -d tears.seudominio.com
   ```

3. **Acessar serviços**:
   - Frontend: `http://IP_SERVIDOR`
   - API: `http://IP_SERVIDOR/api`
   - Grafana: `http://IP_SERVIDOR:3000` (admin/admin)
   - Prometheus: `http://IP_SERVIDOR:9090`

4. **Configurar Grafana**:
   - Trocar senha padrão
   - Importar dashboards
   - Configurar alertas
