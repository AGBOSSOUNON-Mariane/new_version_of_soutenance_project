import os
import pandas as pd
from docx import Document
from pathlib import Path
import re
from tqdm import tqdm
import urllib.parse

def extract_text_and_sources(docx_path):
    """
    Extrait le texte et sépare le contenu principal des sources/références
    VERSION CORRIGÉE pour capturer TOUTES les sources
    """
    try:
        doc = Document(docx_path)
        all_text = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                all_text.append(paragraph.text.strip())
        
        full_text = '\n'.join(all_text)
        
        # CORRECTION: Pattern plus robuste qui capture TOUT après "Sources et références"
        patterns = [
            r'Sources?\s*et?\s*[Rr]éférences?\s*[:•\-\n]*(.*)',
            r'Bibliographie\s*[:•\-\n]*(.*)',
            r'Références?\s*[Bb]ibliographiques?\s*[:•\-\n]*(.*)',
            r'Notes?\s*et?\s*[Rr]éférences?\s*[:•\-\n]*(.*)',
        ]
        
        sources_text = ""
        main_text = full_text
        
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                sources_text = match.group(1).strip()
                # Retirer le texte des sources du contenu principal
                main_text = full_text[:match.start()].strip()
                break
        
        # Si pas trouvé avec les patterns, chercher ligne par ligne
        if not sources_text:
            lines = all_text
            sources_start = -1
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                # Rechercher "Sources et références" ou variantes
                if re.search(r'^sources?\s*et?\s*références?', line_lower):
                    sources_start = i + 1  # Commencer APRÈS la ligne titre
                    break
                elif re.search(r'^bibliographie', line_lower):
                    sources_start = i + 1
                    break
            
            if sources_start != -1:
                # Collecter TOUTES les lignes après le titre de section
                sources_lines = lines[sources_start:]
                sources_text = '\n'.join(sources_lines)
                main_text = '\n'.join(lines[:sources_start-1])  # -1 pour exclure le titre
        
        return main_text.strip(), sources_text.strip()
        
    except Exception as e:
        print(f"Erreur lors de la lecture de {docx_path}: {e}")
        return "", ""

def parse_sources_list(sources_text):
    """
    Parse le texte des sources pour extraire les informations structurées
    VERSION CORRIGÉE pour gérer tous les formats de puces
    """
    if not sources_text:
        return []
    
    sources_list = []
    lines = sources_text.split('\n')
    current_source = ""
    
    for line in lines:
        line = line.strip()
        
        # Ignorer les lignes vides
        if not line:
            continue
        
        # Ignorer les titres de section résiduels
        if re.search(r'^sources?\s*et?\s*références?', line, re.IGNORECASE):
            continue
        
        # Détecter les lignes avec des puces (•, -, *, ·, o, etc.)
        bullet_match = re.match(r'^[•\-\*·o]\s*(.+)', line)
        
        if bullet_match:
            # Si on a une source en cours, la sauvegarder
            if current_source:
                sources_list.append(parse_single_source(current_source))
            
            # Commencer une nouvelle source
            current_source = bullet_match.group(1).strip()
        
        # Si ligne commence par une URL (cas rare mais possible)
        elif line.startswith('http'):
            if current_source:
                current_source += ' ' + line
            else:
                current_source = line
        
        # Continuation de la source précédente (URL sur ligne suivante)
        elif current_source and ('http' in line or len(line) > 20):
            current_source += ' ' + line
        
        # Ligne de texte autonome (sans puce mais avec contenu)
        elif len(line) > 10 and not re.search(r'^[A-ZÀ-Ü\s]+$', line):
            if current_source:
                sources_list.append(parse_single_source(current_source))
            sources_list.append(parse_single_source(line))
            current_source = ""
    
    # Ne pas oublier la dernière source
    if current_source:
        sources_list.append(parse_single_source(current_source))
    
    return sources_list

def parse_single_source(source_text):
    """
    Parse une seule source pour extraire ses composants
    """
    source_dict = {
        'source_name': "",
        'description': "",
        'url': "",
        'source_type': "texte",
        'raw_text': source_text
    }
    
    # Extraire l'URL (si présente)
    url_match = re.search(r'https?://[^\s,\)]+', source_text)
    if url_match:
        source_dict['url'] = url_match.group(0)
        # Enlever l'URL du texte pour faciliter le parsing
        text_without_url = source_text.replace(source_dict['url'], '').strip()
        text_without_url = text_without_url.rstrip(',').strip()
    else:
        text_without_url = source_text
    
    # Parser la structure "Source — Description"
    if '—' in text_without_url:
        parts = text_without_url.split('—', 1)
        source_dict['source_name'] = parts[0].strip()
        source_dict['description'] = parts[1].strip()
    elif '–' in text_without_url:  # tiret moyen
        parts = text_without_url.split('–', 1)
        source_dict['source_name'] = parts[0].strip()
        source_dict['description'] = parts[1].strip()
    else:
        # Pas de séparateur, tout est dans la description
        source_dict['description'] = text_without_url
    
    # Déterminer le type de source
    full_text_lower = source_text.lower()
    if 'wikipédia' in full_text_lower or 'wikipedia' in full_text_lower:
        source_dict['source_type'] = "wikipédia"
    elif any(domain in source_dict['url'] for domain in ['.gov', '.gouv', 'unesco']):
        source_dict['source_type'] = "gouvernemental"
    elif any(domain in source_dict['url'] for domain in ['academia', 'research', 'journal']):
        source_dict['source_type'] = "académique"
    elif source_dict['url'] and any(ext in source_dict['url'] for ext in ['.com', '.fr', '.org', '.net']):
        source_dict['source_type'] = "blog"
    
    return source_dict

