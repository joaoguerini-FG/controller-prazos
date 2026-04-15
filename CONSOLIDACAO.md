# Consolidação do Projeto — 2026-04-15

Snapshot completo do estado do Controller de Prazos.
Leia isto primeiro quando voltar ao projeto.

---

## 🟢 O que está funcionando HOJE

| Componente | Status | Onde |
|-----------|--------|------|
| Captura DJEN | ✅ OK | `pipeline_diario.py` (API pública, 3 filtros) |
| Base de conhecimento | ✅ OK | `base_conhecimento.json` (170 regras, 869 GOLD) |
| Classificação IA | ✅ OK | `motor_definitivo.py` (GPT-4.1 + validação natureza) |
| Dashboard HTML | ✅ OK | `dash_simples.py` → `index.html` |
| Deploy Netlify | ✅ ATIVO | `https://eloquent-banoffee-0b057f.netlify.app/` |
| Repositório GitHub | ✅ ATIVO | `https://github.com/joaoguerini-FG/controller-prazos` |
| Ground truth v4 | ✅ OK | 149 pares validados (filtro 60d + conteúdo puro) |

## 🟡 O que está pendente

| Item | Por quê | Como fazer |
|------|---------|-----------|
| Renomear site Netlify | URL atual é aleatória | Netlify → Project configuration → Change site name → `advisian-prazos` |
| Automação diária | GitHub Actions bloqueado (CNJ bloqueia IP Azure) | Windows Task Scheduler local (instruções abaixo) |
| Criação automática de tarefas DataJuri | API é read-only | Playwright/Selenium em dj33.datajuri.com.br |
| Alerta WhatsApp BAIXA confiança | Não implementado | Seguir padrão `auditoria-liderhub` |

## 🔴 Riscos mapeados

| Risco | Mitigação atual |
|-------|-----------------|
| HD morrer | Backup zip em OneDrive (`_BACKUP_ADVISIAN/`) |
| Credenciais vazarem | `.gitignore` bloqueia `intimacoes_config.json` (verificado) |
| URL Netlify sumir | Conta do João, pode re-deploy a qualquer hora |
| Repo GitHub deletado | Clone local existe |
| CNJ mudar API DJEN | Ponto único de falha — monitorar |
| OpenAI key revogada | Re-gerar em platform.openai.com |

---

## 📁 Inventário de backup (2026-04-15 04:53)

### Backup primário
**Local:** `C:\Users\joaof\Documents\intimacoes_BACKUP_2026-04-15\intimacoes_critical_2026-04-15.zip`

### Backup cloud (sincroniza OneDrive)
**Local:** `C:\Users\joaof\OneDrive\_BACKUP_ADVISIAN\intimacoes_critical_2026-04-15.zip`

### Conteúdo do backup (511 KB total)
- `base_conhecimento.json` (704 KB) — **mais valioso, destilação de 50k tarefas**
- `intimacoes_state.json` (1.6 MB) — 293 publicações classificadas
- `ground_truth_v4.json` (418 KB) — 149 pares validados
- `intimacoes_config.json` (922 B) — **CREDENCIAIS**, não está no git
- `dash_simples.py`, `motor_definitivo.py`, `pipeline_diario.py`
- `README.md`, `SETUP_DEPLOY.md`

---

## 🔑 Credenciais (onde recuperar se perder)

Tudo está em `intimacoes_config.json` (local + OneDrive backup).

### DataJuri
- Painel: https://dj33.datajuri.com.br
- Login: `joaoguerini@furtadoguerini.com.br`
- Client ID / Secret: gerar novo em Configurações → API

### OpenAI
- Painel: https://platform.openai.com/api-keys
- Se perder: revogar todas, gerar nova, atualizar config + GitHub Secret

### GitHub
- Repo: https://github.com/joaoguerini-FG/controller-prazos
- Conta: joaoguerini-FG

### Netlify
- Painel: https://app.netlify.com
- Logar com o email que usou ao subir o site
- Site atual: `eloquent-banoffee-0b057f`

---

