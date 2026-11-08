# WhatsApp real no pitch: Cloud API da Meta em modo de teste

Última atualização: 2026-11-08 02:05 · Decisão: [DEC-038](../decisoes.md)

**Para quê.** Os jurados testam o atendimento pelo **celular simulado** no link (caminho garantido, C7). O WhatsApp de verdade aparece
só no **pitch**, com os celulares do time, pelo número de teste da Cloud API oficial. A ponte não oficial (`whatsapp-web.js`) foi
abandonada: o WhatsApp recusa parear um navegador automatizado ([DEC-038](../decisoes.md)).

## 1. Na Meta (quem tem a conta Facebook; ~15 min)

Fonte: [Get Started da Cloud API](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started), lida em 08/11.

1. Registrar-se como desenvolvedor em developers.facebook.com.
2. Criar um app com o caso de uso **"Connect with customers through WhatsApp"** e escolher ou criar um portfólio de negócios.
3. **API Setup → Start using the API:** a Meta cria um número de teste. Guardar o **Phone number ID** e o **WhatsApp Business account ID**.
4. **Generate access token** (temporário, expira rápido) e, em **To**, adicionar o celular de cada pessoa do time que vai aparecer na demo.
   Mandar a mensagem de teste para confirmar.
5. **Token permanente:** Business Settings → System users → criar um usuário de sistema, atribuir o app ("Manage app") e a conta do
   WhatsApp, e gerar um token com `business_management`, `whatsapp_business_messaging` e `whatsapp_business_management`.
6. **Webhook:** no app, configurar a URL `https://escalista-converge-production.up.railway.app/api/whatsapp/webhook` com um verify token
   escolhido pelo time, e assinar o campo **`messages`**.

**A conferir na hora (a página oficial não diz):** quantos números destinatários o número de teste aceita (relatos falam em 5,
`[NÃO CONFIRMADO]`); se o app precisa sair do modo de desenvolvimento para o webhook chegar; nome de exibição do número de teste.

## 2. No Railway (variáveis do serviço, nunca no repositório)

| Variável | O quê |
|---|---|
| `WHATSAPP_TOKEN` | token permanente do usuário de sistema |
| `WHATSAPP_PHONE_NUMBER_ID` | ID do número de teste |
| `WHATSAPP_VERIFY_TOKEN` | o verify token escolhido no passo 6 |
| `WHATSAPP_APP_SECRET` | App secret do app (para validar a assinatura do webhook) |

## 3. No backend (quem faz a C7, frente do backend) `[PROPOSTA]`

No lugar do `WhatsAppBridge`, uma segunda implementação do adaptador de canal da [arquitetura, seção 10](../arquitetura.md), ao lado do `SimulatedPhone`:
`CloudApiChannel`, com os mesmos `send_message` e `on_message`.

- `GET /api/whatsapp/webhook`: responde `hub.challenge` quando `hub.verify_token` bate com `WHATSAPP_VERIFY_TOKEN`; senão, 403.
- `POST /api/whatsapp/webhook`: **valida o cabeçalho `X-Hub-Signature-256`** (HMAC-SHA256 do corpo com `WHATSAPP_APP_SECRET`) antes de
  ler qualquer coisa; responde 200 rápido e processa a mensagem fora da requisição. Mensagem de número fora do quadro: recusada e
  registrada (RF-42), como no simulador.
- Envio: `POST https://graph.facebook.com/<versão>/<WHATSAPP_PHONE_NUMBER_ID>/messages` com o token. Fora da **janela de 24 h** aberta
  pela última mensagem da pessoa, só sai mensagem de **template aprovado**; na demo, quem fala primeiro é sempre o celular do time.
- **Quadro da demo:** o celular de cada pessoa do time entra no quadro sintético como um colaborador (por exemplo, o do Pedro é o
  Patrick), para a regra de número fora do quadro continuar valendo.
- Atestado em foto chega como mídia: baixar pela Graph API e seguir o mesmo caminho do RN-06 (CID nunca em banco, log ou trace).

## 4. Roteiro do pitch (rascunho)

No palco, o Pedro manda do próprio celular, como Patrick: "Bom dia, não vou conseguir ir hoje" + foto do atestado sintético. O telão
mostra a escala no link público; o agente responde no WhatsApp, oferece o turno a um colega (outro celular do time), o colega aceita e
a grade muda na tela. Se a rede ou a Meta falharem, o mesmo fluxo roda no celular simulado.
