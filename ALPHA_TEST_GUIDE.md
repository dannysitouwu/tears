# Alpha Test Guide - Tears Chat App

## Objetivo
Conseguir **10 usuários reais** testando a aplicação com:
- Mínimo de **10 mensagens** por usuário
- Em pelo menos **5 chats diferentes**

## Como Recrutar Testadores

### 1. Amigos e Familiares
- Explique que é um projeto acadêmico
- Peça 5-10 minutos do tempo deles
- Ofereça ajuda durante o teste

### 2. Colegas de Classe
- Faça um acordo de teste mútuo
- "Eu testo o seu, você testa o meu"

### 3. Grupos Online
- Reddit: r/alphatesting, r/webdev
- Discord: Servidores de programação
- Facebook: Grupos universitários

## Instruções para Testadores

### Setup (envie isso aos testadores):

```
🎮 TESTE DA APLICAÇÃO TEARS CHAT

1. Acesse: http://your-server-url:5174
2. Clique em "Register" e crie uma conta
3. Faça login
4. Entre em pelo menos 5 chats diferentes
5. Envie pelo menos 10 mensagens no total
6. Teste as features:
   - ✅ Criar novo chat
   - ✅ Enviar mensagem
   - ✅ Ver mensagens em tempo real
   - ✅ Buscar chats

⏱️ Tempo estimado: 5-10 minutos

Obrigado por ajudar! 🙏
```

## Chats Pré-criados (facilita o teste)

Crie estes chats antecipadamente:

1. **General Chat** - Chat geral público
2. **Random** - Conversas aleatórias
3. **Tech Talk** - Tecnologia
4. **Gaming** - Jogos
5. **Music** - Música
6. **Movies** - Filmes
7. **Sports** - Esportes

## Tracking dos Testes

### Planilha de Controle:

| # | Nome/Username | Email | Mensagens | Chats | Status | Data |
|---|--------------|-------|-----------|-------|--------|------|
| 1 | João Silva | joao@email.com | 12 | 5 | ✅ | 09/12 |
| 2 | Maria Santos | maria@email.com | 15 | 6 | ✅ | 09/12 |
| 3 | ... | ... | ... | ... | ⏳ | ... |

### Verificar no Grafana:

```logql
# Total de mensagens por usuário
{container="tears-api-1", event="websocket_message"} 
| json 
| count by user_id

# Total de chats únicos acessados
{container="tears-api-1", event="websocket_connected"} 
| json 
| count by chat_id
```

### Verificar no Banco de Dados:

```sql
-- Mensagens por usuário
SELECT user_id, COUNT(*) as message_count 
FROM message 
GROUP BY user_id;

-- Chats únicos por usuário
SELECT user_id, COUNT(DISTINCT chat_id) as unique_chats
FROM chat_member
GROUP BY user_id;
```

## Formulário de Feedback (Google Forms)

Crie um formulário com:

1. **Nome/Username**
2. **Facilidade de uso** (1-5 estrelas)
3. **Velocidade das mensagens** (1-5 estrelas)
4. **Bugs encontrados?** (texto livre)
5. **Sugestões de melhoria** (texto livre)
6. **Usaria novamente?** (Sim/Não)

## Checklist Final

- [ ] 10 usuários únicos registrados
- [ ] Cada usuário enviou ≥10 mensagens
- [ ] Mensagens distribuídas em ≥5 chats
- [ ] Coletar feedback de todos
- [ ] Screenshots do Grafana mostrando atividade
- [ ] Exportar dados do banco para evidência
- [ ] Documentar bugs encontrados
- [ ] Criar issue no GitHub para cada bug

## Evidências para Entregar

1. **Screenshots Grafana**:
   - Total de mensagens
   - Usuários ativos
   - Chats mais populares

2. **Query Results**:
   - Lista de usuários e message_count
   - Estatísticas de uso

3. **Feedback Summary**:
   - Respostas do formulário
   - Principais bugs
   - Sugestões de melhoria

4. **Vídeo/GIF** (opcional):
   - Demonstração de uso em tempo real
   - Mostrar WebSocket funcionando

## Dicas

- ✅ Teste você mesmo primeiro
- ✅ Tenha pelo menos 3 chats já criados
- ✅ Monitore Grafana durante os testes
- ✅ Esteja disponível para ajudar
- ✅ Agradeça os testadores!