## 🔄 Como retomar o desenvolvimento amanhã

### Cenário 1: Só quero regenerar o dashboard (state já existe)
```bash
cd C:\Users\joaof\Documents\intimacoes
python dash_simples.py
# Arrastar deploy/index.html em https://app.netlify.com (ou Netlify Drop)
```

### Cenário 2: Quero capturar + classificar novas publicações
```bash
cd C:\Users\joaof\Documents\intimacoes
python pipeline_diario.py
# state.json vai ser atualizado automaticamente
python dash_simples.py
# redeploy Netlify
```

### Cenário 3: Restaurar em PC novo
```bash
# 1. Instalar Python 3.12
# 2. Clonar repo
git clone https://github.com/joaoguerini-FG/controller-prazos.git
cd controller-prazos

# 3. Instalar dependências
pip install requests openai openpyxl

# 4. Restaurar credenciais (NÃO estão no git!)
# Copiar intimacoes_config.json de: C:\Users\joaof\OneDrive\_BACKUP_ADVISIAN\
#   (descompactar zip → pegar o arquivo)

# 5. Testar
python pipeline_diario.py
```

### Cenário 4: Configurar Task Scheduler (automação diária 06h)
1. Abrir "Agendador de Tarefas" (taskschd.msc)
2. Criar Tarefa Básica:
   - Nome: `Controller Prazos Diario`
   - Trigger: Diário às 06:00
   - Ação: Iniciar programa
     - Programa: `python`
     - Argumentos: `C:\Users\joaof\Documents\intimacoes\pipeline_diario.py`
     - Iniciar em: `C:\Users\joaof\Documents\intimacoes`
3. Configurações adicionais:
   - Executar mesmo se usuário não estiver logado
   - Executar com privilégios mais altos

---

## 📊 Números do estado atual

- **Publicações capturadas:** 22.625 (histórico completo, 16 meses)
- **Publicações classificadas em produção:** 293 (13-15/04/2026)
- **Regras conhecidas:** 170
- **Exemplos GOLD no RAG:** 869
- **Ground truth validado:** 149 pares
- **Processos ativos no escritório:** 6.019
- **Tarefas históricas analisadas:** ~50.000

---

## 🧠 Lições aprendidas (não repetir erros)

1. **Ground truth precisa remover processo, nome, tribunal** — senão a similaridade fica inflada por ruído comum. V4 fez certo.
2. **V2 da base de conhecimento ficou PIOR que V1** — mais dados ≠ melhor. V1 é o release.
3. **Não confiar em `claude-opus-4-6-20250610`** — o ID correto é `claude-opus-4-6` (sem data).
4. **max_tokens=500 trunca JSON** — sempre 2000+ para respostas estruturadas.
5. **CNJ bloqueia IP Azure** — nada de GitHub Actions para captura. Rodar local.
6. **DataJuri API é READ-ONLY** — POST/PUT rejeitados. Para criar tarefas: automação browser.
7. **Filtro HARD de natureza é obrigatório** — IA confunde Previdenciário com Cível em edge cases.
8. **Distribuição ≠ Reclamação Trabalhista** — distribuição mapeia para CADASTRAR PROCESSO.
9. **Reclamação Trabalhista é INFORMATIVO** — não tem prazo, é só registro.
10. **Dedup deve ser conservadora** — só remover com texto 100% idêntico. Risco de perder prazo > risco de revisar duplicata.

---

## 📞 Próxima sessão com o Claude

Copiar e colar para retomar com contexto:

> Retomando o projeto Controller de Prazos (ADVISIAN/Furtado Guerini).
> Leia primeiro `C:\Users\joaof\Documents\intimacoes\CONSOLIDACAO.md` e `README.md`.
> Estado: dashboard no ar em Netlify, 293 pubs classificadas, tudo commitado.
> Quero trabalhar em: [ESCREVER O OBJETIVO DA PRÓXIMA SESSÃO]

---

*Consolidação feita em 15/04/2026 às 04:53 por João + Claude (Sonnet 4.5).*
