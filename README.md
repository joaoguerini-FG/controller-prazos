# Controller de Prazos — ADVISIAN / Furtado Guerini

Sistema de classificação automática de intimações DJEN com IA (GPT-4.1 + Claude Opus 4.6).

Transforma publicações oficiais do DJEN em prazos auditáveis, cruzando com a base de ~50.000 tarefas históricas do DataJuri.

---

## Dashboard online

**URL pública:** https://eloquent-banoffee-0b057f.netlify.app/

> A URL pode ser renomeada em Netlify → Project configuration → Change site name.
> Meta: `https://advisian-prazos.netlify.app`

---

## Arquitetura

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   API DJEN     │────▶│    DataJuri    │────▶│  Motor de IA   │
│    (CNJ)       │     │  (contexto)    │     │  GPT-4.1 +     │
│  3 filtros:    │     │   OAuth 2.0    │     │  Base 170      │
│  OAB/nome/esc. │     │  READ-ONLY     │     │  regras        │
└────────────────┘     └────────────────┘     └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │   Dashboard    │
                                              │     HTML       │
                                              │  (Netlify)     │
                                              └────────────────┘
```

## Pipeline

1. **Captura DJEN** — API pública CNJ, 3 filtros paralelos (OAB 30079/ES + nome JOAO FURTADO GUERINI + nome FURTADO GUERINI)
2. **Deduplicação conservadora** — só remove duplicatas com texto 100% idêntico
3. **Enriquecimento DataJuri** — natureza, histórico, fase processual, andamentos
4. **Classificação IA** — GPT-4.1 com base de conhecimento (170 regras, 869 exemplos GOLD)
5. **Validação hard** — filtro por natureza + retry automático em caso de area_mismatch
6. **Calibração de confiança** — ALTA/MEDIA/BAIXA com flags de revisão humana
7. **Dashboard HTML** — interativo, tema claro/escuro, filtros multi-select, Visual Law

---

## Arquivos do projeto

### Código (tracked no git)
| Arquivo | Função |
|---------|--------|
| `pipeline_diario.py` | Pipeline completo (captura + classifica + atualiza state) |
| `motor_definitivo.py` | Classificador com todas as validações e retry |
| `dash_simples.py` | Gera `index.html` / `dashboard_prazos.html` com branding ADVISIAN |
| `gerar_planilha.py` | Exporta para Excel (aba auditoria) |

### Dados (tracked no git)
| Arquivo | Conteúdo | Tamanho |
|---------|----------|---------|
| `base_conhecimento.json` | 170 regras DataJuri + 869 exemplos GOLD destilados de 50k tarefas | 704 KB |
| `intimacoes_state.json` | 293 publicações classificadas (13-15/04/2026) | 1.6 MB |
| `fluxo_prazos_*.txt` | Referência manual de prazos (trabalhista/cível/previdenciário) | — |

### Ignorados pelo git (.gitignore)
| Arquivo | Motivo |
|---------|--------|
| `intimacoes_config.json` | **CREDENCIAIS** — DataJuri OAuth + OpenAI API key |
| `ground_truth_v4.json` | Ground truth 149 pares validados (reconstruível) |
| `historico_djen_completo.json` | 22.625 publicações históricas (57 MB — reconstruível via API) |
| `base_conhecimento_v2.json` | Versão experimental (pior que v1) |
| Scripts auxiliares | Têm API keys hardcoded — manter local apenas |

---

## Setup

### Dependências
```bash
pip install requests openai openpyxl
```

### Credenciais necessárias (`intimacoes_config.json`)
```json
{
  "datajuri": {
    "client_id": "...",
    "secret": "...",
    "user": "...",
    "pass": "..."
  },
  "openai_api_key": "sk-proj-...",
  "oab_numero": "30079",
  "oab_uf": "ES",
  "nome_advogado": "JOAO FURTADO GUERINI",
  "nome_escritorio": "FURTADO GUERINI"
}
```

### Execução manual
```bash
# Pipeline completo (captura + enriquece + classifica)
python pipeline_diario.py

# Só regenerar dashboard a partir do state.json existente
python dash_simples.py
```

---

## Deploy

### Netlify (atual, funcional)
1. `python dash_simples.py` — gera `index.html`
2. Arrastar pasta `deploy/` em https://app.netlify.com/drop
3. URL instantânea e atualiza na mesma conta

### GitHub Actions (bloqueado)
CNJ bloqueia IPs do Azure/GitHub Actions (403 Forbidden em `comunicaapi.pje.jus.br`).
Solução: rodar localmente via **Windows Task Scheduler** todo dia às 06h.

### Task Scheduler local (recomendado)
```
Trigger: Daily at 06:00
Action: python C:\Users\joaof\Documents\intimacoes\pipeline_diario.py
Condition: Start only if network connection available
```

---

## Performance atual

| Métrica | Valor |
|---------|-------|
| Publicações no histórico | 22.625 (16 meses) |
| Publicações classificadas | 293 (13-15/04/2026) |
| Confiança ALTA | ~48% |
| Confiança MÉDIA | ~35% |
| Confiança BAIXA | ~17% (requer revisão humana) |
| Tempo por publicação | ~4s (captura + classificação) |
| Custo OpenAI por pub | ~US$ 0.006 (GPT-4.1) |

---

## Roadmap

### Fase atual (MVP consolidado)
- [x] Captura DJEN via API pública
- [x] Classificação IA com base de conhecimento
- [x] Dashboard ADVISIAN público
- [x] Deploy Netlify

### Próxima fase
- [ ] Renomear Netlify para `advisian-prazos.netlify.app`
- [ ] Task Scheduler local (06h diário)
- [ ] Alertas WhatsApp para BAIXA confiança (seguir padrão auditoria-liderhub)
- [ ] Auto-criação de tarefas no DataJuri via Playwright (Chrome automation — API é read-only)

### Fase futura
- [ ] Expansão multi-OAB (sócios do escritório)
- [ ] Ground truth contínuo (feedback loop humano)
- [ ] Dashboard Visual Law por processo individual

---

## Licença
Proprietary — Furtado Guerini Advogados. Não redistribuir.

## Autoria
João Furtado Guerini + Claude (Anthropic) · Abril 2026
