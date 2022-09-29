from datetime import date
from pathlib import Path
from sqlalchemy import create_engine
import bs4 as bs
import ftplib
import gzip
import os
import pandas as pd
import psycopg2
import re
import sys
import time
import urllib.request
import wget
import zipfile

#%%
# Ler arquivo de configuração de ambiente # https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1
def getEnv(env):
    return os.getenv(env)

dados_rf = 'http://200.152.38.155/CNPJ/'

#%%
# Read details from ".env" file:
try:
    output_files = getEnv('OUTPUT_FILES_PATH')
    extracted_files = getEnv('EXTRACTED_FILES_PATH')
    print('Diretórios definidos: \n' +
          'output_files: ' + str(output_files)  + '\n' +
          'extracted_files: ' + str(extracted_files))
except:
    pass
    print('Erro na definição dos diretórios, verifique o arquivo ".env" ou o local informado do seu arquivo de configuração.')

#%%
raw_html = urllib.request.urlopen(dados_rf)
raw_html = raw_html.read()

# Formatar página e converter em string
page_items = bs.BeautifulSoup(raw_html, 'lxml')
html_str = str(page_items)

# Obter arquivos
Files = []
text = '.zip'
for m in re.finditer(text, html_str):
    i_start = m.start()-40
    i_end = m.end()
    i_loc = html_str[i_start:i_end].find('href=')+6
    Files.append(html_str[i_start+i_loc:i_end])

# Correcao do nome dos arquivos devido a mudanca na estrutura do HTML da pagina - 31/07/22 - Aphonso Rafael
Files_clean = []
for i in range(len(Files)):
    if not Files[i].find('.zip">') > -1:
        Files_clean.append(Files[i])

try:
    del Files
except:
    pass

Files = Files_clean

print('Arquivos que serão baixados:')
i_f = 0
for f in Files:
    i_f += 1
    print(str(i_f) + ' - ' + f)

#%%
########################################################################################################################
## DOWNLOAD ############################################################################################################
########################################################################################################################
# Create this bar_progress method which is invoked automatically from wget:
def bar_progress(current, total, width=80):
  progress_message = "Downloading: %d%% [%d / %d] bytes - " % (current / total * 100, current, total)
  # Don't use print() as it will print in new line every time.
  sys.stdout.write("\r" + progress_message)
  sys.stdout.flush()

#%%
# Download arquivos ################################################################################################################################
i_l = 0
for l in Files:
    # Download dos arquivos
    i_l += 1
    print('Baixando arquivo:')
    print(str(i_l) + ' - ' + l)
    url = dados_rf+l
    wget.download(url, out=output_files, bar=bar_progress)

#%%
# Download layout:
Layout = 'https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/consultas/arquivos/NOVOLAYOUTDOSDADOSABERTOSDOCNPJ.pdf'
print('Baixando layout:')
wget.download(Layout, out=output_files, bar=bar_progress)

####################################################################################################################################################
#%%
# Creating directory to store the extracted files:
if not os.path.exists(extracted_files):
    os.mkdir(extracted_files)

#%%
# Extracting files:
i_l = 0
for l in Files:
    try:
        i_l += 1
        print('Descompactando arquivo:')
        print(str(i_l) + ' - ' + l)
        with zipfile.ZipFile(output_files + '\\' + l, 'r') as zip_ref:
            zip_ref.extractall(extracted_files)
    except:
        pass

#%%
########################################################################################################################
## LER E INSERIR DADOS #################################################################################################
########################################################################################################################
insert_start = time.time()

# Files:
Items = [name for name in os.listdir(extracted_files) if name.endswith('')]

# Separar arquivos:
arquivos_empresa = []
arquivos_estabelecimento = []
arquivos_socios = []
arquivos_simples = []
arquivos_cnae = []
arquivos_moti = []
arquivos_munic = []
arquivos_natju = []
arquivos_pais = []
arquivos_quals = []
for i in range(len(Items)):
    if Items[i].find('EMPRE') > -1:
        arquivos_empresa.append(Items[i])
    elif Items[i].find('ESTABELE') > -1:
        arquivos_estabelecimento.append(Items[i])
    elif Items[i].find('SOCIO') > -1:
        arquivos_socios.append(Items[i])
    elif Items[i].find('SIMPLES') > -1:
        arquivos_simples.append(Items[i])
    elif Items[i].find('CNAE') > -1:
        arquivos_cnae.append(Items[i])
    elif Items[i].find('MOTI') > -1:
        arquivos_moti.append(Items[i])
    elif Items[i].find('MUNIC') > -1:
        arquivos_munic.append(Items[i])
    elif Items[i].find('NATJU') > -1:
        arquivos_natju.append(Items[i])
    elif Items[i].find('PAIS') > -1:
        arquivos_pais.append(Items[i])
    elif Items[i].find('QUALS') > -1:
        arquivos_quals.append(Items[i])
    else:
        pass

