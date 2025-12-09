# Guia de Deploy - Frontend Dashboard

## 🚀 Passo a Passo Rápido (10-30 minutos)

### 1️⃣ Fazer Build do Frontend React

```bash
cd /Users/dannysito/Documents/tears/tears-frontend
npm run build
```

Isso cria a pasta `dist/` com arquivos otimizados.

---

### 2️⃣ Deploy no Servidor Hetzner

**Conectar via SSH:**
```bash
ssh root@91.99.132.110
```

**Criar diretório para o frontend:**
```bash
mkdir -p /var/www/tears-frontend
```

**No seu Mac, enviar build para o servidor:**
```bash
# Voltar para sua máquina local (sair do SSH)
cd /Users/dannysito/Documents/tears/tears-frontend
scp -r dist/* root@91.99.132.110:/var/www/tears-frontend/
```

---

### 3️⃣ Instalar e Configurar Nginx no Hetzner

**No servidor (via SSH):**

```bash
# Instalar Nginx (se ainda não tiver)
apt update
apt install nginx -y

# Criar configuração do frontend
nano /etc/nginx/sites-available/tears-frontend
```

**Copiar o conteúdo de `observability/nginx-frontend.conf` para este arquivo.**

Ajustar linha 4:
```nginx
server_name seu-dominio.com;  # ou use 91.99.132.110
```

**Ativar o site:**
```bash
ln -s /etc/nginx/sites-available/tears-frontend /etc/nginx/sites-enabled/
```

**Testar configuração:**
```bash
nginx -t
```

**Recarregar Nginx:**
```bash
systemctl reload nginx
```

---

### 4️⃣ Configurar Promtail para Coletar Logs do Frontend

**No servidor (via SSH):**

```bash
cd /caminho/para/observability/promtail
cp config.yml config.yml.backup  # Backup da configuração atual
nano config.yml
```

**Adicionar o job `tears-frontend` no final do arquivo** (copiar de `config-with-frontend.yml`):

```yaml
  # NOVO: Job para logs do Frontend (Nginx)
  - job_name: tears-frontend
    static_configs:
      - targets:
          - localhost
        labels:
          job: tears-frontend
          __path__: /var/log/nginx/tears-frontend-access.log

    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            remote_addr: remote_addr
            request: request
            status: status
            body_bytes_sent: body_bytes_sent
            request_time: request_time
            http_referer: http_referer
            http_user_agent: http_user_agent

      - regex:
          expression: '^(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>\S+)$'
          source: request

      - labels:
          status:
          remote_addr:
          method:
          path:

      - timestamp:
          source: timestamp
          format: RFC3339Nano
```

**Atualizar `docker-compose.yml` do Promtail** para ter acesso aos logs do Nginx:

```yaml
services:
  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./promtail/config.yml:/etc/promtail/config.yml
      - /var/run/docker.sock:/var/run/docker.sock
      - /var/log/nginx:/var/log/nginx:ro  # ADICIONAR ESTA LINHA
    # ... resto da configuração
```

**Reiniciar Promtail:**
```bash
cd /caminho/para/observability
docker-compose restart promtail
```

---

### 5️⃣ Importar Dashboard no Grafana

1. **Acessar Grafana:** http://91.99.132.110:3000
2. **Login:** admin / admin (ou sua senha configurada)
3. **Menu lateral esquerdo → Dashboards → Import**
4. **Upload JSON file:** Selecionar `/Users/dannysito/Documents/tears/observability/grafana/dashboards/tears-frontend-dashboard.json`
5. **Selecionar Data Source:** Loki
6. **Clicar em "Import"**

---

### 6️⃣ Testar e Validar

**Gerar tráfego:**
```bash
# No seu Mac
for i in {1..50}; do curl http://91.99.132.110/; sleep 0.1; done
```

**Verificar logs:**
```bash
# No servidor
tail -f /var/log/nginx/tears-frontend-access.log
```

**Validar no Grafana:**
1. Abrir dashboard "Tears Frontend Monitoring"
2. Verificar se aparecem dados nos painéis (aguardar 30-60 segundos)
3. Painel "Page Views Over Time" deve mostrar gráfico
4. Painel "Recent Frontend Access Logs" deve mostrar logs em tempo real

---

## ✅ Checklist de Verificação

- [ ] Build do React criado (`npm run build`)
- [ ] Arquivos copiados para `/var/www/tears-frontend/`
- [ ] Nginx configurado em `/etc/nginx/sites-available/tears-frontend`
- [ ] Site ativado: `ln -s /etc/nginx/sites-available/tears-frontend /etc/nginx/sites-enabled/`
- [ ] Nginx testado: `nginx -t` (sem erros)
- [ ] Nginx recarregado: `systemctl reload nginx`
- [ ] Site acessível: http://91.99.132.110 retorna página React
- [ ] Logs JSON sendo criados em `/var/log/nginx/tears-frontend-access.log`
- [ ] Promtail atualizado com job `tears-frontend`
- [ ] Promtail reiniciado: `docker-compose restart promtail`
- [ ] Dashboard importado no Grafana
- [ ] Dados aparecendo nos painéis do dashboard

---

## 🐛 Troubleshooting

### Nginx não inicia
```bash
nginx -t  # Ver erro específico
systemctl status nginx
journalctl -u nginx -n 50
```

### Logs não aparecem no Grafana
```bash
# Verificar se logs estão sendo criados
ls -lh /var/log/nginx/tears-frontend-access.log

# Verificar Promtail
docker-compose logs promtail | tail -50

# Verificar Loki
docker-compose logs loki | tail -50

# Query manual no Grafana Explore
{job="tears-frontend"}
```

### Dashboard vazio
- Aguardar 1-2 minutos (delay normal)
- Verificar se Time Range está correto (últimas 6 horas)
- Gerar tráfego: `curl http://91.99.132.110/`
- Verificar no Grafana Explore: `{job="tears-frontend"} | json`

### CORS errors no browser
- Verificar `add_header 'Access-Control-Allow-Origin'` no Nginx
- Ajustar para seu domínio ou `*` (não recomendado em produção)

---

## 📝 Próximos Passos

Após dashboard funcionando:

1. **Configurar alertas** (já tem um configurado para error rate > 5/min)
2. **Adicionar HTTPS** com Let's Encrypt: `certbot --nginx -d seu-dominio.com`
3. **Criar snapshots** do dashboard para documentação
4. **Executar Alpha Test** com 10 usuários
5. **Coletar feedback** e screenshots para relatório final

---

## 🎯 Tempo Estimado

- Deploy inicial: 10-15 minutos
- Troubleshooting (se necessário): +15 minutos
- **Total: 10-30 minutos**

---

## 📚 Referências

- Nginx JSON logging: https://nginx.org/en/docs/http/ngx_http_log_module.html
- Promtail stages: https://grafana.com/docs/loki/latest/send-data/promtail/stages/
- Grafana dashboards: https://grafana.com/docs/grafana/latest/dashboards/
