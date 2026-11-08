# Retrato dos evals (SINTÉTICO)

Última atualização: 2026-11-08

Esta pasta guarda o **retrato** do relatório dos evals do Escalista: `evals-latest.json`. Tudo o que está nele vem de
dados sintéticos gerados pelo time (nenhum dado real) e é medido por código; nada é estimado à mão.

## Para que serve

O relatório completo (`var/evals/all-latest.json`) não vai ao link público: `var/` fica fora do git e fora da imagem
Docker. O retrato é a cópia commitada desse relatório. A imagem copia `data/`, a rota `GET /api/evals` (papel gestor) o
lê e a área **Impacto** mostra o bloco "Evals (dados sintéticos)". Sem o arquivo, a tela diz "Relatório de evals ainda
não publicado".

## Como é gerado

```
uv run python -m escalista.evals --suite all --snapshot data/evals                  # sem modelo (padrão)
uv run python -m escalista.evals --suite all --with-model --snapshot data/evals     # rodada à mão, com chave e teto
```

Antes de gravar, o retrato é conferido contra os valores plantados nos atestados sintéticos (`planted_cid`). Se algum
aparecer no relatório, **nada é gravado** e o erro aponta o caminho JSON, nunca o valor. Sem gabaritos de atestado
disponíveis, o campo `privacidade` diz "sem valores plantados disponíveis".

O arquivo `evals-latest.json` é commitado junto com o código que o gerou (`git_sha` dentro dele). Para a variável de
ambiente `EVALS_SNAPSHOT_PATH`, outro caminho é lido no lugar deste (útil em teste).

## Regras do que entra

- Só número **medido** na rodada. O que não foi medido aparece como `não medido` ou `null`, nunca como zero.
- Cenário `não executado` (sem chave, teto de orçamento, saída ausente) **nunca** conta como aprovado: é um total à
  parte, em cinza na tela.
- Custo e latência do modelo são os do rastro da rodada com modelo; sem a rodada, `null`.
- Estimativas de tempo manual e números de mercado não entram aqui.
