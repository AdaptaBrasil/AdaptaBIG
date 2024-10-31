import xml.etree.ElementTree as ET
import urllib.request, json
import os

url_base = 'https://sistema.adaptabrasil.mcti.gov.br'

recorte = 'BR'

resolucao = 'municipio'

schema = 'adaptabrasil'

# Definindo namespaces
namespaces = {
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'gco': 'http://www.isotc211.org/2005/gco'
}

# Register namespaces
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)
    
# Função para obter a URL de download a partir da API do AdaptaBrasil.
# parametro = api_url: URL da API que retorna o JSON com o campo 'location'.
# return = URL de download contida no campo 'location', ou uma mensagem de erro.
def get_location_url(api_url):        
    try:
        # Fazendo a requisição
        with urllib.request.urlopen(api_url) as response:
            # Verifica se a requisição foi bem-sucedida
            if response.status == 200:
                json_response = json.loads(response.read().decode())
                location_url = json_response.get('location')
                
                # Verifica se a chave 'location' está presente no JSON
                if location_url:
                    return location_url
                else:
                    return "Chave 'location' não encontrada no JSON."
            else:
                return f"Falha na requisição: {response.status}"
    
    except Exception as e:
        return f"Ocorreu um erro: {str(e)}"
        
# Remove todas as ocorrências de <br> do texto fornecido.
# Args: complete_description (str): O texto completo contendo as quebras de linha.
# Returns: str: O texto formatado sem as ocorrências de <br>.     
def remover_quebras(complete_description):      
    return complete_description.replace("<br>", " ")

def getScenarios(dict_scenarios: dict)->str:
    scenarios = ''
    for scenario in dict_scenarios:
        scenarios += f"{scenario['label']} "
    return scenarios

def update_xml_indicator_with_data(xml_template, indicador: list, years: list):
    tree = ET.ElementTree(ET.fromstring(xml_template))
    root = tree.getroot()

    # Adicionando valor para o "UUID = Identificador de metadados"
    file_identifier_elem = root.find('.//gmd:fileIdentifier/gco:CharacterString', namespaces)
    if file_identifier_elem is not None:
        file_identifier_elem.text = f"{schema}{indicador['id']}"

    # Adicionando valor para o "Título"
    title = root.find('.//gmd:title/gco:CharacterString', namespaces)
    if title is not None:
        title.text = indicador.get('title', '')

    # Adicionando valor para "Resumo"
    abstract = root.find('.//gmd:abstract/gco:CharacterString', namespaces)
    if abstract is not None:
        abstract.text = remover_quebras(indicador.get('complete_description', ''))

    url_show_map_on_the_site = f"{url_base}/{indicador['id']}/1/{years[0]}/null/{recorte}/" \
                               f"{resolucao}"

    # Adicionando valor para "Overview (URL da imagem)"
    overview = root.find('.//gmd:MD_BrowseGraphic/gmd:fileName/gco:CharacterString', namespaces)
    if overview is not None:
        overview.text = url_show_map_on_the_site

    # Adicionando valor para "Palavras-chave"
    """keywords = root.findall('.//gmd:keyword/gco:CharacterString', namespaces)
    for i, keyword in enumerate(keywords):
        key = f'keyword_{i+1}'
        keyword.text = indicador.get(key, '')"""        
        
    # Adicionando valor para "Recursos Online" e "Descrição do recurso online"
    # Identificar o protocolo para diferenciar os recursos
    online_resources = root.findall('.//gmd:CI_OnlineResource', namespaces)
    for i, resource in enumerate(online_resources):
        
        protocol = resource.find('.//gmd:protocol/gco:CharacterString', namespaces)

        # Verifica se é o recurso padrão ou o recurso de download
        if protocol is not None and protocol.text == 'WWW:LINK-1.0-http--link':
            linkage = resource.find('.//gmd:linkage/gmd:URL', namespaces)
            if linkage is not None:
                linkage.text = url_show_map_on_the_site
            description = resource.find('.//gmd:description/gco:CharacterString', namespaces)
            if description is not None:
                description.text = indicador.get('simple_description', '')
        elif protocol is not None and protocol.text == 'WWW:DOWNLOAD-1.0-http--download':
            linkage = resource.find('.//gmd:linkage/gmd:URL', namespaces)
            if linkage is not None:                
                linkage.text = get_location_url(f'{url_base}/api/geometria/data/{indicador["id"]}/BR/null/2015/municipio/SHPz')
            name = resource.find('.//gmd:name/gco:CharacterString', namespaces)
            if name is not None:
                name.text = 'Download do arquivo SHP dos dados'
        elif protocol is not None and protocol.text == 'WWW:LINK-2.0-http--link':
            linkage = resource.find('.//gmd:linkage/gmd:URL', namespaces)
            if linkage is not None:                
                linkage.text = f'{url_base}/api/mapa-dados/BR/municipio/{indicador["id"]}/2015/null'
            name = resource.find('.//gmd:name/gco:CharacterString', namespaces)
            if name is not None:
                name.text = 'Exibe a tela de um determinado indicador' 
        
    return tree

# Dados AdaptaBrasil
url_hierarchy = 'https://sistema.adaptabrasil.mcti.gov.br/api/hierarquia/adaptabrasil'

if __name__ == '__main__':
    url = urllib.request.urlopen(url_hierarchy)
    indicadores = json.load(url)

    # Caminho para Template XML ISO19115/19139
    with open('input.xml', 'r', encoding='utf-8') as file:
        xml_template = file.read()

    # Diretório para salvar os arquivos XML de saída
    output_dir = 'output_xml_files'
    os.makedirs(output_dir, exist_ok=True)

# Gera arquivos XML para cada registro
# for i, record in enumerate(exemplo_dados, start=1):
#     tree = update_xml_with_data(xml_template, record)
#     output_file = os.path.join(output_dir, f'record_{i}.xml')
#     tree.write(output_file, encoding='UTF-8', xml_declaration=True)
num_arquivos_gerados = 0  # Contador para arquivos gerados

for i, indicador in enumerate(indicadores):
    if indicador['level'] < 2:
        continue  # Pula se o nível for menor que 2
    
    years = None
    if indicador['years'] is None:
        pass
    elif isinstance(indicador['years'], list):
        years = indicador['years']
    else:
        years = indicador['years'].split(',')
    
    # Atualizando o XML com os dados
    tree = update_xml_indicator_with_data(xml_template, indicador, years)
    
    # Salvando o arquivo XML
    output_file = os.path.join(output_dir, f"{indicador['title']}record_{i}.xml")
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    
    num_arquivos_gerados += 1  # Incrementa o contador para cada arquivo gerado
    
    # Limite de 20 arquivos gerados
    if num_arquivos_gerados >= 20:
        break        

# Imprimindo a quantidade de arquivos gerados
print(f'{num_arquivos_gerados} arquivos XML foram gerados em {output_dir}')
