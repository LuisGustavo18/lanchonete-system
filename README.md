# Sistema de lanchonete

## Executar no Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings_local
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.settings_local
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.settings_local
```

Acesse http://127.0.0.1:8000/ e o administrativo em http://127.0.0.1:8000/admin/.
No administrativo, cadastre uma lanchonete e um membro vinculando seu usuário
à lanchonete com o papel Dono. Esse vínculo é necessário para acessar o painel.

Depois da instalação, o comando abaixo inicia o servidor:

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
```

A configuração `config.settings_local` usa SQLite (`db.sqlite3`) para testes locais
e envia emails para o console. A configuração original de PostgreSQL continua
em `config.settings`.

As credenciais são lidas das variáveis `DJANGO_SECRET_KEY` e `POSTGRES_PASSWORD`.
Você pode defini-las no ambiente ou em `.env` na raiz do projeto; variáveis já
definidas no ambiente têm prioridade. Use `.env.example` como referência.
O `.env`, banco de dados e documento privado de decisões ficam fora do Git.
Sem uma chave definida, o sistema usa uma chave pública apenas para desenvolvimento
local. Para publicar o sistema, configure uma chave secreta própria.

As dependências usam Django 5.2 LTS, compatível com Python 3.12.
Para interromper um servidor iniciado no terminal, pressione Ctrl+C.

## Interface

As telas usam templates HTML do Django, Tailwind CSS compilado e HTMX servido
localmente. Não precisam de CDN para funcionar.

Para recompilar o CSS depois de alterar templates ou estilos:

```powershell
npm ci
npm run build:css
```

Durante a edição, use `npm run watch:css` para recompilar automaticamente.
O CSS de entrada fica em `core/static/core/css/input.css`.
O painel atualiza os pedidos a cada 30 segundos. A busca, os filtros e as ações
de disponibilidade de produtos usam HTMX. Formulários comuns continuam funcionando
sem JavaScript.

## Cardápio público

Abra http://127.0.0.1:8000/cardapio/ para fazer pedidos sem login.
Cada lanchonete tem seu endereço próprio: `/cardapio/ID/`.
Cadastre categorias e produtos no administrativo para preencher o cardápio.
Produtos inativos aparecem como indisponíveis; categorias inativas ficam ocultas.
O carrinho é salvo na sessão do navegador e separado por lanchonete.
Pedidos enviados aparecem como Novos no painel da equipe.
O pagamento é registrado como preferência, sem processamento de cobrança online.
Configure a taxa fixa de entrega em Administração → Lanchonetes. O cliente vê o
total com essa taxa antes de enviar; retirada tem taxa zero.
Cadastre a chave Pix e o favorecido na mesma tela para habilitar Pix.
Dinheiro e cartão são recebidos na entrega/retirada; o caixa registra o recebimento
no painel. Dono/gerente pode corrigir com motivo, mantendo o histórico.
O cliente pode optar por lembrar nome, telefone e endereço neste navegador por
até 90 dias, ou apagar a cópia salva a qualquer momento. Essa opção não cria conta.
