# Logo

Última atualização: 2026-11-08 (logo novo, [DEC-056](../../../decisoes.md)).

Símbolo (o rosto do Pat: quadrado accent com óculos redondos e bigode), seguido do nome "remane" em minúsculas.

- Versão animada (o olhar vai para a esquerda, para a direita e volta, em loop de 6s, e pisca a cada 5s) só no topo da landing
  e na tela de entrada. Em todo o resto, a versão parada, olhando em frente.
- Mesma arte sobre fundo claro e escuro. Não recolora.
- Tamanho mínimo do símbolo: 20px de largura (abaixo disso os óculos viram um traço).

O código de verdade está em `web/components/Logo.tsx`: `Logo` (símbolo + nome), `LogoMark` (só o símbolo) e as peças
`FACE`, `Glasses` e `Mustache`, que o Pat reaproveita.

```tsx
<Logo animated size={30} />   // topo da landing
<Logo size={28} />            // cabeçalho da plataforma
<LogoMark size={20} />        // só o símbolo
```

A animação usa as classes `logo-look` e `pat-blink` de `web/app/globals.css`; com `prefers-reduced-motion` tudo para.
