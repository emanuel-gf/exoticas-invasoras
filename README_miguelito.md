
# Instalação 
Do nosso querido aplicativo

## passo a passo


- lembrar de fazer isso dentro do `TERMINAL` do VScode.

        Se voce precisa abrir o terminal, olhe no canto esquerdo superior:
        `view`-> `terminal`
        uma nova janela ira se abrir na parte central e inferior da tela.


## Primeira Vez

Caso essa seja a primeira vez abrindo o repositorio

### 1. clone o repositorio

```bash
git clone https://github.com/emanuel-gf/exoticas-invasoras.git
```


### 1.2 Criar o ambient o ambiente virtual caso ele nao exista ainda 
isso deve ser feito na raiz do projeto
```bash
uv venv 
```
### 2. Ativar o enviroment

certifique-se que existe um .venv na sua pasta do projeto

```bash
.venv/Scripts/activate ##windows

source .venv/bin/activate ##linux
```
Se tudo der certo, no terminal, deve aparecer um nome entre parentesis com o nome da pasta do projeto. Se o nome da pasta do projeto é 'exoticas-invasoras', entao no terminal vai estar como:

`(exoticas-invasoras) PS C:\Users`

### 3. Instalar as dependencias 

Depois que o environment está ativo, link as dependencias (bibliotecas em python para rodas os scripts)

Lembre-se, isso só precisa ser feito na primeira vez, ou caso, o projeto tenha sido atualizado. 

```bash
uv sync
```
Dessa forma o `uv` vai instalar todas as dependencias corretamente dentro do environment ativo.

### 4. Run the app. 
 
 primeiro é preciso ir para a pasta em que existe o arquivo chamado `app.py`. Para isso use o comand `cd`

```bash
cd app2
```
run the app.
```bash
streamlit run app.py
```
----


## Uso Recorrente

### 1. Ative o environment 

```bash
.venv/Scripts/activate #windows
```

### 2. Rode o aplicativo

- vá para a pasta que contém o aplicativo 
    ```bash
    cd app2
    ```
- RUN
```bash
streamlit run app.py
```

### Atualize o projeto 

Para *atualizar* o repositorio com novas integrações, faça

```bash
git pull 
```

Se voce for <span style="color:red">NEGADO </span>, é devido ao fato de que o repositório foi alterado, portanto, digite no terminal de comando: 

```bash
git restore . 
```

e depois tente novamente: `git pull`

----

## Em caso de Erro:

`EM CASO DE ERRO DE DEPENDENCIA` (Windows) – Instalar Fiona com GDAL incluso

Usuários Windows podem ter erros ao instalar o `fiona` via `uv sync` porque o Windows não provê a biblioteca nativa do GDAL. Para resolver isso, instalamos manualmente o wheel oficial que já contém o GDAL.

Execute no terminal

```bash
$WHEEL_URL = "https://github.com/Toblerity/Fiona/releases/download/1.10.1/fiona-1.10.1-cp311-cp311-win_amd64.whl"
```
Baixar o arquivo

```BASH
Invoke-WebRequest -Uri $WHEEL_URL -OutFile "fiona-1.10.1-cp311-cp311-win_amd64.whl"
```

Desinstalamos a versao antiga

```bash
uv pip uninstall fiona
```

Instalamos a versao nova

```bash
uv pip install fiona-1.10.1-cp311-cp311-win_amd64.whl
```

