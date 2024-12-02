# Automação de Metadados ISO para AdaptaBrasil

Este repositório contém um script em Python projetado para automatizar a geração de arquivos XML de metadados no padrão **ISO 19115/19139**, utilizando dados extraídos da API do AdaptaBrasil. Ele permite o compartilhamento desses metadados com sistemas compatíveis, como o **GeoNetwork**.

## Funcionamento

### Extração de Dados
- Conecta-se à API do AdaptaBrasil para acessar informações hierárquicas e indicadores.
- Recupera metadados como títulos, descrições completas, URLs de imagens (*overview*), e links para download de arquivos.

### Manipulação e Atualização de XML
- Utiliza um template XML no padrão ISO como base.
- Atualiza campos como título, resumo, palavras-chave e recursos online com os dados extraídos.
- Gera arquivos XML individuais para cada indicador.

 ### Diagrama de Fluxo de Dados
![Untitled diagram-2024-12-02-125824](https://github.com/user-attachments/assets/68db55b4-6fb2-4b99-83be-cbcac565d28d)


## Principais Recursos
- **Processamento Hierárquico**: Geração automática de títulos combinando indicadores e seus "pais" na hierarquia.
- **Gerenciamento de Arquivos**: Salva arquivos XML nomeados de forma única em diretórios.
- **Limite de Geração**: Controle para limitar a quantidade de arquivos processados por execução.