def extract_urls_from_text(text):
    """Extrait toutes les URLs d'un texte"""
    url_pattern = r'https?://[^\s,\)\]>]+'
    urls = re.findall(url_pattern, text)
    # Nettoyer les URLs (enlever ponctuation finale)
    cleaned_urls = []
    for url in urls:
        url = url.rstrip('.,;:')
        cleaned_urls.append(url)
    return list(set(cleaned_urls))  # Éliminer les doublons

def analyze_source_format(sources_text):
    """Analyse le format des sources pour comprendre la structure"""
    if not sources_text:
        return {
            'has_bullets': False,
            'has_urls': False,
            'bullet_type': None,
            'url_count': 0,
            'source_count': 0
        }
    
    lines = sources_text.split('\n')
    stats = {
        'has_bullets': any(re.match(r'^[•\-\*·o]\s', line.strip()) for line in lines),
        'has_urls': bool(extract_urls_from_text(sources_text)),
        'bullet_type': None,
        'url_count': len(extract_urls_from_text(sources_text)),
        'source_count': 0
    }
    
    # Compter les sources (lignes avec puces)
    source_lines = [line for line in lines if re.match(r'^[•\-\*·o]\s', line.strip())]
    stats['source_count'] = len(source_lines)
    
    # Identifier le type de puce
    for line in lines:
        if line.strip().startswith('•'):
            stats['bullet_type'] = '•'
            break
        elif line.strip().startswith('·'):
            stats['bullet_type'] = '·'
            break
        elif line.strip().startswith('-'):
            stats['bullet_type'] = '-'
            break
        elif line.strip().startswith('*'):
            stats['bullet_type'] = '*'
            break
    
    return stats