#%%
# Conectar no banco de dados:
# Dados da conexão com o BD
user=getEnv('DB_USER')
passw=getEnv('DB_PASSWORD')
host=getEnv('DB_HOST')
port=getEnv('DB_PORT')
database=getEnv('DB_NAME')

# Conectar:
engine = create_engine('postgresql://'+user+':'+passw+'@'+host+':'+port+'/'+database)
conn = psycopg2.connect('dbname='+database+' '+'user='+user+' '+'host='+host+' '+'password='+passw)
cur = conn.cursor()

#%%
# Arquivos de empresa:
empresa_insert_start = time.time()
print("""
#######################
## Arquivos de EMPRESA:
#######################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "empresa";')
conn.commit()

for e in range(0, len(arquivos_empresa)):
    print('Trabalhando no arquivo: '+arquivos_empresa[e]+' [...]')
    try:
        del empresa
    except:
        pass

    empresa = pd.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6])
    empresa_dtypes = {0: 'object', 1: 'object', 2: 'object', 3: 'object', 4: 'object', 5: 'object', 6: 'object'}
    extracted_file_path = Path(f'{extracted_files}/{arquivos_empresa[e]}')

    empresa = pd.read_csv(filepath_or_buffer=extracted_file_path,
                          sep=';',
                          #nrows=100,
                          skiprows=0,
                          header=None,
                          dtype=empresa_dtypes)

    # Tratamento do arquivo antes de inserir na base:
    empresa = empresa.reset_index()
    del empresa['index']

    # Renomear colunas
    empresa.columns = ['cnpj_basico', 'razao_social', 'natureza_juridica', 'qualificacao_responsavel', 'capital_social', 'porte_empresa', 'ente_federativo_responsavel']

    # Replace "," por "."
    empresa['capital_social'] = empresa['capital_social'].apply(lambda x: x.replace(',','.'))
    empresa['capital_social'] = empresa['capital_social'].astype(float)

    # Gravar dados no banco:
    # Empresa
    empresa.to_sql(name='empresa', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_empresa[e] + ' inserido com sucesso no banco de dados!')

try:
    del empresa
except:
    pass
print('Arquivos de empresa finalizados!')
empresa_insert_end = time.time()
empresa_Tempo_insert = round((empresa_insert_end - empresa_insert_start))
print('Tempo de execução do processo de empresa (em segundos): ' + str(empresa_Tempo_insert))

#%%
# Arquivos de estabelecimento:
estabelecimento_insert_start = time.time()
print("""
############################### 
## Arquivos de ESTABELECIMENTO:
###############################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "estabelecimento";')
conn.commit()

for e in range(0, len(arquivos_estabelecimento)):
    print('Trabalhando no arquivo: '+arquivos_estabelecimento[e]+' [...]')
    try:
        del estabelecimento
    except:
        pass

    estabelecimento = pd.DataFrame(columns=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28])
    extracted_file_path = Path(f'{extracted_files}/{arquivos_estabelecimento[e]}')

    estabelecimento = pd.read_csv(filepath_or_buffer=extracted_file_path,
                          sep=';',
                          #nrows=100,
                          skiprows=0,
                          header=None,
                          dtype='object')

    # Tratamento do arquivo antes de inserir na base:
    estabelecimento = estabelecimento.reset_index()
    del estabelecimento['index']

    # Renomear colunas
    estabelecimento.columns = ['cnpj_basico',
                               'cnpj_ordem',
                               'cnpj_dv',
                               'identificador_matriz_filial',
                               'nome_fantasia',
                               'situacao_cadastral',
                               'data_situacao_cadastral',
                               'motivo_situacao_cadastral',
                               'nome_cidade_exterior',
                               'pais',
                               'data_inicio_atividade',
                               'cnae_fiscal_principal',
                               'cnae_fiscal_secundaria',
                               'tipo_logradouro',
                               'logradouro',
                               'numero',
                               'complemento',
                               'bairro',
                               'cep',
                               'uf',
                               'municipio',
                               'ddd_1',
                               'telefone_1',
                               'ddd_2',
                               'telefone_2',
                               'ddd_fax',
                               'fax',
                               'correio_eletronico',
                               'situacao_especial',
                               'data_situacao_especial']

    # Gravar dados no banco:
    # estabelecimento
    estabelecimento.to_sql(name='estabelecimento', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_estabelecimento[e] + ' inserido com sucesso no banco de dados!')

