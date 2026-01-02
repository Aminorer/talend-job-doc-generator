# 📚 Talend Documentation Generator - README Technique Complet

## 🎯 Vue d'ensemble du projet

**Objectif** : Créer une application Python/Streamlit qui génère automatiquement de la documentation professionnelle pour des jobs Talend ETL en parsant les fichiers `.item` (XML), en analysant les dépendances, et en produisant des documents Markdown enrichis avec schémas et descriptions générées par LLM local.

**Principe de fonctionnement** :
1. L'utilisateur fournit le chemin d'un fichier `.item` (fichier XML contenant la définition complète d'un job Talend)
2. L'application détecte automatiquement tous les fichiers associés (`.properties`, `.screenshot`)
3. Parse le XML pour extraire composants, connexions, paramètres, variables de contexte
4. Génère des diagrammes (Mermaid/Graphviz) du flux de données
5. Utilise un LLM local (Llama via Ollama) pour générer une description intelligente
6. Produit un document Markdown avec plusieurs niveaux de détail au choix
7. Permet l'export en PDF

---

## 📁 Structure du projet

```
talend-doc-generator/
├── src/
│   ├── parser/                    # Module de parsing des fichiers Talend
│   │   ├── __init__.py
│   │   ├── item_parser.py         # Parse le fichier .item (XML)
│   │   ├── properties_parser.py   # Parse le fichier .properties
│   │   └── context_parser.py      # Parse les variables de contexte
│   ├── analyzer/                  # Module d'analyse des jobs
│   │   ├── __init__.py
│   │   ├── job_analyzer.py        # Analyse la structure du job
│   │   ├── dependency_finder.py   # Trouve routines, joblets, connexions
│   │   └── flow_analyzer.py       # Analyse les flux de données
│   ├── generator/                 # Module de génération de documentation
│   │   ├── __init__.py
│   │   ├── markdown_generator.py  # Génère le Markdown
│   │   ├── diagram_generator.py   # Génère les diagrammes
│   │   └── pdf_exporter.py        # Export PDF
│   ├── llm/                       # Module LLM local
│   │   ├── __init__.py
│   │   ├── llama_client.py        # Client Ollama
│   │   └── prompts.py             # Templates de prompts
│   ├── ui/                        # Interface utilisateur
│   │   ├── __init__.py
│   │   └── streamlit_app.py       # Application Streamlit
│   ├── utils/                     # Utilitaires
│   │   ├── __init__.py
│   │   ├── screenshot_handler.py  # Gestion des screenshots
│   │   └── file_finder.py         # Détection auto des fichiers
│   └── main.py                    # Point d'entrée principal
├── templates/                     # Templates Markdown
│   ├── job_compact.md
│   ├── job_standard.md
│   └── job_exhaustif.md
├── tests/                         # Tests unitaires
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_analyzer.py
│   └── fixtures/                  # Fichiers de test
├── docs/                          # Documentation du projet
│   └── examples/                  # Exemples de documentation générée
├── config.yaml                    # Configuration
├── requirements.txt               # Dépendances Python
├── README.md                      # Ce fichier
└── .gitignore
```

---

## 🔍 Partie 1 : Parser le fichier .item (XML)

### 📄 Contexte technique

Le fichier `.item` est un fichier XML qui contient **TOUTE** la définition d'un job Talend. Voici sa structure :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<talendfile:ProcessType xmi:version="2.0" 
    xmlns:xmi="http://www.omg.org/XMI" 
    xmlns:talendfile="platform:/resource/org.talend.model/model/TalendFile.xsd"
    defaultContext="Default"
    jobType="Standard">
  
  <!-- Métadonnées du job -->
  <context confirmationNeeded="false" name="Default">
    <contextParameter comment="" name="stock_file" prompt="stock_file?" 
                      promptNeeded="false" type="id_String" value="/data/stocks.csv"/>
    <contextParameter name="db_host" type="id_String" value="srv-oracle-prod"/>
    <!-- Autres variables de contexte -->
  </context>

  <!-- Définition des composants (nodes) -->
  <node componentName="tFileInputDelimited" componentVersion="0.101" 
        offsetLabelX="0" offsetLabelY="0" posX="96" posY="160">
    <elementParameter field="TEXT" name="UNIQUE_NAME" value="tFileInputDelimited_1"/>
    <elementParameter field="FILE" name="FILENAME" value="context.stock_file"/>
    <elementParameter field="TEXT" name="FIELDSEPARATOR" value="&quot;;&quot;"/>
    <elementParameter field="TEXT" name="ENCODING" value="&quot;UTF-8&quot;"/>
    <!-- Beaucoup d'autres paramètres... -->
  </node>

  <node componentName="tMap" componentVersion="2.1">
    <elementParameter field="TEXT" name="UNIQUE_NAME" value="tMap_1"/>
    <!-- Structure du mapping interne très complexe -->
    <mapperTableEntries>...</mapperTableEntries>
  </node>

  <!-- Définition des connexions entre composants -->
  <connection connectorName="FLOW" label="row1" lineStyle="0" 
              source="tFileInputDelimited_1" target="tMap_1">
    <elementParameter field="CHECK" name="MONITOR_CONNECTION" value="false"/>
  </connection>

  <!-- Autres éléments... -->
</talendfile:ProcessType>
```

### 🎯 Objectif du parser

Créer une classe `TalendItemParser` qui :
1. Parse le XML avec `lxml`
2. Extrait les informations suivantes dans un dictionnaire Python structuré :
   - **Métadonnées** : nom du job, version, auteur, dates
   - **Variables de contexte** : toutes les `contextParameter`
   - **Composants** : tous les `node` avec leurs paramètres
   - **Connexions** : toutes les `connection` entre composants
   - **Schémas de données** : structure des colonnes pour chaque flux

### 📝 Implémentation détaillée

```python
# src/parser/item_parser.py

from lxml import etree
from pathlib import Path
from typing import Dict, List, Any
import re

class TalendItemParser:
    """
    Parser pour fichiers .item de Talend.
    
    Le fichier .item est un XML qui contient la définition complète d'un job Talend.
    Structure principale :
    - <context> : variables de contexte
    - <node> : composants du job (tFileInputDelimited, tMap, etc.)
    - <connection> : connexions entre composants (FLOW, ITERATE, etc.)
    """
    
    def __init__(self, item_path: str):
        """
        Initialise le parser avec le chemin du fichier .item
        
        Args:
            item_path: Chemin absolu vers le fichier .item
        """
        self.item_path = Path(item_path)
        self.tree = None
        self.root = None
        self.namespaces = {}
        
        # Validation
        if not self.item_path.exists():
            raise FileNotFoundError(f"Le fichier {item_path} n'existe pas")
        if not self.item_path.suffix == '.item':
            raise ValueError("Le fichier doit avoir l'extension .item")
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse le fichier .item et retourne un dictionnaire structuré.
        
        Returns:
            Dict contenant :
            {
                'name': str,                    # Nom du job
                'version': str,                 # Version
                'job_type': str,                # Type (Standard, etc.)
                'default_context': str,         # Contexte par défaut
                'author': str,                  # Auteur
                'created_at': str,              # Date de création
                'modified_at': str,             # Dernière modification
                'description': str,             # Description
                'contexts': Dict[str, Dict],    # Variables de contexte
                'components': List[Dict],       # Liste des composants
                'connections': List[Dict],      # Liste des connexions
                'subjobs': List[Dict],          # Sous-jobs
                'notes': List[Dict],            # Notes dans le job
                'stats': Dict                   # Statistiques
            }
        """
        # 1. Charger et parser le XML
        self._load_xml()
        
        # 2. Extraire les namespaces (important pour XPath)
        self._extract_namespaces()
        
        # 3. Parser chaque section
        job_data = {
            'name': self._get_job_name(),
            'version': self._get_version(),
            'job_type': self._get_job_type(),
            'default_context': self._get_default_context(),
            'author': self._get_author(),
            'created_at': self._get_creation_date(),
            'modified_at': self._get_modification_date(),
            'description': self._get_description(),
            'contexts': self._parse_contexts(),
            'components': self._parse_components(),
            'connections': self._parse_connections(),
            'subjobs': self._parse_subjobs(),
            'notes': self._parse_notes(),
        }
        
        # 4. Calculer des statistiques
        job_data['stats'] = self._calculate_stats(job_data)
        
        return job_data
    
    def _load_xml(self):
        """
        Charge le fichier XML avec lxml.
        
        Astuce : Utiliser etree.parse() qui gère automatiquement l'encodage.
        Ne pas utiliser ElementTree standard car moins performant.
        """
        try:
            self.tree = etree.parse(str(self.item_path))
            self.root = self.tree.getroot()
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Erreur de parsing XML : {e}")
    
    def _extract_namespaces(self):
        """
        Extrait les namespaces du XML pour faciliter les requêtes XPath.
        
        Les namespaces dans Talend sont généralement :
        - talendfile: platform:/resource/org.talend.model/model/TalendFile.xsd
        - xmi: http://www.omg.org/XMI
        
        Méthode : self.root.nsmap contient tous les namespaces
        """
        self.namespaces = self.root.nsmap
        
        # Ajouter un namespace par défaut si None existe
        if None in self.namespaces:
            self.namespaces['default'] = self.namespaces[None]
    
    def _get_job_name(self) -> str:
        """
        Extrait le nom du job depuis le nom du fichier.
        Format attendu : nom_job_version.item
        
        Exemple : j_unknown_ref_in_stock_alert_0.1.item
        -> Nom : j_unknown_ref_in_stock_alert
        """
        filename = self.item_path.stem  # Enlève l'extension
        # Pattern : tout sauf le dernier _X.X (version)
        match = re.match(r'(.+)_(\d+\.\d+)$', filename)
        if match:
            return match.group(1)
        return filename
    
    def _get_version(self) -> str:
        """
        Extrait la version depuis le nom du fichier.
        
        Exemple : j_unknown_ref_in_stock_alert_0.1.item -> "0.1"
        """
        filename = self.item_path.stem
        match = re.match(r'.+_(\d+\.\d+)$', filename)
        if match:
            return match.group(1)
        return "0.1"  # Version par défaut
    
    def _get_job_type(self) -> str:
        """
        Extrait le type de job depuis l'attribut jobType de la racine.
        
        XPath : /talendfile:ProcessType/@jobType
        Valeurs possibles : Standard, Big Data Batch, Data Service, etc.
        """
        job_type = self.root.get('jobType')
        return job_type if job_type else "Standard"
    
    def _get_default_context(self) -> str:
        """
        Extrait le contexte par défaut.
        
        XPath : /talendfile:ProcessType/@defaultContext
        """
        return self.root.get('defaultContext', 'Default')
    
    def _get_author(self) -> str:
        """
        Extrait l'auteur depuis le fichier .properties associé.
        
        Le .item ne contient pas l'auteur, il faut aller le chercher dans le .properties.
        Pour l'instant, on peut retourner "Unknown" et créer une méthode séparée.
        """
        # TODO: Implémenter la lecture du .properties
        return "Unknown"
    
    def _get_creation_date(self) -> str:
        """
        Extrait la date de création (depuis .properties).
        """
        return "Unknown"
    
    def _get_modification_date(self) -> str:
        """
        Extrait la date de dernière modification (depuis .properties).
        """
        return "Unknown"
    
    def _get_description(self) -> str:
        """
        Extrait la description du job si elle existe.
        
        XPath : //parameters/elementParameter[@name='DESCRIPTION']/@value
        """
        description_elem = self.root.find(
            ".//parameters/elementParameter[@name='DESCRIPTION']"
        )
        if description_elem is not None:
            return description_elem.get('value', '')
        return ""
    
    def _parse_contexts(self) -> Dict[str, Dict]:
        """
        Parse toutes les variables de contexte.
        
        Structure XML :
        <context name="Default">
            <contextParameter name="var1" type="id_String" value="valeur1" comment="..." />
            <contextParameter name="var2" type="id_Integer" value="42" />
        </context>
        
        Returns:
            {
                'Default': {
                    'var1': {
                        'value': 'valeur1',
                        'type': 'String',
                        'comment': '...'
                    },
                    'var2': {
                        'value': 42,
                        'type': 'Integer',
                        'comment': ''
                    }
                }
            }
        """
        contexts = {}
        
        # XPath pour trouver tous les contexts
        context_nodes = self.root.findall('.//context')
        
        for context_node in context_nodes:
            context_name = context_node.get('name', 'Default')
            contexts[context_name] = {}
            
            # Parser chaque variable de contexte
            for param in context_node.findall('contextParameter'):
                var_name = param.get('name')
                var_value = param.get('value', '')
                var_type = param.get('type', 'id_String')
                var_comment = param.get('comment', '')
                
                # Convertir le type Talend en type lisible
                var_type_clean = self._clean_type(var_type)
                
                # Convertir la valeur selon le type
                var_value_typed = self._convert_value(var_value, var_type_clean)
                
                contexts[context_name][var_name] = {
                    'value': var_value_typed,
                    'type': var_type_clean,
                    'comment': var_comment
                }
        
        return contexts
    
    def _clean_type(self, talend_type: str) -> str:
        """
        Convertit un type Talend (id_String, id_Integer) en type lisible.
        
        Mapping :
        - id_String -> String
        - id_Integer -> Integer
        - id_Double -> Double
        - id_Boolean -> Boolean
        - id_Date -> Date
        - id_File -> File
        - id_Directory -> Directory
        """
        type_mapping = {
            'id_String': 'String',
            'id_Integer': 'Integer',
            'id_Long': 'Long',
            'id_Double': 'Double',
            'id_Float': 'Float',
            'id_Boolean': 'Boolean',
            'id_Date': 'Date',
            'id_File': 'File',
            'id_Directory': 'Directory',
            'id_Character': 'Character',
            'id_BigDecimal': 'BigDecimal',
            'id_Object': 'Object',
            'id_List': 'List',
            'id_Password': 'Password'
        }
        return type_mapping.get(talend_type, talend_type)
    
    def _convert_value(self, value: str, var_type: str) -> Any:
        """
        Convertit une valeur string en son type Python approprié.
        
        Args:
            value: Valeur sous forme de string
            var_type: Type de la variable (String, Integer, etc.)
        
        Returns:
            Valeur convertie dans le bon type Python
        """
        if var_type == 'Integer' or var_type == 'Long':
            try:
                return int(value)
            except ValueError:
                return value
        elif var_type == 'Double' or var_type == 'Float':
            try:
                return float(value)
            except ValueError:
                return value
        elif var_type == 'Boolean':
            return value.lower() in ('true', '1', 'yes')
        else:
            return value
    
    def _parse_components(self) -> List[Dict]:
        """
        Parse tous les composants du job.
        
        C'EST LA PARTIE LA PLUS COMPLEXE car chaque composant a des dizaines de paramètres.
        
        Structure XML d'un composant :
        <node componentName="tFileInputDelimited" componentVersion="0.101" 
              offsetLabelX="0" offsetLabelY="0" posX="96" posY="160">
          <elementParameter field="TEXT" name="UNIQUE_NAME" value="tFileInputDelimited_1"/>
          <elementParameter field="FILE" name="FILENAME" value="context.stock_file"/>
          <elementParameter field="TEXT" name="FIELDSEPARATOR" value="&quot;;&quot;"/>
          <elementParameter field="CHECK" name="HEADER" value="1"/>
          <!-- 50+ autres paramètres... -->
          
          <!-- Schéma des colonnes (si applicable) -->
          <metadata connector="FLOW" name="tFileInputDelimited_1">
            <column comment="" key="false" length="50" name="ref_code" 
                    nullable="true" pattern="" precision="0" 
                    sourceType="" type="id_String" usefulColumn="true"/>
            <column name="stock_qty" type="id_Integer" length="10"/>
            <!-- Autres colonnes... -->
          </metadata>
        </node>
        
        Returns:
            Liste de dictionnaires :
            [
                {
                    'id': 'tFileInputDelimited_1',
                    'type': 'tFileInputDelimited',
                    'version': '0.101',
                    'position': {'x': 96, 'y': 160},
                    'category': 'Input',  # Déduit du type de composant
                    'parameters': {
                        'FILENAME': 'context.stock_file',
                        'FIELDSEPARATOR': ';',
                        'HEADER': True,
                        ...
                    },
                    'schema': [
                        {
                            'name': 'ref_code',
                            'type': 'String',
                            'length': 50,
                            'nullable': True,
                            'comment': ''
                        },
                        ...
                    ]
                },
                ...
            ]
        """
        components = []
        
        # XPath : tous les nodes
        node_elements = self.root.findall('.//node')
        
        for node in node_elements:
            component = {
                'id': None,
                'type': node.get('componentName'),
                'version': node.get('componentVersion', 'unknown'),
                'position': {
                    'x': int(node.get('posX', 0)),
                    'y': int(node.get('posY', 0))
                },
                'category': self._get_component_category(node.get('componentName')),
                'parameters': {},
                'schema': []
            }
            
            # Parser les paramètres
            for param in node.findall('elementParameter'):
                param_name = param.get('name')
                param_value = param.get('value')
                param_field = param.get('field')
                
                # Le UNIQUE_NAME est l'ID du composant
                if param_name == 'UNIQUE_NAME':
                    component['id'] = param_value
                
                # Convertir la valeur selon le type de field
                converted_value = self._convert_parameter_value(param_value, param_field)
                component['parameters'][param_name] = converted_value
            
            # Parser le schéma (colonnes de données)
            metadata = node.find('metadata')
            if metadata is not None:
                component['schema'] = self._parse_schema(metadata)
            
            components.append(component)
        
        return components
    
    def _get_component_category(self, component_name: str) -> str:
        """
        Détermine la catégorie d'un composant selon son nom.
        
        Règles de catégorisation :
        - t*Input* -> Input
        - t*Output* -> Output
        - tMap, tFilterRow, tSortRow, etc. -> Transform
        - tLogRow, tWarn -> Log
        - tRunJob, tPreJob, tPostJob -> Flow Control
        - tJava, tJavaRow -> Custom
        
        Args:
            component_name: Nom du composant (ex: tFileInputDelimited)
        
        Returns:
            Catégorie du composant
        """
        name_lower = component_name.lower()
        
        if 'input' in name_lower or 'extract' in name_lower:
            return 'Input'
        elif 'output' in name_lower or 'load' in name_lower:
            return 'Output'
        elif component_name in ['tMap', 'tFilterRow', 'tSortRow', 'tAggregateRow', 
                                 'tJoin', 'tUnite', 'tSplitRow', 'tNormalize', 'tDenormalize']:
            return 'Transform'
        elif 'log' in name_lower or 'warn' in name_lower:
            return 'Log'
        elif 'run' in name_lower or 'pre' in name_lower or 'post' in name_lower:
            return 'Flow Control'
        elif 'java' in name_lower:
            return 'Custom'
        else:
            return 'Other'
    
    def _convert_parameter_value(self, value: str, field_type: str) -> Any:
        """
        Convertit une valeur de paramètre selon son type de field.
        
        Types de fields Talend :
        - TEXT : String simple
        - MEMO_SQL : Requête SQL (String multiligne)
        - FILE : Chemin de fichier
        - DIRECTORY : Chemin de répertoire
        - CHECK : Boolean
        - CLOSED_LIST : Valeur d'une liste déroulante
        - TABLE : Tableau de valeurs (très complexe, format XML)
        - TECHNICAL : Valeur technique (ne pas afficher)
        
        Args:
            value: Valeur brute (string)
            field_type: Type de field
        
        Returns:
            Valeur convertie
        """
        if value is None:
            return None
        
        # Les valeurs avec des guillemets échappés : &quot;
        value = value.replace('&quot;', '"')
        
        if field_type == 'CHECK':
            return value.lower() in ('true', '1')
        elif field_type in ['TEXT', 'MEMO_SQL', 'FILE', 'DIRECTORY', 'CLOSED_LIST']:
            # Enlever les guillemets au début et à la fin si présents
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1]
            return value
        elif field_type == 'TABLE':
            # Les tables sont trop complexes, on les garde en string pour l'instant
            return value
        elif field_type == 'TECHNICAL':
            # Ne pas exposer les valeurs techniques
            return None
        else:
            return value
    
    def _parse_schema(self, metadata_node) -> List[Dict]:
        """
        Parse le schéma (colonnes) d'un composant.
        
        Structure XML :
        <metadata connector="FLOW" name="tFileInputDelimited_1">
          <column comment="" key="false" length="50" name="ref_code" 
                  nullable="true" pattern="" precision="0" 
                  sourceType="" type="id_String" usefulColumn="true"/>
          <column name="stock_qty" type="id_Integer" length="10"/>
        </metadata>
        
        Returns:
            [
                {
                    'name': 'ref_code',
                    'type': 'String',
                    'length': 50,
                    'precision': 0,
                    'nullable': True,
                    'key': False,
                    'comment': ''
                },
                ...
            ]
        """
        schema = []
        
        for column in metadata_node.findall('column'):
            column_info = {
                'name': column.get('name'),
                'type': self._clean_type(column.get('type', 'id_String')),
                'length': int(column.get('length', 0)),
                'precision': int(column.get('precision', 0)),
                'nullable': column.get('nullable', 'true').lower() == 'true',
                'key': column.get('key', 'false').lower() == 'true',
                'comment': column.get('comment', '')
            }
            schema.append(column_info)
        
        return schema
    
    def _parse_connections(self) -> List[Dict]:
        """
        Parse toutes les connexions entre composants.
        
        Structure XML :
        <connection connectorName="FLOW" label="row1" lineStyle="0" 
                    source="tFileInputDelimited_1" target="tMap_1">
          <elementParameter field="CHECK" name="MONITOR_CONNECTION" value="false"/>
          <elementParameter field="TEXT" name="UNIQUE_NAME" value="row1"/>
        </connection>
        
        Types de connexions (connectorName) :
        - FLOW (ou ROW) : flux de données ligne par ligne
        - ITERATE : itération (boucle)
        - TRIGGER : déclenchement (On Subjob Ok, On Subjob Error, etc.)
        - REJECT : lignes rejetées
        
        Returns:
            [
                {
                    'id': 'row1',
                    'type': 'FLOW',
                    'from': 'tFileInputDelimited_1',
                    'to': 'tMap_1',
                    'label': 'row1',
                    'line_style': 0
                },
                ...
            ]
        """
        connections = []
        
        connection_elements = self.root.findall('.//connection')
        
        for conn in connection_elements:
            connection = {
                'id': None,
                'type': conn.get('connectorName'),
                'from': conn.get('source'),
                'to': conn.get('target'),
                'label': conn.get('label', ''),
                'line_style': int(conn.get('lineStyle', 0))
            }
            
            # Trouver le UNIQUE_NAME
            unique_name_param = conn.find("elementParameter[@name='UNIQUE_NAME']")
            if unique_name_param is not None:
                connection['id'] = unique_name_param.get('value')
            
            connections.append(connection)
        
        return connections
    
    def _parse_subjobs(self) -> List[Dict]:
        """
        Parse les sous-jobs (subjobs).
        
        Un subjob est un groupe de composants qui s'exécutent ensemble.
        Dans Talend Studio, visuellement, les subjobs sont séparés par des lignes.
        
        Structure XML :
        <subjob>
          <elementParameter field="TEXT" name="UNIQUE_NAME" value="tFileInputDelimited_1"/>
          <elementParameter field="CHECK" name="SHOW_SUBJOB_TITLE" value="true"/>
          <elementParameter field="TEXT" name="SUBJOB_TITLE_COLOR" value="92;131;150"/>
        </subjob>
        
        Returns:
            [
                {
                    'start_component': 'tFileInputDelimited_1',
                    'show_title': True,
                    'title_color': '92;131;150'
                },
                ...
            ]
        """
        subjobs = []
        
        subjob_elements = self.root.findall('.//subjob')
        
        for subjob in subjob_elements:
            subjob_data = {
                'start_component': None,
                'show_title': False,
                'title_color': None
            }
            
            for param in subjob.findall('elementParameter'):
                param_name = param.get('name')
                param_value = param.get('value')
                
                if param_name == 'UNIQUE_NAME':
                    subjob_data['start_component'] = param_value
                elif param_name == 'SHOW_SUBJOB_TITLE':
                    subjob_data['show_title'] = param_value.lower() == 'true'
                elif param_name == 'SUBJOB_TITLE_COLOR':
                    subjob_data['title_color'] = param_value
            
            subjobs.append(subjob_data)
        
        return subjobs
    
    def _parse_notes(self) -> List[Dict]:
        """
        Parse les notes (commentaires) dans le job.
        
        Les notes sont des annotations textuelles que les développeurs ajoutent
        dans Talend Studio pour documenter le job.
        
        Structure XML :
        <note opaque="true" posX="32" posY="32" sizeHeight="64" sizeWidth="160" 
              text="Cette section charge les données depuis le fichier CSV"/>
        
        Returns:
            [
                {
                    'text': 'Cette section charge...',
                    'position': {'x': 32, 'y': 32},
                    'size': {'width': 160, 'height': 64},
                    'opaque': True
                },
                ...
            ]
        """
        notes = []
        
        note_elements = self.root.findall('.//note')
        
        for note in note_elements:
            note_data = {
                'text': note.get('text', ''),
                'position': {
                    'x': int(note.get('posX', 0)),
                    'y': int(note.get('posY', 0))
                },
                'size': {
                    'width': int(note.get('sizeWidth', 100)),
                    'height': int(note.get('sizeHeight', 50))
                },
                'opaque': note.get('opaque', 'false').lower() == 'true'
            }
            notes.append(note_data)
        
        return notes
    
    def _calculate_stats(self, job_data: Dict) -> Dict:
        """
        Calcule des statistiques sur le job.
        
        Args:
            job_data: Données parsées du job
        
        Returns:
            {
                'nb_components': int,
                'nb_connections': int,
                'nb_context_vars': int,
                'nb_inputs': int,
                'nb_outputs': int,
                'nb_transformations': int,
                'component_types': Dict[str, int],  # Compteur par type
                'connection_types': Dict[str, int]
            }
        """
        stats = {
            'nb_components': len(job_data['components']),
            'nb_connections': len(job_data['connections']),
            'nb_context_vars': sum(
                len(vars) for vars in job_data['contexts'].values()
            ),
            'nb_inputs': 0,
            'nb_outputs': 0,
            'nb_transformations': 0,
            'component_types': {},
            'connection_types': {}
        }
        
        # Compter par catégorie
        for comp in job_data['components']:
            category = comp['category']
            comp_type = comp['type']
            
            if category == 'Input':
                stats['nb_inputs'] += 1
            elif category == 'Output':
                stats['nb_outputs'] += 1
            elif category == 'Transform':
                stats['nb_transformations'] += 1
            
            # Compter par type de composant
            stats['component_types'][comp_type] = \
                stats['component_types'].get(comp_type, 0) + 1
        
        # Compter par type de connexion
        for conn in job_data['connections']:
            conn_type = conn['type']
            stats['connection_types'][conn_type] = \
                stats['connection_types'].get(conn_type, 0) + 1
        
        return stats


# === EXEMPLE D'UTILISATION ===

if __name__ == '__main__':
    # Test du parser
    parser = TalendItemParser(
        "REFERENTIELS_TV8/process/Alertes/j_unknown_ref_in_stock_alert_0.1.item"
    )
    
    job_data = parser.parse()
    
    print(f"Job : {job_data['name']} v{job_data['version']}")
    print(f"Type : {job_data['job_type']}")
    print(f"Composants : {job_data['stats']['nb_components']}")
    print(f"Connexions : {job_data['stats']['nb_connections']}")
    print(f"Variables contexte : {job_data['stats']['nb_context_vars']}")
    
    print("\n=== Composants ===")
    for comp in job_data['components']:
        print(f"- {comp['id']} ({comp['type']}) [{comp['category']}]")
    
    print("\n=== Connexions ===")
    for conn in job_data['connections']:
        print(f"- {conn['from']} --{conn['type']}-> {conn['to']}")
    
    print("\n=== Variables de contexte (Default) ===")
    for var_name, var_data in job_data['contexts'].get('Default', {}).items():
        print(f"- {var_name} = {var_data['value']} ({var_data['type']})")
```

---

## 🔍 Partie 2 : Parser le fichier .properties

### 📄 Contexte technique

Le fichier `.properties` contient les métadonnées du job (auteur, dates, statut, etc.). C'est un fichier XML plus simple que le `.item`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xmi:XMI xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" 
         xmlns:TalendProperties="http://www.talend.org/properties">
  <TalendProperties:Property xmi:id="_abc123" 
      id="_abc123" label="j_unknown_ref_in_stock_alert" 
      version="0.1" statusCode="" 
      author="amine@wyz.fr" 
      creationDate="2024-06-15T10:30:00.000+0200"
      modificationDate="2024-12-28T14:45:00.000+0200">
    <description>Job pour détecter les références inconnues dans les stocks</description>
  </TalendProperties:Property>
  <TalendProperties:ItemState path="Alertes"/>
</xmi:XMI>
```

### 📝 Implémentation

```python
# src/parser/properties_parser.py

from lxml import etree
from pathlib import Path
from typing import Dict
from datetime import datetime

class TalendPropertiesParser:
    """
    Parser pour fichiers .properties de Talend.
    
    Le fichier .properties contient les métadonnées du job :
    - Auteur
    - Dates de création/modification
    - Description
    - Statut
    - Chemin dans le projet
    """
    
    def __init__(self, properties_path: str):
        """
        Initialise le parser.
        
        Args:
            properties_path: Chemin vers le fichier .properties
        """
        self.properties_path = Path(properties_path)
        self.tree = None
        self.root = None
        
        if not self.properties_path.exists():
            raise FileNotFoundError(f"Le fichier {properties_path} n'existe pas")
    
    def parse(self) -> Dict:
        """
        Parse le fichier .properties.
        
        Returns:
            {
                'author': str,
                'created_at': datetime,
                'modified_at': datetime,
                'description': str,
                'status': str,
                'category_path': str,  # Ex: "Alertes"
                'label': str
            }
        """
        # Charger le XML
        self.tree = etree.parse(str(self.properties_path))
        self.root = self.tree.getroot()
        
        # Trouver l'élément Property
        # Namespace : http://www.talend.org/properties
        namespaces = {'tp': 'http://www.talend.org/properties'}
        
        property_elem = self.root.find('.//tp:Property', namespaces)
        
        if property_elem is None:
            raise ValueError("Élément Property introuvable dans le fichier")
        
        # Extraire les métadonnées
        metadata = {
            'author': property_elem.get('author', 'Unknown'),
            'created_at': self._parse_date(property_elem.get('creationDate')),
            'modified_at': self._parse_date(property_elem.get('modificationDate')),
            'description': '',
            'status': property_elem.get('statusCode', ''),
            'label': property_elem.get('label', ''),
            'category_path': ''
        }
        
        # Description
        desc_elem = property_elem.find('description')
        if desc_elem is not None and desc_elem.text:
            metadata['description'] = desc_elem.text.strip()
        
        # Chemin de catégorie
        item_state = self.root.find('.//tp:ItemState', namespaces)
        if item_state is not None:
            metadata['category_path'] = item_state.get('path', '')
        
        return metadata
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse une date au format ISO.
        
        Format : 2024-06-15T10:30:00.000+0200
        
        Args:
            date_str: String de date
        
        Returns:
            Objet datetime
        """
        if not date_str:
            return None
        
        try:
            # Supprimer les millisecondes et le timezone pour simplifier
            # Format : 2024-06-15T10:30:00
            date_clean = date_str[:19]
            return datetime.fromisoformat(date_clean)
        except ValueError:
            return None
```

---

## 🔍 Partie 3 : Détection automatique des fichiers associés

### 📝 Objectif

L'utilisateur ne donne que le chemin du `.item`, l'application doit trouver automatiquement :
- Le `.properties` (même nom, même dossier)
- Le `.screenshot` (même nom, même dossier)
- Le dossier racine du projet (`REFERENTIELS_TV8/`)
- Les fichiers de contexte dans `context/`

### 📝 Implémentation

```python
# src/utils/file_finder.py

from pathlib import Path
from typing import Dict, Optional, List

class TalendFileFinder:
    """
    Utilitaire pour trouver automatiquement tous les fichiers associés à un job Talend.
    """
    
    def __init__(self, item_path: str):
        """
        Args:
            item_path: Chemin vers le fichier .item
        """
        self.item_path = Path(item_path)
        
        if not self.item_path.exists():
            raise FileNotFoundError(f"Le fichier {item_path} n'existe pas")
        
        # Déterminer le nom de base (sans version)
        self.base_name = self._get_base_name()
        self.version = self._get_version()
        
        # Trouver la racine du projet
        self.project_root = self._find_project_root()
    
    def find_all(self) -> Dict[str, Optional[Path]]:
        """
        Trouve tous les fichiers associés au job.
        
        Returns:
            {
                'item': Path,
                'properties': Path or None,
                'screenshot': Path or None,
                'project_root': Path,
                'context_files': List[Path]
            }
        """
        return {
            'item': self.item_path,
            'properties': self._find_properties(),
            'screenshot': self._find_screenshot(),
            'project_root': self.project_root,
            'context_files': self._find_context_files()
        }
    
    def _get_base_name(self) -> str:
        """
        Extrait le nom de base sans version.
        
        Exemple : j_unknown_ref_in_stock_alert_0.1.item
        -> j_unknown_ref_in_stock_alert
        """
        stem = self.item_path.stem  # Sans extension
        # Retirer le _X.X à la fin
        parts = stem.split('_')
        # Le dernier élément est la version (0.1, 1.0, etc.)
        if len(parts) > 1 and '.' in parts[-1]:
            return '_'.join(parts[:-1])
        return stem
    
    def _get_version(self) -> str:
        """Extrait la version du nom de fichier."""
        stem = self.item_path.stem
        parts = stem.split('_')
        if len(parts) > 1 and '.' in parts[-1]:
            return parts[-1]
        return '0.1'
    
    def _find_project_root(self) -> Path:
        """
        Remonte l'arborescence pour trouver la racine du projet Talend.
        
        La racine contient les dossiers : process/, context/, metadata/, etc.
        """
        current = self.item_path.parent
        
        # Remonter jusqu'à trouver un dossier avec "process" dedans
        while current.parent != current:
            # Vérifier si on est dans un dossier de projet Talend
            if (current / 'process').exists() and (current / 'context').exists():
                return current
            current = current.parent
        
        # Par défaut, retourner 2 niveaux au-dessus du .item
        return self.item_path.parent.parent.parent
    
    def _find_properties(self) -> Optional[Path]:
        """
        Trouve le fichier .properties associé.
        
        Il est dans le même dossier avec le même nom.
        """
        properties_path = self.item_path.with_suffix('.properties')
        return properties_path if properties_path.exists() else None
    
    def _find_screenshot(self) -> Optional[Path]:
        """
        Trouve le fichier .screenshot associé.
        
        Il est dans le même dossier avec le même nom.
        """
        screenshot_path = self.item_path.with_suffix('.screenshot')
        return screenshot_path if screenshot_path.exists() else None
    
    def _find_context_files(self) -> List[Path]:
        """
        Trouve tous les fichiers de contexte du projet.
        
        Ils sont dans le dossier context/ à la racine du projet.
        """
        context_dir = self.project_root / 'context'
        
        if not context_dir.exists():
            return []
        
        # Trouver tous les .item dans context/
        return list(context_dir.rglob('*.item'))
```

---

## 🔍 Partie 4 : Génération des diagrammes

### 📝 Objectif

Générer des diagrammes visuels du flux de données en **Mermaid** (intégré dans Markdown) et/ou **Graphviz** (PNG/SVG).

### 📝 Implémentation Mermaid

```python
# src/generator/diagram_generator.py

from typing import Dict, List

class DiagramGenerator:
    """
    Générateur de diagrammes pour les jobs Talend.
    
    Supporte :
    - Mermaid (intégré dans Markdown)
    - Graphviz (génération d'images PNG/SVG)
    """
    
    def __init__(self, diagram_type: str = 'mermaid'):
        """
        Args:
            diagram_type: 'mermaid', 'graphviz', ou 'both'
        """
        self.diagram_type = diagram_type
    
    def generate(self, job_data: Dict) -> str:
        """
        Génère le diagramme selon le type configuré.
        
        Args:
            job_data: Données du job parsé
        
        Returns:
            String Markdown contenant le(s) diagramme(s)
        """
        if self.diagram_type == 'mermaid':
            return self._generate_mermaid(job_data)
        elif self.diagram_type == 'graphviz':
            return self._generate_graphviz(job_data)
        else:  # both
            mermaid = self._generate_mermaid(job_data)
            graphviz = self._generate_graphviz(job_data)
            return f"{mermaid}\n\n### Version Graphviz\n{graphviz}"
    
    def _generate_mermaid(self, job_data: Dict) -> str:
        """
        Génère un diagramme Mermaid.
        
        Format Mermaid :
        ```mermaid
        graph LR
            A[Component 1] -->|row1| B[Component 2]
            B -.->|iterate| C[Component 3]
        ```
        
        Styles de connexions :
        - FLOW : -->
        - ITERATE : -.->
        - TRIGGER : ==>
        - REJECT : --x
        
        Args:
            job_data: Données du job
        
        Returns:
            String Markdown avec code Mermaid
        """
        diagram = "```mermaid\ngraph LR\n"
        
        # Créer un mapping id -> label court
        component_labels = {}
        for i, comp in enumerate(job_data['components']):
            # Label court : nom sans le type
            label = comp['id'].replace(comp['type'] + '_', '')
            component_labels[comp['id']] = f"{label}[{comp['type']}]"
        
        # Ajouter les connexions
        for conn in job_data['connections']:
            from_id = conn['from']
            to_id = conn['to']
            conn_type = conn['type']
            label = conn['label']
            
            # Style selon le type
            style = self._get_mermaid_style(conn_type)
            
            # Format : FROM style|label| TO
            from_label = component_labels.get(from_id, from_id)
            to_label = component_labels.get(to_id, to_id)
            
            diagram += f"    {from_id}{from_label} {style}|{label}| {to_id}{to_label}\n"
        
        diagram += "```\n"
        return diagram
    
    def _get_mermaid_style(self, conn_type: str) -> str:
        """
        Retourne le style Mermaid selon le type de connexion.
        
        Mapping :
        - FLOW/ROW : -->
        - ITERATE : -.->
        - TRIGGER : ==>
        - REJECT : --x
        """
        styles = {
            'FLOW': '-->',
            'ROW': '-->',
            'ITERATE': '-.->',
            'TRIGGER': '==>',
            'REJECT': '--x',
            'LOOKUP': '-->',
            'FILTER': '-->'
        }
        return styles.get(conn_type, '-->')
    
    def _generate_graphviz(self, job_data: Dict) -> str:
        """
        Génère un diagramme Graphviz.
        
        Graphviz permet plus de personnalisation :
        - Couleurs selon les catégories de composants
        - Formes différentes (rectangle, ellipse, etc.)
        - Layout automatique optimisé
        
        Format DOT :
        digraph G {
            rankdir=LR;
            node [shape=box];
            
            comp1 [label="tFileInput" fillcolor=lightblue];
            comp2 [label="tMap" fillcolor=yellow];
            
            comp1 -> comp2 [label="row1"];
        }
        
        Returns:
            Chemin vers l'image générée (PNG/SVG)
        """
        try:
            import graphviz
        except ImportError:
            return "⚠️ Graphviz non installé. Utilisez : pip install graphviz"
        
        # Créer le graphe
        dot = graphviz.Digraph(comment=job_data['name'])
        dot.attr(rankdir='LR')  # Left to Right
        dot.attr('node', shape='box', style='filled')
        
        # Ajouter les nœuds avec couleurs selon catégorie
        for comp in job_data['components']:
            color = self._get_component_color(comp['category'])
            dot.node(
                comp['id'],
                label=f"{comp['id']}\n{comp['type']}",
                fillcolor=color
            )
        
        # Ajouter les connexions
        for conn in job_data['connections']:
            style = self._get_graphviz_style(conn['type'])
            dot.edge(
                conn['from'],
                conn['to'],
                label=conn['label'],
                style=style
            )
        
        # Générer l'image
        output_path = f"/tmp/{job_data['name']}_diagram"
        dot.render(output_path, format='png', cleanup=True)
        
        return f"![Diagram]({output_path}.png)"
    
    def _get_component_color(self, category: str) -> str:
        """Couleur selon la catégorie du composant."""
        colors = {
            'Input': 'lightblue',
            'Output': 'lightgreen',
            'Transform': 'yellow',
            'Log': 'orange',
            'Flow Control': 'pink',
            'Custom': 'lightgray',
            'Other': 'white'
        }
        return colors.get(category, 'white')
    
    def _get_graphviz_style(self, conn_type: str) -> str:
        """Style de connexion pour Graphviz."""
        styles = {
            'FLOW': 'solid',
            'ROW': 'solid',
            'ITERATE': 'dashed',
            'TRIGGER': 'bold',
            'REJECT': 'dotted'
        }
        return styles.get(conn_type, 'solid')
```

---

## 🔍 Partie 5 : Intégration LLM (Ollama/Llama)

### 📄 Contexte

Utiliser un LLM local (Llama 3.2 via Ollama) pour générer automatiquement :
1. Une **description** du job en français
2. Une **analyse technique** (complexité, points d'attention)
3. Des **suggestions d'optimisation** (optionnel)

### 📝 Installation Ollama

```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger Llama 3.2
ollama pull llama3.2:latest

# Ou un modèle plus petit pour être plus rapide
ollama pull llama3.2:1b  # Version 1B de paramètres (plus rapide)

# Tester
ollama run llama3.2:latest
```

### 📝 Implémentation

```python
# src/llm/llama_client.py

import requests
import json
from typing import Dict

class LlamaClient:
    """
    Client pour communiquer avec Ollama (LLM local).
    
    Ollama expose une API REST sur http://localhost:11434
    """
    
    def __init__(self, model: str = "llama3.2:latest", base_url: str = "http://localhost:11434"):
        """
        Args:
            model: Nom du modèle Ollama à utiliser
            base_url: URL de l'API Ollama
        """
        self.model = model
        self.base_url = base_url
        self.timeout = 60  # Timeout de 60 secondes
    
    def generate_description(self, job_data: Dict) -> str:
        """
        Génère une description du job en français.
        
        Le prompt est construit avec :
        - Nom du job
        - Liste des composants principaux
        - Flux de données (connexions)
        - Variables de contexte importantes
        
        Args:
            job_data: Données du job parsé
        
        Returns:
            Description générée par le LLM
        """
        # Construire le prompt
        prompt = self._build_description_prompt(job_data)
        
        # Appeler l'API Ollama
        response = self._call_ollama(prompt, max_tokens=300)
        
        if response:
            return response.strip()
        else:
            # Fallback : description basique
            return self._fallback_description(job_data)
    
    def generate_technical_analysis(self, job_data: Dict) -> str:
        """
        Génère une analyse technique du job.
        
        Points analysés :
        - Complexité du job
        - Points d'attention (performances, erreurs potentielles)
        - Dépendances critiques
        """
        prompt = self._build_analysis_prompt(job_data)
        response = self._call_ollama(prompt, max_tokens=400)
        
        return response.strip() if response else "Analyse non disponible."
    
    def _build_description_prompt(self, job_data: Dict) -> str:
        """
        Construit le prompt pour la génération de description.
        
        Stratégie :
        - Être précis et concis dans le prompt
        - Fournir des exemples de sortie attendue
        - Limiter les informations pour ne pas surcharger le contexte
        """
        # Top 5 des composants
        top_components = job_data['components'][:5]
        components_str = "\n".join([
            f"- {comp['type']} (ID: {comp['id']})"
            for comp in top_components
        ])
        
        # Top 5 des connexions
        top_connections = job_data['connections'][:5]
        connections_str = "\n".join([
            f"- {conn['from']} → {conn['to']} ({conn['type']})"
            for conn in top_connections
        ])
        
        # Variables de contexte importantes
        context_vars = job_data['contexts'].get('Default', {})
        context_str = "\n".join([
            f"- {var_name}: {var_data['value']}"
            for var_name, var_data in list(context_vars.items())[:5]
        ])
        
        prompt = f"""Tu es un expert en Talend ETL. Analyse ce job Talend et rédige une description claire et concise en français (2-3 paragraphes).

**Nom du job** : {job_data['name']}
**Version** : {job_data['version']}
**Type** : {job_data['job_type']}

**Composants principaux** :
{components_str}

**Flux de données** :
{connections_str}

**Variables de contexte** :
{context_str}

**Statistiques** :
- Total composants : {job_data['stats']['nb_components']}
- Composants Input : {job_data['stats']['nb_inputs']}
- Composants Output : {job_data['stats']['nb_outputs']}
- Transformations : {job_data['stats']['nb_transformations']}

Rédige une description professionnelle qui explique :
1. L'objectif principal du job (que fait-il ?)
2. Les étapes clés du traitement (comment ?)
3. Les sources et destinations des données

Description :"""
        
        return prompt
    
    def _build_analysis_prompt(self, job_data: Dict) -> str:
        """
        Construit le prompt pour l'analyse technique.
        """
        prompt = f"""Tu es un expert en Talend ETL. Analyse ce job techniquement.

**Job** : {job_data['name']}
**Statistiques** :
- {job_data['stats']['nb_components']} composants
- {job_data['stats']['nb_connections']} connexions
- {job_data['stats']['nb_transformations']} transformations

Identifie :
1. Niveau de complexité (Simple/Moyen/Complexe)
2. Points d'attention potentiels (performances, erreurs)
3. Bonnes pratiques respectées ou non

Analyse :"""
        
        return prompt
    
    def _call_ollama(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Appelle l'API Ollama pour générer du texte.
        
        API Endpoint : POST /api/generate
        
        Body :
        {
            "model": "llama3.2:latest",
            "prompt": "...",
            "stream": false,
            "options": {
                "temperature": 0.3,
                "num_predict": 300
            }
        }
        
        Args:
            prompt: Le prompt à envoyer
            max_tokens: Nombre maximum de tokens à générer
        
        Returns:
            Texte généré ou None si erreur
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,  # Pas de streaming
                    "options": {
                        "temperature": 0.3,  # Assez déterministe
                        "num_predict": max_tokens  # Limite de tokens
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                print(f"Erreur API Ollama : {response.status_code}")
                return None
        
        except requests.exceptions.Timeout:
            print("Timeout lors de l'appel à Ollama")
            return None
        except requests.exceptions.ConnectionError:
            print("Impossible de se connecter à Ollama. Est-il lancé ?")
            return None
        except Exception as e:
            print(f"Erreur inattendue : {e}")
            return None
    
    def _fallback_description(self, job_data: Dict) -> str:
        """
        Description de base si le LLM est indisponible.
        
        Génère une description simple basée sur les statistiques.
        """
        return f"""Job Talend '{job_data['name']}' (version {job_data['version']}).

Ce job contient {job_data['stats']['nb_components']} composants, dont {job_data['stats']['nb_inputs']} sources de données et {job_data['stats']['nb_outputs']} destinations. Il effectue {job_data['stats']['nb_transformations']} transformation(s) de données.

Type de job : {job_data['job_type']}."""

    def check_availability(self) -> bool:
        """
        Vérifie si Ollama est disponible.
        
        Returns:
            True si Ollama répond, False sinon
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
```

---

## 🎨 Partie 6 : Interface Streamlit

### 📝 Fonctionnalités

1. **Zone d'upload/input** : Chemin ou upload du fichier `.item`
2. **Configuration** : Sliders et checkboxes pour personnaliser
3. **Génération** : Bouton qui lance le processus
4. **Aperçu** : Affichage du Markdown généré
5. **Export** : Téléchargement MD et PDF

### 📝 Layout

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR                    │  MAIN                     │
├─────────────────────────────┼───────────────────────────┤
│  ⚙️ Configuration           │  🎯 Génération             │
│  • Input method             │  • Button Generate        │
│  • Detail level (slider)    │  • Progress bar           │
│  • Diagram type (radio)     │  • Success message        │
│  • Options (checkboxes)     ├───────────────────────────┤
│    - Screenshot             │  📥 Export                 │
│    - Contexts               │  • Download MD            │
│    - LLM description        │  • Generate PDF           │
│  • Expandable Details       ├───────────────────────────┤
│    - Routines               │  👁️ Preview (tabs)         │
│    - Joblets                │  • Markdown code          │
│    - Connections            │  • Rendered view          │
│                             │  • Statistics             │
└─────────────────────────────┴───────────────────────────┘
```

### 📝 Implémentation

Le code complet est dans la section précédente. Points clés :

1. **Session state** : Utiliser `st.session_state` pour garder les données entre interactions
2. **Spinners** : `with st.spinner(...)` pour les opérations longues
3. **Metrics** : `st.metric()` pour afficher les statistiques
4. **Tabs** : `st.tabs()` pour organiser l'aperçu
5. **Download buttons** : `st.download_button()` pour les exports

---

## 🔍 Partie 7 : Génération du Markdown final

### 📝 Templates selon le niveau de détail

#### 🎯 Niveau Compact (1-2 pages)

```markdown
# {job_name}

## 📋 Résumé
- Version : {version}
- Catégorie : {category}
- Composants : {nb_components}
- Auteur : {author}

## 📝 Description
{llm_description}

## 🎯 Flux principal
{mermaid_diagram}

## ⚙️ Variables clés
| Variable | Valeur | Type |
|----------|--------|------|
| ... | ... | ... |
```

#### 🎯 Niveau Standard (3-5 pages)

```markdown
# {job_name}

## 📋 Informations générales
[Table avec toutes les métadonnées]

## 📸 Aperçu visuel
![Screenshot](...)

## 📝 Description
{llm_description}

## 🎨 Schéma du flux
{diagram}

## 🔧 Composants ({nb})
[Liste des composants avec détails]

## ⚙️ Variables de contexte
[Table complète]

## 📊 Statistiques
[Métriques]
```

#### 🎯 Niveau Exhaustif (10+ pages)

Inclut tout de "Standard" plus :
- Détails de **chaque composant** (paramètres, schémas)
- **Routines** utilisées (avec code si disponible)
- **Joblets** inclus
- **Connexions DB** (configurations)
- **Notes** dans le job
- **Analyse technique** (LLM)
- **Suggestions d'optimisation**

---

## 🔍 Partie 8 : Export PDF

### 📝 Conversion Markdown → PDF

Utiliser **WeasyPrint** qui gère bien le HTML/CSS et produit de beaux PDFs.

```python
# src/generator/pdf_exporter.py

from markdown import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from weasyprint import HTML, CSS
from io import BytesIO
from pathlib import Path
import base64

class PDFExporter:
    """
    Exporte la documentation Markdown en PDF.
    
    Utilise WeasyPrint pour un rendu professionnel.
    """
    
    def __init__(self):
        # CSS pour le PDF
        self.css = """
        @page {
            size: A4;
            margin: 2.5cm 2cm;
            
            @top-center {
                content: "Documentation Talend";
                font-size: 10pt;
                color: #666;
            }
            
            @bottom-right {
                content: "Page " counter(page) " / " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
            page-break-before: always;
        }
        
        h1:first-of-type {
            page-break-before: avoid;
        }
        
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }
        
        h3 {
            color: #555;
            margin-top: 20px;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
        
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-left: 3px solid #3498db;
            padding: 10px;
            overflow-x: auto;
            page-break-inside: avoid;
        }
        
        pre code {
            background-color: transparent;
            padding: 0;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            page-break-inside: avoid;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }
        
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        img {
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 15px;
            color: #555;
            font-style: italic;
            margin: 15px 0;
        }
        
        .toc {
            page-break-after: always;
            border: 1px solid #ddd;
            padding: 20px;
            background-color: #f9f9f9;
        }
        
        .toc h2 {
            margin-top: 0;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc li {
            margin: 5px 0;
        }
        """
    
    def convert(self, markdown_content: str, doc_data: Dict, include_screenshot: bool = True) -> bytes:
        """
        Convertit le Markdown en PDF.
        
        Args:
            markdown_content: Contenu Markdown
            doc_data: Métadonnées du document
            include_screenshot: Inclure le screenshot dans le PDF
        
        Returns:
            Bytes du PDF généré
        """
        # 1. Construire la page de couverture
        cover_html = self._build_cover_page(doc_data)
        
        # 2. Convertir Markdown en HTML
        body_html = markdown(
            markdown_content,
            extensions=[
                'tables',
                'fenced_code',
                'codehilite',
                'toc'
            ]
        )
        
        # 3. Intégrer le screenshot si disponible
        if include_screenshot and doc_data.get('screenshot_path'):
            body_html = self._embed_screenshot(body_html, doc_data['screenshot_path'])
        
        # 4. Assembler le HTML complet
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{doc_data['job_name']} - Documentation</title>
            <style>{self.css}</style>
        </head>
        <body>
            {cover_html}
            <div class="content">
                {body_html}
            </div>
        </body>
        </html>
        """
        
        # 5. Générer le PDF avec WeasyPrint
        pdf_bytes = HTML(string=full_html).write_pdf()
        
        return pdf_bytes
    
    def _build_cover_page(self, doc_data: Dict) -> str:
        """
        Construit une page de couverture professionnelle.
        """
        return f"""
        <div class="cover-page" style="text-align: center; padding: 100px 50px;">
            <h1 style="font-size: 36pt; margin-bottom: 20px; border: none;">
                {doc_data['job_name']}
            </h1>
            <h2 style="font-size: 18pt; color: #7f8c8d; border: none;">
                Documentation Technique
            </h2>
            <p style="margin-top: 50px; font-size: 14pt;">
                Version {doc_data['version']}<br>
                Catégorie: {doc_data.get('category', 'N/A')}<br>
                {doc_data.get('author', 'Unknown')}<br>
                Généré le {doc_data.get('generated_at', 'N/A')}
            </p>
            <div style="margin-top: 100px; padding: 20px; background-color: #ecf0f1; border-radius: 5px;">
                <p style="font-size: 12pt; color: #555;">
                    📊 {doc_data['stats']['nb_components']} composants<br>
                    🔗 {doc_data['stats']['nb_connections']} connexions<br>
                    ⚙️ {doc_data['stats']['nb_context_vars']} variables de contexte
                </p>
            </div>
        </div>
        """
    
    def _embed_screenshot(self, html: str, screenshot_path: Path) -> str:
        """
        Intègre le screenshot en base64 dans le HTML.
        
        Pourquoi base64 ? Car WeasyPrint embarque les images dans le PDF.
        """
        if not screenshot_path.exists():
            return html
        
        # Lire l'image et la convertir en base64
        with open(screenshot_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Détecter le format
        ext = screenshot_path.suffix.lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }.get(ext, 'image/png')
        
        # Remplacer le chemin par l'image base64
        img_tag = f'<img src="data:{mime_type};base64,{img_data}" alt="Job Screenshot" />'
        
        # Remplacer dans le HTML
        html = html.replace(f'![Screenshot]({screenshot_path})', img_tag)
        
        return html
```

---

## 🔍 Partie 9 : Point d'entrée principal

### 📝 Orchestration de tout le système

```python
# src/main.py

from pathlib import Path
from typing import Dict
from datetime import datetime

from src.parser.item_parser import TalendItemParser
from src.parser.properties_parser import TalendPropertiesParser
from src.utils.file_finder import TalendFileFinder
from src.generator.markdown_generator import MarkdownGenerator
from src.generator.diagram_generator import DiagramGenerator
from src.llm.llama_client import LlamaClient

class TalendDocGenerator:
    """
    Orchestrateur principal de la génération de documentation.
    
    Cette classe coordonne tous les modules :
    1. Trouve les fichiers associés
    2. Parse les fichiers Talend
    3. Génère la description avec LLM
    4. Génère les diagrammes
    5. Produit le Markdown final
    """
    
    def __init__(self, item_path: str, config: Dict):
        """
        Args:
            item_path: Chemin vers le fichier .item
            config: Configuration de la génération
        """
        self.item_path = Path(item_path)
        self.config = config
        
        # Initialiser les composants
        self.file_finder = TalendFileFinder(str(self.item_path))
        self.llm_client = None
        
        if config.get('use_llm', False):
            self.llm_client = LlamaClient(model=config.get('llm_model', 'llama3.2:latest'))
    
    def generate(self) -> Dict:
        """
        Génère la documentation complète.
        
        Returns:
            {
                'job_name': str,
                'version': str,
                'markdown': str,           # Contenu Markdown
                'doc_data': Dict,          # Données du job
                'stats': Dict,             # Statistiques
                'screenshot_path': Path    # Chemin du screenshot
            }
        """
        # 1. Trouver tous les fichiers
        files = self.file_finder.find_all()
        
        # 2. Parser le .item
        item_parser = TalendItemParser(str(files['item']))
        job_data = item_parser.parse()
        
        # 3. Parser le .properties si disponible
        if files['properties']:
            props_parser = TalendPropertiesParser(str(files['properties']))
            properties_data = props_parser.parse()
            
            # Fusionner les métadonnées
            job_data['author'] = properties_data['author']
            job_data['created_at'] = properties_data['created_at']
            job_data['modified_at'] = properties_data['modified_at']
            if properties_data['description']:
                job_data['description'] = properties_data['description']
            job_data['category'] = properties_data['category_path']
        
        # 4. Générer la description avec LLM
        llm_description = None
        if self.config.get('use_llm') and self.llm_client:
            if self.llm_client.check_availability():
                llm_description = self.llm_client.generate_description(job_data)
            else:
                print("⚠️ Ollama non disponible, description par défaut utilisée")
                llm_description = self.llm_client._fallback_description(job_data)
        
        # 5. Générer les diagrammes
        diagram_gen = DiagramGenerator(self.config.get('diagram_type', 'mermaid'))
        diagram = diagram_gen.generate(job_data)
        
        # 6. Générer le Markdown
        md_gen = MarkdownGenerator(self.config)
        markdown_content = md_gen.generate(
            job_data,
            dependencies={},  # TODO: implémenter l'analyse des dépendances
            llm_description=llm_description
        )
        
        # 7. Préparer les données de retour
        return {
            'job_name': job_data['name'],
            'version': job_data['version'],
            'markdown': markdown_content,
            'doc_data': job_data,
            'stats': job_data['stats'],
            'screenshot_path': files.get('screenshot'),
            'generated_at': datetime.now().isoformat()
        }


# === EXEMPLE D'UTILISATION CLI ===

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Générateur de documentation Talend')
    parser.add_argument('item_path', help='Chemin vers le fichier .item')
    parser.add_argument('--detail', choices=['compact', 'standard', 'exhaustif'], 
                       default='standard', help='Niveau de détail')
    parser.add_argument('--diagram', choices=['mermaid', 'graphviz', 'both'], 
                       default='mermaid', help='Type de diagramme')
    parser.add_argument('--no-llm', action='store_true', help='Désactiver le LLM')
    parser.add_argument('--output', '-o', help='Fichier de sortie')
    
    args = parser.parse_args()
    
    # Configuration
    config = {
        'detail_level': args.detail.capitalize(),
        'diagram_type': args.diagram,
        'use_llm': not args.no_llm,
        'llm_model': 'llama3.2:latest',
        'include_screenshot': True,
        'include_contexts': True,
        'include_details': {
            'routines': args.detail == 'exhaustif',
            'joblets': args.detail == 'exhaustif',
            'connections': args.detail == 'exhaustif',
            'metadata': args.detail == 'exhaustif'
        }
    }
    
    # Génération
    generator = TalendDocGenerator(args.item_path, config)
    result = generator.generate()
    
    # Sauvegarder
    output_file = args.output or f"{result['job_name']}_doc.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result['markdown'])
    
    print(f"✅ Documentation générée : {output_file}")
    print(f"📊 Statistiques :")
    print(f"   - Composants : {result['stats']['nb_components']}")
    print(f"   - Connexions : {result['stats']['nb_connections']}")
    print(f"   - Variables : {result['stats']['nb_context_vars']}")
```

---

## 🧪 Tests unitaires

### 📝 Fixtures de test

```python
# tests/fixtures/sample_job.item
"""
Créer un fichier .item minimal pour les tests.
Contenir :
- 3 composants (tFileInputDelimited, tMap, tOracleOutput)
- 2 connexions (FLOW)
- 2 variables de contexte
"""
```

### 📝 Tests du parser

```python
# tests/test_parser.py

import pytest
from src.parser.item_parser import TalendItemParser

def test_parse_basic_job():
    """Test le parsing d'un job basique."""
    parser = TalendItemParser('tests/fixtures/sample_job.item')
    job_data = parser.parse()
    
    assert job_data['name'] == 'sample_job'
    assert job_data['version'] == '0.1'
    assert len(job_data['components']) == 3
    assert len(job_data['connections']) == 2

def test_parse_contexts():
    """Test le parsing des variables de contexte."""
    parser = TalendItemParser('tests/fixtures/sample_job.item')
    job_data = parser.parse()
    
    contexts = job_data['contexts']['Default']
    assert 'db_host' in contexts
    assert contexts['db_host']['type'] == 'String'

def test_component_categories():
    """Test la catégorisation des composants."""
    parser = TalendItemParser('tests/fixtures/sample_job.item')
    job_data = parser.parse()
    
    categories = [c['category'] for c in job_data['components']]
    assert 'Input' in categories
    assert 'Output' in categories
    assert 'Transform' in categories
```

---

## 📦 Requirements complet

```txt
# requirements.txt

# Parsing XML
lxml==5.1.0

# Configuration
pyyaml==6.0.1

# Templates
jinja2==3.1.2

# Markdown
markdown==3.5.1
pymdown-extensions==10.5

# Diagrammes
graphviz==0.20.1

# PDF
weasyprint==60.1
pypdf==3.17.4

# LLM
requests==2.31.0

# Interface
streamlit==1.29.0
streamlit-option-menu==0.3.6

# Images
Pillow==10.1.0

# Utilitaires
python-dateutil==2.8.2
rich==13.7.0

# CLI
click==8.1.7

# Tests
pytest==7.4.3
pytest-cov==4.1.0
```

---

## 🚀 Instructions de déploiement

### 1. Installation

```bash
# Cloner le repo
git clone <repo>
cd talend-doc-generator

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:latest
```

### 2. Configuration

```bash
# Éditer config.yaml pour personnaliser
cp config.yaml.example config.yaml
nano config.yaml
```

### 3. Lancement

```bash
# Interface Streamlit
streamlit run src/ui/streamlit_app.py

# CLI
python src/main.py path/to/job.item --detail standard --output doc.md
```

---

## 📚 Documentation pour Codex

### Ordre de développement recommandé

1. ✅ **Parser XML (.item)** → Fondation du projet
2. ✅ **Parser .properties** → Métadonnées
3. ✅ **File Finder** → Détection auto
4. ✅ **Générateur de diagrammes** → Visualisation
5. ✅ **Client LLM** → Description intelligente
6. ✅ **Générateur Markdown** → Assemblage final
7. ✅ **Export PDF** → Bonus
8. ✅ **Interface Streamlit** → UI finale
9. ✅ **Tests** → Qualité

### Points d'attention pour Codex

- **Gestion des namespaces XML** : Crucial pour XPath
- **Conversion des types Talend** : id_String → String
- **Gestion des erreurs** : Toujours avoir un fallback
- **Performance** : Parser peut être lent sur gros jobs (>200 composants)
- **Encodage** : Toujours UTF-8
- **Sécurité** : Valider les chemins de fichiers (éviter path traversal)

---

## ⚡ Quick Start (5 minutes)

1. **Installer depuis PyPI**  
   ```bash
   pip install talend-doc-gen
   ```
2. **Générer immédiatement un Markdown**  
   ```bash
   talend-doc-gen generate /chemin/job.item --detail standard --diagram mermaid
   ```
3. **Visualiser via Streamlit**  
   ```bash
   talend-doc-gen-ui
   # Ouvrir http://localhost:8501 et fournir le chemin du .item
   ```
4. **Exporter en PDF (optionnel)**  
   ```bash
   talend-doc-gen generate /chemin/job.item --pdf
   ```
5. **Consulter la documentation API**  
   ```bash
   sphinx-build -b html docs/api docs/api/_build/html
   open docs/api/_build/html/index.html
   ```

## 🧭 Guide utilisateur complet (≈30 minutes)

1. **Préparer l'environnement**
   - Installer Graphviz (`apt-get install graphviz`) pour les exports DOT.
   - Vérifier `ollama serve` si vous souhaitez les descriptions LLM.
   - Copier vos jobs `.item`, `.properties`, `.screenshot` dans un dossier accessible.
2. **Générer un premier job**
   - `talend-doc-gen generate data/job.item --detail exhaustif --diagram both --output docs/output/job.md`
   - Ouvrir `docs/output/job.md` pour vérifier le rendu.
3. **Personnaliser les templates**
   - Les templates Markdown sont dans `templates/` (embarqué dans le package). Dupliquez `job_standard.md`, ajoutez vos sections, puis passez `--template mon_template.md`.
4. **Analyse en batch**
   - `talend-doc-gen batch data/jobs/ --incremental` pour ne regénérer que les jobs modifiés.
   - Suivre la progression dans la console Rich.
5. **Statistiques détaillées**
   - `talend-doc-gen stats data/job.item --format yaml` pour intégrer des métriques dans vos pipelines CI/CD.
6. **Interface Streamlit**
   - Lancer `talend-doc-gen-ui`, uploader/indiquer le chemin du `.item`, télécharger Markdown et PDF directement depuis l'UI.
7. **Intégration CI**
   - Ajouter un job GitHub Actions : `pip install talend-doc-gen && talend-doc-gen batch data/jobs --incremental`.
8. **Publication**
   - Publier le Markdown/PDF dans Confluence, SharePoint ou GitHub Pages (voir section Sphinx ci-dessous).

## 🛠️ Guide développeur (≈1 heure)

1. **Installer en mode développement**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```
2. **Comprendre l'architecture**
   - `parser/`: lecture des `.item`, `.properties`, contextes.
   - `analyzer/`: normalisation, stats, génération des flux.
   - `generator/`: Markdown, PDF, diagrammes.
   - `llm/`: prompts et client Ollama.
   - `utils/`: cache, logs, recherche des fichiers et ressources embarquées.
3. **Ajouter un nouveau parser ou plugin**
   - Créer un module dans `parser/` ou `generator/plugins/`.
   - Ajouter des tests dans `tests/` avec des fixtures `.item` dédiées.
   - Exposer les nouveaux types dans `MarkdownGenerator`.
4. **Travailler sur les templates**
   - Les templates sont chargés via `utils.resource_finder.find_assets_root()`. Vérifiez que vos nouveaux fichiers sont inclus dans `talend_doc_gen_assets`.
5. **Packaging & distribution**
   - Le package PyPI est défini dans `setup.py` (`talend-doc-gen`).
   - Inclut `config.yaml` + `templates/*.md` pour une installation autonome.
   - Tester l'installation locale : `pip install .` puis `talend-doc-gen --help`.
6. **Tests et qualité**
   - `python -m compileall src`
   - `pytest --maxfail=1`
   - `sphinx-build -b html docs/api docs/api/_build/html` pour vérifier la doc.
7. **Profilage**
   - Ajouter `--profile` sur `generate` ou `batch` pour produire un rapport SnakeViz.
8. **Release**
   - Mettre à jour `CHANGELOG.md`, tagger la version, publier sur PyPI, puis déployer la doc HTML sur GitHub Pages.

## 📖 Documentation API (Sphinx + GitHub Pages)

1. **Installation locale**
   ```bash
   pip install sphinx sphinx-rtd-theme
   ```
2. **Génération HTML**
   ```bash
   sphinx-build -b html docs/api docs/api/_build/html
   ```
3. **Aperçu**
   - Ouvrir `docs/api/_build/html/index.html`.
4. **Publication sur GitHub Pages**
   - Copier le contenu de `docs/api/_build/html` dans le dossier `docs/` de la branche principale **ou** pousser sur la branche `gh-pages`.
   - Dans GitHub > Settings > Pages, choisir la source `gh-pages` (ou `/docs`).
   - Les assets (CSS/JS) sont inclus, aucun backend n'est requis.
5. **Regénération automatique**
   - Ajouter un workflow CI :
     ```yaml
     - name: Build Sphinx
       run: sphinx-build -b html docs/api docs/api/_build/html
     - name: Deploy to gh-pages
       uses: peaceiris/actions-gh-pages@v3
       with:
         publish_dir: docs/api/_build/html
     ```

## ❓ FAQ (10+ questions)

1. **Quelle est la commande la plus simple pour générer un job ?**  
   `talend-doc-gen generate mon_job.item --detail standard`
2. **Puis-je désactiver le LLM ?**  
   Oui, ajoutez `--no-llm` (CLI) ou décochez dans l'UI Streamlit.
3. **Graphviz est-il obligatoire ?**  
   Non pour Mermaid, oui pour les rendus Graphviz (`--diagram graphviz` ou `both`).
4. **Où sont stockés les outputs ?**  
   Par défaut dans `docs/output/`, modifiable via `config.yaml`.
5. **Comment changer le template Markdown ?**  
   Dupliquez un template dans `templates/` et passez `--template <nom>.md`.
6. **Comment purger le cache ?**  
   Utilisez `--no-cache` ou supprimez le dossier indiqué par `utils.cache_manager.get_cache_manager().cache_dir`.
7. **Puis-je lancer plusieurs jobs en parallèle ?**  
   Oui, l'option `--workers` sur `batch` contrôle le parallélisme (ProcessPool + ThreadPool).
8. **Comment obtenir des stats YAML ?**  
   `talend-doc-gen stats job.item --format yaml`.
9. **L'UI Streamlit supporte-t-elle les PDF ?**  
   Oui, activez la case "Exporter en PDF" dans la barre latérale.
10. **Comment forcer un layout vertical Mermaid ?**  
    Changez `diagrams.style` dans `config.yaml` (ex: `LR`, `TB`, `TD`).
11. **Le projet supporte-t-il Talend Cloud ?**  
    La roadmap 2.0.0 prévoit le support natif ; en attendant, utilisez les exports `.item`.

## 🩺 Troubleshooting

- **Erreur `OSError: Graphviz executables not found`**  
  Installer Graphviz (`apt-get install graphviz`) puis relancer `talend-doc-gen`.
- **Connexion Ollama impossible**  
  Vérifier que `ollama serve` tourne sur `http://localhost:11434` ou mettre à jour `config.yaml`.
- **Streamlit ne démarre pas (port occupé)**  
  Lancer `talend-doc-gen-ui --server.port 8502`.
- **PDF vide ou tronqué**  
  Vérifier la présence du screenshot `.screenshot` et la police configurée dans `config.yaml`.
- **Templates introuvables après installation pip**  
  Confirmer que `talend_doc_gen_assets` est installé (`python -c "import talend_doc_gen_assets; print(talend_doc_gen_assets.__file__)"`).
- **Crash sur fichiers volumineux**  
  Activer `--no-cache` pour forcer un parsing propre et augmenter `--workers` prudemment.
- **Timeout LLM**  
  Augmenter `ollama.timeout` dans `config.yaml` ou désactiver le LLM avec `--no-llm`.
- **EncodingError sur Windows**  
  Exporter `PYTHONIOENCODING=utf-8` avant de lancer la CLI.
