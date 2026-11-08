# Entrega: submissão, pitch e demo

Última atualização: 2026-11-08 03:20 (pitch, vídeo e descrição em [pitch.md](pitch.md)). Antes: 2026-11-07 14:42. Prazo de submissão: **domingo 08/11, 13h00**, no painel
https://hackathons.canastra.ventures/. Percorra esta lista antes de enviar (e com `/sync-docs`).

## 1. Checklist de submissão (guia, seção 7)

- [ ] **Descrição:** problema, para quem, solução e como o agente funciona. Declara que dados e integrações são sintéticos
      ou simulados. Sinaliza se responde ao Desafio Tako.
- [ ] **Vídeo de demonstração** do sistema rodando num caso real (sintético), mostrando também uma exceção.
- [ ] **Link de acesso** estável, navegável e testável, com dados pré-carregados. No ar: <https://remane.up.railway.app> (domínio trocado em 08/11 pela manhã; o antigo, `escalista-converge-production`, saiu do ar) (Railway, [DEC-037](decisoes.md)); falta a demo com dados.
- [ ] **Material de apresentação** para o pitch.
- [ ] **Ferramentas, modelos e APIs de terceiros:** copiar de [declaracao-ferramentas.md](declaracao-ferramentas.md), sem
      itens `a confirmar`.
- [ ] Nenhum segredo no repositório; `.env` fora do git.
- [ ] Histórico de commits íntegro, sem importação de outro repositório.

## 2. Teste do jurado (os jurados testam a solução)

- [ ] Abre em janela anônima, em celular e em notebook, sem instalar nada.
- [ ] Sem cadastro, ou com acesso de demonstração claro na própria tela.
- [ ] Dados pré-carregados; botão para **reiniciar a demo** ao estado inicial.
- [ ] Um caminho feliz e **pelo menos um caso difícil** que mostre a escalada ao humano com contexto pronto.
- [ ] O rastro do que o agente fez é visível ou acessível (auditoria).
- [ ] Custo por execução visível, medido (não estimado).
- [ ] Orçamento de inferência suficiente para vários jurados testarem: estime execuções por jurado e confira o saldo; se
      acabar o crédito, a demo para.
- [ ] Erro amigável quando a API do modelo falha, com fallback ou mensagem clara.
- [ ] Plano B: vídeo gravado e uma execução salva, caso a rede do evento falhe.

## 3. Pitch de 3 minutos (tempo controlado)

Esqueleto; adapte à ideia escolhida. Meta: a banca sair sabendo **quem sofre, o que o agente faz e quem paga**.

| Tempo | Conteúdo |
|---|---|
| 0:00 - 0:25 | **Problema:** quem sofre, com que frequência, quanto custa. Âncora numérica com fonte, em faixa |
| 0:25 - 0:50 | **Alternativa de hoje e why now:** como resolvem sem nós; o que mudou para tornar possível |
| 0:50 - 2:15 | **Demo ao vivo:** o agente conduzindo o caso, uma exceção resolvida com o humano, o resultado entregue |
| 2:15 - 2:40 | **Números medidos:** custo por execução, % resolvido sozinho, erros sem revisão (evals) |
| 2:40 - 3:00 | **Negócio:** quem paga, modelo de receita (hipótese rotulada), próximo passo e para onde cresce |

Ensaiar com cronômetro pelo menos 3 vezes. Quem fala o quê já definido. Uma frase de abertura que dá para dizer em 5 segundos.

### 3.1 Rascunho do pitch da IDEA-002 (**substituído** por [pitch.md](pitch.md) em 08/11 03:20: abria com a 6x1, contra a [DEC-036](decisoes.md))

Abertura de 5 segundos: "A 6x1 acaba em dezembro. Quem refaz a escala da sua loja?" Fatos e rótulos em
[IDEA-002](ideacao/ideias/IDEA-002-escalista.md).

| Tempo | O que dizer | Base |
|---|---|---|
| 0:00 - 0:25 | O gerente monta a escala na planilha e conserta faltas no WhatsApp. Errar custa hora extra (adicional mínimo de 50%), turno descoberto ou processo: horas extras é o tema mais recorrente no TST (70.508 processos julgados em 2024). Cerca de 14,9 milhões de trabalhadores estão em 6x1 (MTE), um terço dos ocupados com jornada identificada | **[FATO]**: CF art. 7º XVI, TST, Agência Senado. O 14,9 milhões é âncora de dor, não tamanho de mercado |
| 0:25 - 0:50 | Em 16/12 vêm as 42h e dois repousos, e em 2027 as 40h. A hora contratada fica 4,8% e depois 10% mais cara (conta nossa, salário fixo). Hoje: planilha, ponto que registra ou sugere ajustes, apps de escala. Só 9% do food service decidiram como se adaptar | **[FATO]** EC 141 e IFB; **[INFERÊNCIA]** os 4,8% e 10% |
| 0:50 - 2:15 | Demo ao vivo. (1) A política da empresa vira regras com a cláusula de origem; trocar de 44h para 42h ("vigência simulada") gera a nova escala com impacto em custo e em contratações. (2) A colaboradora manda o atestado no celular simulado, um colega confirma o turno, o gerente valida e a escala muda ([DEC-014](decisoes.md)). (3) Uma exceção com opções e custo, e o gerente decide. O agente não decide nada sobre pessoas | [requisitos.md](requisitos.md) RF-07, RF-09, RX, RH |
| 2:15 - 2:40 | Números do trace: custo por execução [medir], % de faltas cobertas sem hora extra [medir], tempo da falta até a cobertura [medir], violações não detectadas nos evals [medir, meta zero] | Só valor **medido**; nada estimado sem rótulo |
| 2:40 - 3:00 | Cobrança por colaborador escalado por mês (hipótese; o ponto custa de R$ 3,75 a R$ 6,90 por colaborador, Genyo). A política da empresa é parâmetro: cada convenção vira regras versionadas com origem. O canal com o trabalhador é a porta para o resto do DP. Próximo passo: piloto com uma rede | **[HIPÓTESE]** de preço; **[FATO]** da âncora de ponto |

Cuidados: não dizer que "ninguém faz isso" (ausência de evidência); não apresentar interpretação jurídica como certa; avisar que
dados e atestados são sintéticos e que o WhatsApp é simulado ou não oficial.

## 4. O que evitar

- Dizer ou sugerir que dados, simulador ou mocks são reais.
- Citar número de mercado como fato sem fonte, ou percentual de preço sem fonte.
- Mostrar seis funções pela metade em vez de uma que funciona.
- Esconder a limitação: dizer o que o agente **não** faz e onde o humano decide é ponto forte.
- Começar sem link público testado em rede diferente da do evento.

## 5. Congelamento

Sugestão: **domingo 12h00** congelar o código. Depois, só vídeo, descrição, material e envio. Enviar **antes das 13h00**, não às
12h59: o painel pode ter fila ou falha.