def clean_filename(filename):
    """Nettoie le nom de fichier pour extraire le titre"""
    name = filename.replace('.docx', '').replace('.DOCX', '')
    name = name.replace('_', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_category_from_path(file_path, base_path):
    """Extrait les catégories et sous-catégories du chemin"""
    relative_path = os.path.relpath(file_path, base_path)
    parts = relative_path.split(os.sep)
    
    site = parts[0] if len(parts) > 0 else "Unknown"
    category = parts[1] if len(parts) > 1 else "General"
    subcategory = parts[2] if len(parts) > 2 else "None"
    
    return site, category, subcategory

def clean_image_filename(filename):
    """Nettoie le nom d'un fichier image"""
    clean = re.sub(r'\s*\([^)]*\)', '', filename)
    clean = clean.strip()
    return clean

def get_associated_images(docx_path):
    """Récupère et nettoie la liste des images associées"""
    try:
        doc_dir = os.path.dirname(docx_path)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        all_images = []
        
        for file in os.listdir(doc_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                clean_name = clean_image_filename(file)
                all_images.append(clean_name)
        
        return sorted(list(set(all_images)))
    except Exception as e:
        return []

def create_dataset_from_structure(base_path):
    """
    Crée un dataset structuré avec sources parsées
    VERSION CORRIGÉE
    """
    data = []
    
    if not os.path.exists(base_path):
        print(f"ERREUR: Le chemin {base_path} n'existe pas!")
        return pd.DataFrame()
    
    # Rechercher tous les fichiers .docx
    docx_files = list(Path(base_path).rglob("*.docx"))
    docx_files += list(Path(base_path).rglob("*.DOCX"))
    
    # Filtrer les fichiers temporaires
    docx_files = [f for f in docx_files if not os.path.basename(str(f)).startswith('~$')]
    
    print(f"Nombre total de fichiers .docx trouvés: {len(docx_files)}")
    print("Extraction et analyse des sources en cours...")
    
    for docx_file in tqdm(docx_files, desc="Traitement des documents"):
        try:
            # Extraire le contenu et les sources
            main_content, sources_content = extract_text_and_sources(str(docx_file))
            
            if not main_content.strip():
                continue
            
            # Parser les sources
            sources_list = parse_sources_list(sources_content)
            source_stats = analyze_source_format(sources_content)
            
            # Extraire les métadonnées
            site, category, subcategory = extract_category_from_path(docx_file, base_path)
            filename = os.path.basename(docx_file)
            title = clean_filename(filename)
            
            # Statistiques
            main_char_count = len(main_content)
            main_word_count = len(main_content.split())
            sources_char_count = len(sources_content)
            sources_word_count = len(sources_content.split())
            
            # URLs extraites
            all_urls = extract_urls_from_text(sources_content)
            
            # Images associées
            associated_images = get_associated_images(str(docx_file))
            
            # Créer l'entrée
            entry = {
                'site': site,
                'category': category,
                'subcategory': subcategory,
                'filename_doc': filename,
                'title': title,
                'content_main': main_content,
                'content_sources': sources_content,
                'sources_parsed': sources_list,
                'sources_count': len(sources_list),
                'sources_stats': source_stats,
                'urls': all_urls,
                'url_count': len(all_urls),
                'content_combined': f"{main_content}\n\n=== SOURCES ===\n{sources_content}" if sources_content else main_content,
                'char_count_main': main_char_count,
                'word_count_main': main_word_count,
                'char_count_sources': sources_char_count,
                'word_count_sources': sources_word_count,
                'total_char_count': main_char_count + sources_char_count,
                'total_word_count': main_word_count + sources_word_count,
                'has_sources': bool(sources_content.strip()),
                'has_structured_sources': len(sources_list) > 0,
                'image_count': len(associated_images),
                'images': associated_images,
                'images_list': '|||'.join(associated_images) if associated_images else "Aucune",
                'path': str(docx_file),
                'directory': os.path.dirname(str(docx_file)),
                'source_category': f"{category}/{subcategory}"
            }
            
            data.append(entry)
            
        except Exception as e:
            print(f"\n❌ Erreur avec le fichier {docx_file}: {e}")
            continue
    
    df = pd.DataFrame(data)
    return df

def analyze_source_types(df):
    """Analyse détaillée des types de sources"""
    if df.empty:
        return
    
    print("\n" + "="*60)
    print("ANALYSE DES TYPES DE SOURCES")
    print("="*60)
    
    all_sources = []
    for _, row in df.iterrows():
        if row['sources_parsed']:
            for source in row['sources_parsed']:
                source['document_title'] = row['title']
                source['site'] = row['site']
                all_sources.append(source)
    
    if not all_sources:
        print("Aucune source structurée trouvée.")
        return
    
    sources_df = pd.DataFrame(all_sources)
    
    print("\n📊 RÉPARTITION PAR TYPE DE SOURCE:")
    type_counts = sources_df['source_type'].value_counts()
    for source_type, count in type_counts.items():
        percentage = count / len(sources_df) * 100
        print(f"  • {source_type:<15}: {count:>3} ({percentage:.1f}%)")
    
    print("\n🏆 TOP 10 DES SOURCES LES PLUS FRÉQUENTES:")
    source_counts = sources_df['source_name'].value_counts().head(10)
    for source_name, count in source_counts.items():
        if source_name:
            print(f"  • {source_name[:40]:<40}: {count:>2} occurrences")
    
    print(f"\n🌐 ANALYSE DES URLs:")
    print(f"  • Documents avec URLs: {len(df[df['url_count'] > 0])}/{len(df)}")
    print(f"  • URLs totales: {df['url_count'].sum()}")
    
    domains = {}
    for urls in df['urls']:
        for url in urls:
            try:
                domain = urllib.parse.urlparse(url).netloc
                domains[domain] = domains.get(domain, 0) + 1
            except:
                pass
    
    if domains:
        print("\n🔗 DOMAINES LES PLUS COURANTS:")
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
        for domain, count in sorted_domains:
            print(f"  • {domain:<40}: {count:>3}")
    
    return sources_df

def display_source_examples(df, num_examples=5):
    """Affiche des exemples de sources extraites"""
    print("\n" + "="*60)
    print("EXEMPLES DE SOURCES EXTRACTES")
    print("="*60)
    
    docs_with_sources = df[df['has_structured_sources']].head(num_examples)
    
    for idx, row in docs_with_sources.iterrows():
        print(f"\n📄 {row['site']} - {row['title']}:")
        print(f"   Sources trouvées: {row['sources_count']} | URLs: {row['url_count']}")
        
        if row['sources_parsed']:
            for i, source in enumerate(row['sources_parsed'], 1):
                print(f"\n   [{i}] {source['source_name'] or 'Sans nom'}")
                if source['description']:
                    print(f"       Description: {source['description'][:80]}...")
                if source['url']:
                    print(f"       URL: {source['url'][:80]}...")
                print(f"       Type: {source['source_type']}")

def save_dataset_with_excel(df, output_base="data/df_unified"):
    """Sauvegarde le dataset en CSV et Excel"""
    if df.empty:
        print("Le DataFrame est vide, impossible de sauvegarder.")
        return
    
    os.makedirs(os.path.dirname(output_base), exist_ok=True)
    
    # CSV
    csv_path = f"{output_base}.csv"
    df_for_csv = df.copy()
    
    df_for_csv['sources_parsed_str'] = df_for_csv['sources_parsed'].apply(
        lambda x: ' | '.join([f"{s['source_name']}: {s['url']}" for s in x]) if x else ""
    )
    df_for_csv['urls_str'] = df_for_csv['urls'].apply(
        lambda x: ' | '.join(x) if x else ""
    )
    df_for_csv['images_str'] = df_for_csv['images'].apply(
        lambda x: ' | '.join(x) if x else ""
    )
    
    cols_to_drop = ['sources_parsed', 'urls', 'images', 'sources_stats']
    df_csv = df_for_csv.drop(columns=[c for c in cols_to_drop if c in df_for_csv.columns])
    
    df_csv.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n✅ Dataset principal sauvegardé: {csv_path}")
    
    # Excel
    excel_path = f"{output_base}.xlsx"
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_csv.to_excel(writer, sheet_name='Documents', index=False)
        
        # Sources détaillées
        all_sources = []
        for _, row in df.iterrows():
            if row['sources_parsed']:
                for source in row['sources_parsed']:
                    all_sources.append({
                        'site': row['site'],
                        'document': row['title'],
                        'source_name': source.get('source_name', ''),
                        'description': source.get('description', ''),
                        'url': source.get('url', ''),
                        'source_type': source.get('source_type', ''),
                        'raw_text': source.get('raw_text', '')
                    })
        
        if all_sources:
            sources_df = pd.DataFrame(all_sources)
            sources_df.to_excel(writer, sheet_name='Sources_détaillées', index=False)
        
        # Statistiques
        stats_data = {
            'Métrique': [
                'Total documents',
                'Documents avec sources',
                'Documents avec sources structurées',
                'Sources totales extraites',
                'URLs totales',
                'Images totales'
            ],
            'Valeur': [
                len(df),
                len(df[df['has_sources']]),
                len(df[df['has_structured_sources']]),
                df['sources_count'].sum(),
                df['url_count'].sum(),
                df['image_count'].sum()
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        # Par site
        site_stats = df.groupby('site').agg({
            'filename_doc': 'count',
            'has_sources': 'sum',
            'has_structured_sources': 'sum',
            'sources_count': 'sum',
            'url_count': 'sum',
            'image_count': 'sum'
        }).reset_index()
        
        site_stats.columns = ['Site', 'Documents', 'Avec sources', 
                             'Avec sources structurées', 'Nombre sources', 'URLs', 'Images']
        site_stats.to_excel(writer, sheet_name='Par_site', index=False)
    
    print(f"✅ Dataset Excel complet sauvegardé: {excel_path}")
    return csv_path, excel_path

if __name__ == "__main__":
    BASE_PATH = "Donnees_soutenance"
    
    print("📁 CRÉATION DU DATASET AVEC SOURCES COMPLÈTES")
    print("="*70)
    
    df = create_dataset_from_structure(BASE_PATH)
    
    if not df.empty:
        csv_path, excel_path = save_dataset_with_excel(df)
        
        print("\n" + "="*70)
        print("RÉSUMÉ DU DATASET")
        print("="*70)
        
        print(f"\n📊 STATISTIQUES GLOBALES:")
        print(f"  • Documents totaux: {len(df)}")
        print(f"  • Avec sources: {len(df[df['has_sources']])} ({len(df[df['has_sources']])/len(df)*100:.1f}%)")
        print(f"  • Avec sources structurées: {len(df[df['has_structured_sources']])} ({len(df[df['has_structured_sources']])/len(df)*100:.1f}%)")
        print(f"  • Sources totales extraites: {df['sources_count'].sum()}")
        print(f"  • URLs trouvées: {df['url_count'].sum()}")
        print(f"  • Images associées: {df['image_count'].sum()}")
        
        print(f"\n📍 PAR SITE:")
        for site in df['site'].unique():
            site_df = df[df['site'] == site]
            structured = len(site_df[site_df['has_structured_sources']])
            total = len(site_df)
            sources_total = site_df['sources_count'].sum()
            print(f"  • {site:<12}: {total:>2} docs | {structured:>2} structurés | {sources_total:>3} sources")
        
        analyze_source_types(df)
        display_source_examples(df)
        
        print("\n" + "="*70)
        print("✅ DATASET CRÉÉ AVEC SUCCÈS !")
        print("="*70)
    else:
        print("\n❌ Aucun document traité.")