try:
    del estabelecimento
except:
    pass
print('Arquivos de estabelecimento finalizados!')
estabelecimento_insert_end = time.time()
estabelecimento_Tempo_insert = round((estabelecimento_insert_end - estabelecimento_insert_start))
print('Tempo de execução do processo de estabelecimento (em segundos): ' + str(estabelecimento_Tempo_insert))

#%%
# Arquivos de socios:
socios_insert_start = time.time()
print("""
######################
## Arquivos de SOCIOS:
######################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "socios";')
conn.commit()

for e in range(0, len(arquivos_socios)):
    print('Trabalhando no arquivo: '+arquivos_socios[e]+' [...]')
    try:
        del socios
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_socios[e]}')
    socios = pd.DataFrame(columns=[1,2,3,4,5,6,7,8,9,10,11])
    socios = pd.read_csv(filepath_or_buffer=extracted_file_path,
                          sep=';',
                          #nrows=100,
                          skiprows=0,
                          header=None,
                          dtype='object')

    # Tratamento do arquivo antes de inserir na base:
    socios = socios.reset_index()
    del socios['index']

    # Renomear colunas
    socios.columns = ['cnpj_basico',
                      'identificador_socio',
                      'nome_socio_razao_social',
                      'cpf_cnpj_socio',
                      'qualificacao_socio',
                      'data_entrada_sociedade',
                      'pais',
                      'representante_legal',
                      'nome_do_representante',
                      'qualificacao_representante_legal',
                      'faixa_etaria']

    # Gravar dados no banco:
    # socios
    socios.to_sql(name='socios', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_socios[e] + ' inserido com sucesso no banco de dados!')

try:
    del socios
except:
    pass
print('Arquivos de socios finalizados!')
socios_insert_end = time.time()
socios_Tempo_insert = round((socios_insert_end - socios_insert_start))
print('Tempo de execução do processo de sócios (em segundos): ' + str(socios_Tempo_insert))

#%%
# Arquivos de simples:
simples_insert_start = time.time()
print("""
################################
## Arquivos do SIMPLES NACIONAL:
################################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "simples";')
conn.commit()

for e in range(0, len(arquivos_simples)):
    print('Trabalhando no arquivo: '+arquivos_simples[e]+' [...]')
    try:
        del simples
    except:
        pass

    # Verificar tamanho do arquivo:
    print('Lendo o arquivo ' + arquivos_simples[e]+' [...]')
    extracted_file_path = Path(f'{extracted_files}/{arquivos_simples[e]}')

    simples_lenght = sum(1 for line in open(extracted_file_path, "r"))
    print('Linhas no arquivo do Simples '+ arquivos_simples[e] +': '+str(simples_lenght))

    tamanho_das_partes = 1000000 # Registros por carga
    partes = round(simples_lenght / tamanho_das_partes)
    nrows = tamanho_das_partes
    skiprows = 0

    print('Este arquivo será dividido em ' + str(partes) + ' partes para inserção no banco de dados')

    for i in range(0, partes):
        print('Iniciando a parte ' + str(i+1) + ' [...]')
        simples = pd.DataFrame(columns=[1,2,3,4,5,6])

        simples = pd.read_csv(filepath_or_buffer=extracted_file_path,
                              sep=';',
                              nrows=nrows,
                              skiprows=skiprows,
                              header=None,
                              dtype='object')

        # Tratamento do arquivo antes de inserir na base:
        simples = simples.reset_index()
        del simples['index']

        # Renomear colunas
        simples.columns = ['cnpj_basico',
                           'opcao_pelo_simples',
                           'data_opcao_simples',
                           'data_exclusao_simples',
                           'opcao_mei',
                           'data_opcao_mei',
                           'data_exclusao_mei']

        skiprows = skiprows+nrows

        # Gravar dados no banco:
        # simples
        simples.to_sql(name='simples', con=engine, if_exists='append', index=False)
        print('Arquivo ' + arquivos_simples[e] + ' inserido com sucesso no banco de dados! - Parte '+ str(i+1))

        try:
            del simples
        except:
            pass

try:
    del simples
except:
    pass

print('Arquivos do simples finalizados!')
simples_insert_end = time.time()
simples_Tempo_insert = round((simples_insert_end - simples_insert_start))
print('Tempo de execução do processo do Simples Nacional (em segundos): ' + str(simples_Tempo_insert))

#%%
# Arquivos de cnae:
cnae_insert_start = time.time()
print("""
######################
## Arquivos de cnae:
######################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "cnae";')
conn.commit()

for e in range(0, len(arquivos_cnae)):
    print('Trabalhando no arquivo: '+arquivos_cnae[e]+' [...]')
    try:
        del cnae
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_cnae[e]}')
    cnae = pd.DataFrame(columns=[1,2])
    cnae = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    cnae = cnae.reset_index()
    del cnae['index']

    # Renomear colunas
    cnae.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # cnae
    cnae.to_sql(name='cnae', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_cnae[e] + ' inserido com sucesso no banco de dados!')

try:
    del cnae
except:
    pass
print('Arquivos de cnae finalizados!')
cnae_insert_end = time.time()
cnae_Tempo_insert = round((cnae_insert_end - cnae_insert_start))
print('Tempo de execução do processo de cnae (em segundos): ' + str(cnae_Tempo_insert))

#%%
# Arquivos de moti:
moti_insert_start = time.time()
print("""
#########################################
## Arquivos de motivos da situação atual:
#########################################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "moti";')
conn.commit()

for e in range(0, len(arquivos_moti)):
    print('Trabalhando no arquivo: '+arquivos_moti[e]+' [...]')
    try:
        del moti
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_moti[e]}')
    moti = pd.DataFrame(columns=[1,2])
    moti = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    moti = moti.reset_index()
    del moti['index']

    # Renomear colunas
    moti.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # moti
    moti.to_sql(name='moti', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_moti[e] + ' inserido com sucesso no banco de dados!')

try:
    del moti
except:
    pass
print('Arquivos de moti finalizados!')
moti_insert_end = time.time()
moti_Tempo_insert = round((moti_insert_end - moti_insert_start))
print('Tempo de execução do processo de motivos da situação atual (em segundos): ' + str(moti_Tempo_insert))

#%%
# Arquivos de munic:
munic_insert_start = time.time()
print("""
##########################
## Arquivos de municípios:
##########################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "munic";')
conn.commit()

for e in range(0, len(arquivos_munic)):
    print('Trabalhando no arquivo: '+arquivos_munic[e]+' [...]')
    try:
        del munic
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_munic[e]}')
    munic = pd.DataFrame(columns=[1,2])
    munic = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    munic = munic.reset_index()
    del munic['index']

    # Renomear colunas
    munic.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # munic
    munic.to_sql(name='munic', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_munic[e] + ' inserido com sucesso no banco de dados!')

try:
    del munic
except:
    pass
print('Arquivos de munic finalizados!')
munic_insert_end = time.time()
munic_Tempo_insert = round((munic_insert_end - munic_insert_start))
print('Tempo de execução do processo de municípios (em segundos): ' + str(munic_Tempo_insert))

#%%
# Arquivos de natju:
natju_insert_start = time.time()
print("""
#################################
## Arquivos de natureza jurídica:
#################################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "natju";')
conn.commit()

for e in range(0, len(arquivos_natju)):
    print('Trabalhando no arquivo: '+arquivos_natju[e]+' [...]')
    try:
        del natju
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_natju[e]}')
    natju = pd.DataFrame(columns=[1,2])
    natju = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    natju = natju.reset_index()
    del natju['index']

    # Renomear colunas
    natju.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # natju
    natju.to_sql(name='natju', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_natju[e] + ' inserido com sucesso no banco de dados!')

try:
    del natju
except:
    pass
print('Arquivos de natju finalizados!')
natju_insert_end = time.time()
natju_Tempo_insert = round((natju_insert_end - natju_insert_start))
print('Tempo de execução do processo de natureza jurídica (em segundos): ' + str(natju_Tempo_insert))

#%%
# Arquivos de pais:
pais_insert_start = time.time()
print("""
######################
## Arquivos de país:
######################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "pais";')
conn.commit()

for e in range(0, len(arquivos_pais)):
    print('Trabalhando no arquivo: '+arquivos_pais[e]+' [...]')
    try:
        del pais
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_pais[e]}')
    pais = pd.DataFrame(columns=[1,2])
    pais = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    pais = pais.reset_index()
    del pais['index']

    # Renomear colunas
    pais.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # pais
    pais.to_sql(name='pais', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_pais[e] + ' inserido com sucesso no banco de dados!')

try:
    del pais
except:
    pass
print('Arquivos de pais finalizados!')
pais_insert_end = time.time()
pais_Tempo_insert = round((pais_insert_end - pais_insert_start))
print('Tempo de execução do processo de país (em segundos): ' + str(pais_Tempo_insert))

#%%
# Arquivos de qualificação de sócios:
quals_insert_start = time.time()
print("""
######################################
## Arquivos de qualificação de sócios:
######################################
""")

# Drop table antes do insert
cur.execute('DROP TABLE IF EXISTS "quals";')
conn.commit()

for e in range(0, len(arquivos_quals)):
    print('Trabalhando no arquivo: '+arquivos_quals[e]+' [...]')
    try:
        del quals
    except:
        pass

    extracted_file_path = Path(f'{extracted_files}/{arquivos_quals[e]}')
    quals = pd.DataFrame(columns=[1,2])
    quals = pd.read_csv(filepath_or_buffer=extracted_file_path, sep=';', skiprows=0, header=None, dtype='object', encoding='ANSI')

    # Tratamento do arquivo antes de inserir na base:
    quals = quals.reset_index()
    del quals['index']

    # Renomear colunas
    quals.columns = ['codigo', 'descricao']

    # Gravar dados no banco:
    # quals
    quals.to_sql(name='quals', con=engine, if_exists='append', index=False)
    print('Arquivo ' + arquivos_quals[e] + ' inserido com sucesso no banco de dados!')

try:
    del quals
except:
    pass
print('Arquivos de quals finalizados!')
quals_insert_end = time.time()
quals_Tempo_insert = round((quals_insert_end - quals_insert_start))
print('Tempo de execução do processo de qualificação de sócios (em segundos): ' + str(quals_Tempo_insert))

#%%
insert_end = time.time()
Tempo_insert = round((insert_end - insert_start))

print("""
#############################################
## Processo de carga dos arquivos finalizado!
#############################################
""")

print('Tempo total de execução do processo de carga (em segundos): ' + str(Tempo_insert)) # Tempo de execução do processo (em segundos): 17.770 (4hrs e 57 min)

# ###############################
# Tamanho dos arquivos:
# empresa = 45.811.638
# estabelecimento = 48.421.619
# socios = 20.426.417
# simples = 27.893.923
# ###############################

#%%
# Criar índices na base de dados:
index_start = time.time()
print("""
#######################################
## Criar índices na base de dados [...]
#######################################
""")
cur.execute("""
create index empresa_cnpj on empresa(cnpj_basico);
commit;
create index estabelecimento_cnpj on estabelecimento(cnpj_basico);
commit;
create index socios_cnpj on socios(cnpj_basico);
commit;
create index simples_cnpj on simples(cnpj_basico);
commit;
""")
conn.commit()
print("""
############################################################
## Índices criados nas tabelas, para a coluna `cnpj_basico`:
   - empresa
   - estabelecimento
   - socios
   - simples
############################################################
""")
index_end = time.time()
index_time = round(index_end - index_start)
print('Tempo para criar os índices (em segundos): ' + str(index_time))

#%%
print("""Processo 100% finalizado! Você já pode usar seus dados no BD!
 - Desenvolvido por: Aphonso Henrique do Amaral Rafael
 - Contribua com esse projeto aqui: https://github.com/aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ
""")