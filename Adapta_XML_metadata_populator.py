import xml.etree.ElementTree as ET
import urllib.request, json
import os
import re
import requests
from datetime import datetime

url_base = 'https://sistema.adaptabrasil.mcti.gov.br'
recorte = 'BR'
resolucao_default = 'municipio'
schema = 'adaptabrasil'

url_hierarchy = 'https://sistema.adaptabrasil.mcti.gov.br/api/hierarquia/adaptabrasil'
hierarchy = requests.get(url_hierarchy).json()

namespaces = {
    'gmd': 'http://www.isotc211.org/2005/gmd',
    'gco': 'http://www.isotc211.org/2005/gco'
}
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)


# Realiza uma requisição HTTP para a URL fornecida e retorna o valor do campo 'location' da resposta JSON.
# Parâmetros: api_url (str): URL da API a ser consultada.
# Retorna: str: Valor do campo 'location' se presente na resposta; caso contrário, retorna string vazia.
def get_location_url(api_url):
    try:
        with urllib.request.urlopen(api_url) as response:
            if response.status == 200:
                json_response = json.loads(response.read().decode())
                return json_response.get('location', '')
    except Exception:
        return ''
    return ''


# Remove quebras de linha em HTML (tags <br>) substituindo por espaço simples.
# Parâmetros: texto (str): Texto de entrada com possíveis tags <br>.
# Retorna: str: Texto com as tags <br> substituídas por espaço.
def remover_quebras(texto):
    return texto.replace("<br>", " ")


# Constrói uma string representando a hierarquia de um indicador a partir de seus pais (níveis 1 e 2).
# Parâmetros: indicadores (list): Lista de dicionários contendo os indicadores e suas relações hierárquicas.
#             indicator_id (int): ID do indicador para o qual se deseja obter a hierarquia.
# Retorna: str: Título hierárquico no formato "AdaptaBrasil: Nível 1 - Nível 2 - Indicador".
def get_hierarchy_titles(indicadores, indicator_id):
    indicadores_dict = {ind['id']: ind for ind in indicadores}
    nomes = []
    current_id = indicator_id
    while current_id:
        indicador = indicadores_dict.get(current_id)
        if indicador is None:
            break
        if indicador['level'] <= 2 and indicador['name'] not in nomes:
            nomes.insert(0, indicador['name'])
        current_id = int(indicador['indicator_id_master']) if indicador.get('indicator_id_master') else None
    original_indicator = indicadores_dict.get(indicator_id)
    if original_indicator and original_indicator['name'] not in nomes:
        nomes.append(original_indicator['name'])
    return f"AdaptaBrasil: {' - '.join(nomes)}"


# Retorna a URL da imagem de overview associada ao indicador de nível 1.
# Parâmetros: indicadores: lista de dicionários com todos os indicadores da API.
#             indicator_id: ID do indicador atual.
# Retorna: URL da imagem (string) se encontrada, ou string vazia se não existir.
def get_overview_url(indicadores, indicator_id):
    indicadores_dict = {ind['id']: ind for ind in indicadores}
    current_id = indicator_id
    while current_id:
        indicador = indicadores_dict.get(current_id)
        if indicador is None:
            break
        if indicador['level'] == 1:
            return indicador.get('imageurl', '')
        current_id = int(indicador.get('indicator_id_master', 0)) if indicador.get('indicator_id_master') else None
    return ''


# Obtém o valor padrão de resolução associado ao indicador de nível 1, subindo pela hierarquia se necessário.
# Parâmetros: indicadores_dict (dict): Dicionário onde as chaves são IDs de indicadores e os valores são os próprios indicadores.
#             indicador (dict): Indicador a partir do qual a busca deve começar.
# Retorna: str: Valor do 'resolution_id' padrão definido na estrutura de menu do indicador de nível 1.
# Se não for encontrado, retorna o valor padrão global `resolucao_default`.
def get_resolution_from_level1(indicadores_dict, indicador):
    current_id = indicador['id']
    while current_id:
        current = indicadores_dict.get(current_id)
        if current and current['level'] == 1:
            try:
                return current["menu_structure"]["defaultclippingresolution"]["resolution_id"]
            except Exception:
                return resolucao_default
        current_id = int(current.get('indicator_id_master', 0)) if current.get('indicator_id_master') else None
    return resolucao_default


