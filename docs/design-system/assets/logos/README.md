# Logos

Última atualização: 2026-11-08 (logo novo, [DEC-056](../../../decisoes.md)).

O símbolo é o **rosto do Pat**: quadrado accent #2BD48A com cantos arredondados (rx 19 em 64), óculos redondos, olhos e
bigode em ink #17181A. A fonte é `remane-logo-original.png` (arte entregue pelo time); os SVGs abaixo são a vetorização dela,
com o verde trocado pelo token `accent` (no PNG ele sai #21E491).

- **remane-logo-original.png**: arte original, raster 1310 x 1200 com fundo branco. Referência, não use direto na interface.
- **remane-simbolo.svg**: o símbolo, viewBox 64 x 64. Serve sobre fundo claro e escuro (o quadrado verde já separa do fundo).
- **remane-simbolo-negativo.svg**: mantido pelo nome; hoje é a mesma arte do `remane-simbolo.svg`.
- **remane-icone-app.svg**: ícone de app; mesma arte, que já tem forma de ícone. O favicon (`web/app/icon.svg`) é igual.
- **remane-avatar-whatsapp.svg**: foto de perfil do agente no WhatsApp: círculo accent com óculos, olhos e bigode a 85%.
- **pat-estados.svg**: folha estática dos 5 estados do Pat (parado, trabalhando, digitando, resolveu, exceção). O componente
  vivo é `web/components/Pat.tsx`; a regra dos estados está em `web/lib/pat.ts`. O Pat é o mesmo rosto do logo: só o olhar
  muda (pupilas, olhos fechados em arco, sobrancelhas no "trabalhando"); `warning` só no estado de exceção.

O nome "remane" não é um arquivo: escreva em Geist 500, minúsculas, tracking -0.06em, à direita do símbolo. Espaço livre mínimo
em volta do conjunto: um quarto da largura do símbolo. Não gire, não recolora o verde nem os traços, não tire os óculos nem o
bigode.

A geometria (centros das lentes, raio do aro, caminho do bigode) mora em `FACE`, `Glasses` e `Mustache` de
`web/components/Logo.tsx`; os SVGs estáticos usam os mesmos números.
