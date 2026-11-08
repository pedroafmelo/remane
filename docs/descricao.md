> *Remane: o engenheiro da sua escala de trabalho.* Responde ao *Desafio Tako* (Digital Workers para RH, frente de
> Departamento Pessoal).
>
> *Problema:* Toda empresa com equipe em turnos monta escala toda semana, e quase sempre à mão: planilha, papel ou mensagem.
> Uma escala feita assim não é otimizada nem conferida. Ela custa mais do que precisava, com hora extra que ninguém planejou e
> turno descoberto no horário de pico, e descumpre a lei sem que ninguém perceba: repouso semanal, descanso entre jornadas, domingo,
> limite de hora extra. As regras estão espalhadas entre a CLT, a convenção coletiva e a política da empresa, e ninguém tem tempo de
> cruzar as três a cada troca. Quando alguém falta, cobre quem atende o telefone, não quem sai mais barato, quase sempre com hora
> extra. O erro custa duas vezes: na folha e na Justiça do Trabalho, onde hora extra foi o tema mais recorrente do TST em 2024
> (70.508 processos).
>
> *Por que agora:* A EC 141 leva a jornada para 42 h com dois repousos semanais a partir de 16/12/2026, e toda escala em vigor
> precisa ser refeita. No food service, 91% das 132 empresas ouvidas pelo IFB ainda não sabem como vão cumprir a nova jornada.
>
> *Para quem:* Qualquer operação com turnos sob a CLT, do ponto de venda único às redes com dezenas de unidades: as regras vêm da
> lei, da convenção e da política de cada empresa, não de um setor. Começamos pelas redes de varejo, food service e farmácia com 5 a
> 200 unidades que ainda fazem escala em planilha, onde o erro se repete em cada loja. Atende o gestor que monta a escala, o DP que
> responde por ela e o colaborador que a recebe e avisa as faltas.
>
> *Solução:* O gestor envia a escala como ela já existe, em XLSX, CSV ou PDF. O Pat, agente do Remane, lê o arquivo, mostra o que
> entendeu e espera a confirmação. Depois monta a escala de menor custo que cumpre a lei, a convenção e a política da empresa, e
> mostra lado a lado a de antes e a nova, com custo, hora extra, cobertura e violações. Se o quadro não fecha a demanda dentro da
> regra, ele mostra quanto falta, em vez de esconder o buraco com hora extra. Durante a semana, quando o colaborador avisa uma falta,
> o agente procura quem cobre sem hora extra e respeitando o descanso, e leva ao gestor um cartão com as opções, o custo de cada uma
> e uma recomendação. *Nada é publicado sem aprovação humana.*
>
> *Como o agente funciona:* Grafo LangGraph com paradas para decisão humana: ler → (gestor confirma) → otimizar → verificar →
> comparar → justificar → (gestor aprova) → publicar. O modelo de linguagem lê arquivos, conversa e explica, mas nunca calcula
> escala, hora ou custo: quem calcula é um solver (OR-Tools CP-SAT), e um verificador independente confere cada regra antes da
> aprovação. As regras ficam num cartão de regras em dados, em três camadas (lei, convenção e política), cada uma com a cláusula de
> origem, então trocar a política ou a lei muda a escala sem mexer no código. O que foge da regra vira cartão de exceção, e quem
> decide é sempre uma pessoa. A ferramenta de publicar recusa sem aprovação (conferido em código), falha do modelo vira exceção
> visível, nunca texto inventado, e cada passo fica num rastro auditável com custo e tempo.
>
> *Medido* (escala de exemplo: 3 lojas, 60 pessoas, dados sintéticos, link público, 08/11/2026):
> - Violações de regra: 158 → 0.
> - Hora extra: 216,5 h → 0.
> - Custo da semana: R$ 33.989,15 → R$ 28.456,00, R$ 5.533,15 a menos (16,3%), pela mesma função de custo nas duas escalas.
> - A escala antiga cobria 95,7% da demanda à custa de hora extra e violação. Dentro da regra, o quadro aguenta ~80% dela (2.400 de
>   2.774,5 pessoa-hora), e o Remane mostra o tamanho do buraco.
> - Execução completa: ~61 s, com US$ 0,007 de modelo.
> - Evals sem modelo: 45 de 45 cenários executados passaram; nenhuma das 14 violações plantadas passou despercebida.
>
> *Teste:* https://remane.up.railway.app → "Testar a demo" → entrar como gestor ou como colaborador, sem senha. A conversa com
> o colaborador acontece num celular simulado dentro do próprio app.
>
> *Declarações.* Todos os dados são sintéticos, gerados pelo time. A convenção coletiva e a política da empresa são fictícias. O
> celular do colaborador é simulado, não é WhatsApp. Decisões sobre pessoas ficam sempre com humanos. Ferramentas, modelos e APIs de
> terceiros: Featherless (Qwen3.5-9B e Gemma 4 31B), OR-Tools, LangGraph, FastAPI, Next.js, SQLite e Railway. A lista completa com
> licenças está em docs/declaracao-ferramentas.md. O código foi escrito durante o evento, com apoio do Claude Code.
