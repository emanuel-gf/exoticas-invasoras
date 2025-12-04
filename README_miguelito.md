
## passo a passo

- lembrar de fazer isso dentro do `TERMINAL`

1. clonar o repositorio

```bash
git clone https://github.com/emanuel-gf/exoticas-invasoras.git
```

Caso o repositorio ja exista, e voce precise atualizar o repositorio com novas integrações, faça

```bash
git pull 
```

2. Ativar o enviroment

certifique-se que existe um .venv na sua pasta do projeto

```bash
.venv/bin/activate ##windows

source .venv/bin/activate ##linux
```
Se tudo der certo, no terminal, deve aparecer um nome entre parentesis com o nome da pasta do projeto. Se o nome da pasta do projeto é carijos, entao no terminal vai estar como:

`(carijos)your_username@windows`

3. Instalar as dependencias

Depois que o environment está ativo, link as dependencias (bibliotecas em python para rodas os scripts)

```bash
uv sync
```
Dessa forma o `uv` vai instalar todas as dependencias corretamente dentro do environment ativo.

4. Run the app. 
 
 primeiro é preciso ir para a pasta em que existe o arquivo chamado `app.py`. Para isso use o comand `cd`

```bash
cd app2
```
run the app.
```bash
streamlit run app.py
```