# Extrai e organiza as informações de um indicador do AdaptaBrasil para preenchimento de um metadado XML.
# Gera campos como título hierárquico, resumo, links para página do indicador e downloads SHP. 
# A resolução espacial é determinada a partir do nível 1 do indicador.
# Parâmetros: indicador (dict): Dicionário com os dados do indicador.
# Retorna: dict: Dicionário contendo os metadados organizados.
def extrair_dados_para_xml(indicador):
    indicadores_dict = {ind['id']: ind for ind in hierarchy}

    anos_raw = indicador.get('years')
    if not anos_raw:
        anos = ['0']  # usar '0' como padrão, ano presente
    elif isinstance(anos_raw, str):
        anos = [y.strip() for y in anos_raw.split(',') if y.strip().isdigit()]
    else:
        anos = [str(y) for y in anos_raw if str(y).isdigit()]

    anos = sorted(set(anos))
    ano_atual = datetime.now().year
    anos_futuros = [a for a in anos if int(a) >= ano_atual or a in ['2030', '2050']]
    anos_presente = [a for a in anos if int(a) < ano_atual or a == '0']
    ano_presente = max(anos_presente or ['0'], key=int)

    resolucao = get_resolution_from_level1(indicadores_dict, indicador)

    if indicador['level'] > 1:
        link_pagina = f"{url_base}/{indicador['id']}/1/{ano_presente}/null/{recorte}/{resolucao}/"
    else:
        link_pagina = url_base

    dados = {
        "file_identifier": f"{schema}{indicador['id']}",
        "parent_identifier": f"{schema}{indicador['indicator_id_master']}",
        "titulo": get_hierarchy_titles(hierarchy, indicador['id']),
        "resumo": remover_quebras(indicador.get('complete_description', '')),
        "overview_url": get_overview_url(hierarchy, indicador['id']),
        "simple_description": indicador.get('simple_description', ''),
        "link_dados_api": [],
        "link_pagina_indicador": link_pagina
    }

    # Sempre inclui o link da plataforma (item 4)
    dados["link_dados_api"].append({
        "url": dados["link_pagina_indicador"],
        "protocol": "WWW:LINK-PLATAFORMA.0-http--link",
        "name": "Página do indicador na plataforma AdaptaBrasil",
        "description": "Informações descritivas e estruturais sobre o indicador na plataforma"
    })

    # Link do visualizador só para ano presente (0) e se houver dados (RETIRADO)
    """ano_presente_str = str(ano_presente)
    url_visualizador_presente = f"{url_base}/api/mapa-dados/{recorte}/{resolucao}/{indicador['id']}/{ano_presente_str}/null"
    try:
        with urllib.request.urlopen(url_visualizador_presente) as response:
            if response.status == 200:
                dados["link_dados_api"].append({
                    "url": url_visualizador_presente,
                    "protocol": f"WWW:LINK-VISUALIZACAO-{ano_presente_str}.0-http--link",
                    "name": f"Visualizar indicador no painel AdaptaBrasil - ano presente" if ano_presente_str == '0' else f"Visualizar indicador no painel AdaptaBrasil - {ano_presente_str}",
                    "description": f"Mapa interativo do indicador no ano {'presente' if ano_presente_str == '0' else ano_presente_str}, na plataforma AdaptaBrasil"
                })
    except:
        print(f"⚠️ Visualização indisponível para o ano presente ({ano_presente_str}) - {indicador['id']}")"""

    # Links de download para anos presentes (inclui ano 0)
    i = 1
    for ano in anos_presente:
        url_api = f'{url_base}/api/geometria/data/{indicador["id"]}/{recorte}/null/{ano}/{resolucao}/SHPz/adaptabrasil'
        download_url = get_location_url(url_api)
        if download_url.startswith('http'):
            nome_ano = "ano presente" if ano == '0' else ano
            print(f"✔️ Ano presente encontrado: {ano} - {indicador['id']}")
            dados["link_dados_api"].append({
                "url": download_url,
                "protocol": f"WWW:DOWNLOAD-{i}.0-http--download",
                "name": f"Download SHP - {recorte}, {nome_ano}, resolução {resolucao}",
                "description": f"Shapefile dos dados para {recorte}, {nome_ano}, {resolucao}"
            })
            i += 1
        else:
            print(f"❌ Nenhum dado encontrado para {ano} - {indicador['id']}")

    # Downloads para anos futuros (exclui 2030 e 2050 dos visualizadores, mas mantém downloads)
    cenarios_raw = indicador.get('scenarios') or []
    cenarios_futuros = [c['value'] for c in cenarios_raw if 'value' in c]
    cenarios_dict = {1: 'otimista', 2: 'pessimista'}

    for ano in anos_futuros:
        for cenario in cenarios_futuros:
            url_api = f'{url_base}/api/geometria/data/{indicador["id"]}/{recorte}/{cenario}/{ano}/{resolucao}/SHPz/adaptabrasil'
            download_url = get_location_url(url_api)
            if download_url.startswith('http'):
                print(f"✔️ Cenário futuro encontrado: {ano} - {cenario} - {indicador['id']}")
                nome_cenario = cenarios_dict.get(cenario, f"cenário {cenario}")
                dados["link_dados_api"].append({
                    "url": download_url,
                    "protocol": f"WWW:DOWNLOAD-{i}.0-http--download",
                    "name": f"Download SHP - {recorte}, ano {ano}, resolução {resolucao}, cenário {nome_cenario}",
                    "description": f"Shapefile dos dados para {recorte}, {ano}, {resolucao}, cenário {nome_cenario}"
                })
                i += 1
            else:
                print(f"❌ Nenhum dado encontrado para {ano} - {cenario} - {indicador['id']}")

    return dados


