# Entrega: submissão, pitch e demo

Última atualização: 2026-11-07 11:55. Prazo de submissão: **domingo 08/11, 13h00**, no painel
https://hackathons.canastra.ventures/. Percorra esta lista antes de enviar (e com `/sync-docs`).

## 1. Checklist de submissão (guia, seção 7)

- [ ] **Descrição:** problema, para quem, solução e como o agente funciona. Declara que dados e integrações são sintéticos
      ou simulados. Sinaliza se responde ao Desafio Tako.
- [ ] **Vídeo de demonstração** do sistema rodando num caso real (sintético), mostrando também uma exceção.
- [ ] **Link de acesso** estável, navegável e testável, com dados pré-carregados.
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

## 4. O que evitar

- Dizer ou sugerir que dados, simulador ou mocks são reais.
- Citar número de mercado como fato sem fonte, ou percentual de preço sem fonte.
- Mostrar seis funções pela metade em vez de uma que funciona.
- Esconder a limitação: dizer o que o agente **não** faz e onde o humano decide é ponto forte.
- Começar sem link público testado em rede diferente da do evento.

## 5. Congelamento

Sugestão: **domingo 12h00** congelar o código. Depois, só vídeo, descrição, material e envio. Enviar **antes das 13h00**, não às
12h59: o painel pode ter fila ou falha.
