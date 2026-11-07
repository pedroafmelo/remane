> **ARQUIVADO em 07/11/2026.** Material da IDEA-001 (recuperação de depósitos judiciais), preservado para consulta. A ideia não é mais a escolhida; ver [DEC-001](../../decisoes.md) e a [ficha](../../ideacao/ideias/IDEA-001-recuperacao-depositos.md). Só os links relativos foram ajustados.

# Arquitetura-alvo

Rascunho de arquitetura (preparação pré-evento: só texto, sem código). `[H]` marca intervenção humana.
`[H*]` marca aprovação obrigatória por natureza jurídica e financeira.

```
 0. ONBOARDING (uma vez por cliente)
    planilha + pasta de documentos + descrição em linguagem natural
      -> perfil da planilha -> mapeamento de colunas
      -> extração de regras (com trecho de origem) -> "cartão de regras"
      -> simulação em amostra -> [H] aprova e congela a versão (hash)

 1. INGESTÃO
    planilha -> normalização -> validação do número CNJ (dígito verificador)
    inválidos -> fila de exceção (motivo) [H se acima do teto de valor]

 2. FILTROS DETERMINÍSTICOS (custo zero)
    tribunal, classe, tipo de procedimento, partes, valor mínimo (do cartão de regras)

 3. ENRIQUECIMENTO (simulador DataJud no demo; API real em produção)
    classe, movimentos, órgão -> status "arquivado definitivo" (TPU 861/246, baixa 22)
    divergência entre planilha e tribunal -> exceção

 4. DOCUMENTOS (PDFs sintéticos no demo)
    seleção de páginas relevantes -> OCR barato -> parsing
    cascata: modelo pequeno -> escala ao grande somente se confiança < limiar
    auto-verificação dos campos contra o texto-fonte

 5. SCORE DE RECUPERABILIDADE
    regras + modelo; saída = score + confiança calibrada + evidências citadas

 6. ROTEAMENTO POR INCERTEZA
    alta confiança e baixo valor -> segue
    baixa confiança ou valor acima do teto -> [H] fila com contexto pronto

 7. AÇÃO
    gera minuta de petição / pedido de alvará (não protocola)
    -> [H*] advogado aprova e protocola

 8. REGISTRO E MEDIÇÃO
    trace de cada passo (Langfuse), custo e latência por processo
    evals em casos rotulados; painel: intervenção, erros sem revisão, R$/processo
```

## Integrações simuladas (que o agente realmente chama)

| Mock | Papel |
|---|---|
| Tribunal (formato DataJud) | Classe, órgão, movimentos, com códigos da TPU para arquivamento |
| Extrato / banco | Saldo e titularidade do depósito |
| Sistema do escritório | Criação de tarefa e registro da minuta aprovada |
| Notificação | E-mail ou Slack simulados |

## Sempre com aprovação humana (advogado)

- Protocolar petição ou pedido de alvará.
- Qualquer movimentação de dinheiro.
- Renúncia ou desistência de crédito.
- Comunicação a partes ou terceiros.
- Classificar como "irrecuperável" acima de um valor-teto.

## Métricas (painel e evals)

| Métrica | Definição |
|---|---|
| Taxa de intervenção | % de processos que exigem humano |
| Decisões erradas sem revisão | Erros que passaram sem escalar. **A mais importante**, meta próxima de zero |
| Precision@k / recall ponderado por valor | Qualidade do ranking de prioridade |
| Calibração | A confiança corresponde à acurácia real? |
| Custo por processo e tempo ponta a ponta | Medidos no trace, comparados ao manual (hipótese) |

## Decisões em aberto (resolver no evento e registrar em `docs/decisoes.md`)

- Framework de UI e plataforma de deploy do link público.
- Quais modelos do Featherless para o nível pequeno e para o grande.
- OCR: qual engine open source ou API de baixo custo.
- Formato exato do cartão de regras.
