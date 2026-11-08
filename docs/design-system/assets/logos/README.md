# Logos

Última atualização: 2026-11-08 10:25 ([DEC-057](../../../decisoes.md): a logo da Remane volta à grade; o rosto com óculos é do Pat).

Há **duas artes**, e não se misturam:

- **Remane (a marca):** a grade da semana com um bloco remanejado. Quadrados em ink #17181A, bloco em accent #2BD48A.
- **Pat (o agente):** o rosto com óculos redondos e bigode, em quadrado accent. Aparece nos estados do agente, não no lugar da logo.

## Remane

- **remane-simbolo.svg**: o símbolo sobre fundos claros. Quadrados em ink #17181A, bloco remanejado em accent #2BD48A.
- **remane-simbolo-negativo.svg**: sobre fundos escuros. Quadrados brancos, bloco em accent.
- **remane-icone-app.svg**: ícone de app e favicon (fundo ink, cantos de 120/512). O favicon é `web/app/icon.svg`.

O nome "remane" não é um arquivo: escreva em Geist 500, minúsculas, tracking -0.06em, à direita do símbolo, com altura de x
próxima da altura de um quadrado. Espaço livre mínimo em volta do conjunto: a largura de um quadrado. Não gire, não recolora
os oito quadrados e não troque a cor do bloco remanejado. O código está em `web/components/Logo.tsx`.

## Pat

- **pat-rosto-original.png**: arte entregue pelo time (antes `remane-logo-original.png`), raster 1310 x 1200 com fundo branco.
  Referência, não use direto na interface.
- **remane-avatar-whatsapp.svg**: foto de perfil do agente no WhatsApp: círculo accent com óculos, olhos e bigode a 85%. O
  nome do arquivo ficou como estava; a arte é do Pat. `[PROPOSTA]`: confirmar com o time se o avatar deve ser o Pat (como
  está) ou a grade.
- **pat-estados.svg**: folha estática dos 5 estados do Pat (parado, trabalhando, digitando, resolveu, exceção). O componente
  vivo é `web/components/Pat.tsx`; a regra dos estados está em `web/lib/pat.ts`. Só o olhar muda (pupilas, olhos fechados em
  arco, sobrancelhas no "trabalhando"); `warning` só no estado de exceção. Não recolora o verde nem os traços, não tire os
  óculos nem o bigode.

A geometria do rosto (centros das lentes, raio do aro, caminho do bigode) mora em `FACE`, `Glasses` e `Mustache` de
`web/components/PatFace.tsx`; os SVGs do Pat usam os mesmos números.