# Preenche um template XML ISO 19115/19139 com os dados fornecidos.
# Substitui campos fixos como identificadores, título, resumo e overview, e atualiza ou insere recursos online (CI_OnlineResource) no bloco de distribuição do metadado, com base nas informações de links fornecidos.
# Retorna: ElementTree: Objeto XML com os dados preenchidos.
def preencher_template_com_dados(xml_template, dados):
    tree = ET.ElementTree(ET.fromstring(xml_template))
    root = tree.getroot()

    def set_text(xpath, value):
        elem = root.find(xpath, namespaces)
        if elem is not None:
            elem.text = value

    set_text('.//gmd:fileIdentifier/gco:CharacterString', dados['file_identifier'])
    set_text('.//gmd:parentIdentifier/gco:CharacterString', dados['parent_identifier'])
    set_text('.//gmd:title/gco:CharacterString', dados['titulo'])
    set_text('.//gmd:abstract/gco:CharacterString', dados['resumo'])
    set_text('.//gmd:MD_BrowseGraphic/gmd:fileName/gco:CharacterString', dados['overview_url'])

    for resource_data in dados["link_dados_api"]:
        protocolo = resource_data["protocol"]
        url = resource_data["url"]
        name = resource_data["name"]
        description = resource_data["description"]

        atualizado = False
        for resource in root.findall('.//gmd:CI_OnlineResource', namespaces):
            protocol_elem = resource.find('.//gmd:protocol/gco:CharacterString', namespaces)
            if protocol_elem is not None and protocol_elem.text == protocolo:
                linkage = resource.find('.//gmd:linkage/gmd:URL', namespaces)
                desc_elem = resource.find('.//gmd:description/gco:CharacterString', namespaces)
                name_elem = resource.find('.//gmd:name/gco:CharacterString', namespaces)

                if linkage is not None:
                    linkage.text = url
                if desc_elem is not None:
                    desc_elem.text = description
                if name_elem is not None:
                    name_elem.text = name
                atualizado = True
                break

        if not atualizado:
            online_resource = ET.Element('{http://www.isotc211.org/2005/gmd}CI_OnlineResource')

            linkage = ET.SubElement(online_resource, '{http://www.isotc211.org/2005/gmd}linkage')
            url_elem = ET.SubElement(linkage, '{http://www.isotc211.org/2005/gmd}URL')
            url_elem.text = url

            protocolo_elem = ET.SubElement(online_resource, '{http://www.isotc211.org/2005/gmd}protocol')
            protocolo_txt = ET.SubElement(protocolo_elem, '{http://www.isotc211.org/2005/gco}CharacterString')
            protocolo_txt.text = protocolo

            nome_elem = ET.SubElement(online_resource, '{http://www.isotc211.org/2005/gmd}name')
            nome_txt = ET.SubElement(nome_elem, '{http://www.isotc211.org/2005/gco}CharacterString')
            nome_txt.text = name

            descricao_elem = ET.SubElement(online_resource, '{http://www.isotc211.org/2005/gmd}description')
            descricao_txt = ET.SubElement(descricao_elem, '{http://www.isotc211.org/2005/gco}CharacterString')
            descricao_txt.text = description

            distrib_info = root.find('.//gmd:MD_Distribution', namespaces)
            if distrib_info is not None:
                transfer_options = distrib_info.find('.//gmd:MD_DigitalTransferOptions', namespaces)
                if transfer_options is not None:
                    onlineresp = ET.SubElement(transfer_options, '{http://www.isotc211.org/2005/gmd}onLine')
                    onlineresp.append(online_resource)

    return tree


if __name__ == '__main__':
    # Caminho do template ISO 19115/19139
    with open('input.xml', 'r', encoding='utf-8') as file:
        xml_template = file.read()

    with urllib.request.urlopen(url_hierarchy) as url:
        indicadores = json.load(url)
        
    # Caminho do diretório de saída
    output_dir = 'output_xml_files'
    os.makedirs(output_dir, exist_ok=True)

    num_arquivos_gerados = 0

    for indicador in indicadores:
        if indicador.get('level', 0) < 1:
            continue
        dados = extrair_dados_para_xml(indicador)
        tree = preencher_template_com_dados(xml_template, dados)
        safe_title = re.sub(r'[<>:"/\\|?*\n]', "_", indicador['title'])
        output_file = os.path.join(output_dir, f"{indicador['id']}.xml")
        tree.write(output_file, encoding='UTF-8', xml_declaration=True)
        num_arquivos_gerados += 1

    print(f'{num_arquivos_gerados} arquivos XML foram gerados em {output_dir}')
