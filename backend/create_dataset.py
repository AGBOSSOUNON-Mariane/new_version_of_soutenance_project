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
    Adaptation spécifique pour le format avec puces • et URLs
    """
    try:
        doc = Document(docx_path)
        all_text = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                all_text.append(paragraph.text.strip())
        
        full_text = '\n'.join(all_text)
        
        # Chercher la section "Sources et références"
        # Patterns plus spécifiques pour le format donné
        patterns = [
            r'(Sources?\s*et?\s*Références?[\s\:\-\n]*)(.*?)(?=\n\n|$|\n[A-Z]|\n•[^•]|\n\d)',
            r'(Bibliographie[\s\:\-\n]*)(.*?)(?=\n\n|$|\n[A-Z]|\n•[^•]|\n\d)',
            r'(Références?\s*Bibliographiques?[\s\:\-\n]*)(.*?)(?=\n\n|$|\n[A-Z]|\n•[^•]|\n\d)',
            r'(Notes?\s*et?\s*Références?[\s\:\-\n]*)(.*?)(?=\n\n|$|\n[A-Z]|\n•[^•]|\n\d)',
        ]
        
        sources_text = ""
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                sources_text = match.group(2).strip()
                # Retirer le texte des sources du contenu principal
                main_text = full_text.replace(match.group(0), '').strip()
                return main_text, sources_text
        
        # Si pas trouvé avec les patterns, chercher ligne par ligne
        if not sources_text:
            lines = all_text
            sources_start = -1
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                # Rechercher plus précisément "Sources et références"
                if re.search(r'^sources?\s*et?\s*références?\s*$', line_lower) or \
                   re.search(r'^bibliographie\s*$', line_lower):
                    sources_start = i
                    break
                # Ou une ligne qui commence par "Sources" avec des deux-points
                elif re.search(r'^sources?\s*[:]', line_lower):
                    sources_start = i
                    break
            
            if sources_start != -1:
                # Collecter toutes les lignes jusqu'à la prochaine section majeure
                sources_lines = []
                for j in range(sources_start, len(lines)):
                    sources_lines.append(lines[j])
                    # S'arrêter si on rencontre une nouvelle section (titre en majuscule)
                    if j < len(lines)-1 and re.search(r'^[A-ZÀ-Ü][A-ZÀ-Ü\s]+$', lines[j+1]):
                        break
                    # S'arrêter si on rencontre un nouveau titre de section
                    if j < len(lines)-1 and len(lines[j+1]) < 100 and re.search(r'^[A-Z]', lines[j+1]):
                        break
                
                sources_text = '\n'.join(sources_lines)
                main_text = '\n'.join(lines[:sources_start])
                return main_text.strip(), sources_text.strip()
        
        return full_text.strip(), ""
        
    except Exception as e:
        print(f"Erreur lors de la lecture de {docx_path}: {e}")
        return "", ""

def parse_sources_list(sources_text):
    """
    Parse le texte des sources pour extraire les informations structurées
    Format attendu: • Wikipédia (FR) — Amazones du Dahomey / Agodjié, https://...
    """
    if not sources_text:
        return []
    
    sources_list = []
    lines = sources_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Ignorer les titres de section
        if re.search(r'^sources?\s*et?\s*références?', line, re.IGNORECASE) or \
           re.search(r'^===.*===$', line):
            continue
        
        # Détecter les lignes avec des puces
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            source_item = line[1:].strip()  # Enlever la puce
            
            # Séparer la description de l'URL
            parts = source_item.split(', http')
            if len(parts) > 1:
                description = parts[0].strip()
                url = 'http' + parts[1].strip()
                
                # Extraire le nom de la source (ex: "Wikipédia (FR)")
                source_match = re.match(r'^([^—]+)—\s*(.+)$', description)
                if source_match:
                    source_name = source_match.group(1).strip()
                    source_desc = source_match.group(2).strip()
                else:
                    source_name = description.split('—')[0].strip() if '—' in description else description
                    source_desc = description.split('—')[1].strip() if '—' in description else ""
                
                # Extraire le type de source
                source_type = "autre"
                if 'wikipédia' in source_name.lower():
                    source_type = "wikipédia"
                elif 'blog' in url or '.com' in url:
                    source_type = "blog"
                elif 'academia' in url or 'research' in url:
                    source_type = "académique"
                elif 'gov' in url or 'gouv' in url:
                    source_type = "gouvernemental"
                
                sources_list.append({
                    'source_name': source_name,
                    'description': source_desc,
                    'url': url,
                    'source_type': source_type,
                    'raw_text': line
                })
            else:
                # Si pas d'URL, garder le texte brut
                sources_list.append({
                    'source_name': "",
                    'description': source_item,
                    'url': "",
                    'source_type': "texte",
                    'raw_text': line
                })
        elif line and not re.search(r'^[A-ZÀ-Ü\s]+$', line):  # Ignorer les titres tout en majuscules
            # Pour les lignes sans puce mais qui pourraient être des sources
            sources_list.append({
                'source_name': "",
                'description': line,
                'url': "",
                'source_type': "texte",
                'raw_text': line
            })
    
    return sources_list

def extract_urls_from_text(text):
    """Extrait toutes les URLs d'un texte"""
    url_pattern = r'https?://[^\s,\]]+'
    urls = re.findall(url_pattern, text)
    return urls

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
        'has_bullets': any(line.strip().startswith(('•', '-', '*')) for line in lines),
        'has_urls': bool(extract_urls_from_text(sources_text)),
        'bullet_type': None,
        'url_count': len(extract_urls_from_text(sources_text)),
        'source_count': 0
    }
    
    # Compter les sources (lignes avec puces)
    source_lines = [line for line in lines if line.strip().startswith(('•', '-', '*'))]
    stats['source_count'] = len(source_lines)
    
    # Identifier le type de puce
    for line in lines:
        if line.strip().startswith('•'):
            stats['bullet_type'] = '•'
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

def get_associated_images(docx_path):
    """Récupère et nettoie la liste des images associées"""
    try:
        doc_dir = os.path.dirname(docx_path)
        doc_name = os.path.basename(docx_path).replace('.docx', '').replace('.DOCX', '')
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.JPG', '.JPEG', '.PNG']
        all_images = []
        
        for file in os.listdir(doc_dir):
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in image_extensions):
                # AJOUTE ICI LE NETTOYAGE DES NOMS
                clean_name = clean_image_filename(file)
                all_images.append(clean_name)
        
        return sorted(list(set(all_images)))
    except Exception as e:
        print(f"Erreur images pour {docx_path}: {e}")
        return []

def clean_image_filename(filename):
    """Nettoie le nom d'un fichier image"""
    # Enlever les annotations entre parenthèses
    import re
    clean = re.sub(r'\s*\([^)]*\)', '', filename)
    # Nettoyer les espaces en début/fin
    clean = clean.strip()
    return clean

def create_dataset_from_structure(base_path):
    """
    Crée un dataset structuré avec sources parsées
    """
    data = []
    
    if not os.path.exists(base_path):
        print(f"ERREUR: Le chemin {base_path} n'existe pas!")
        return pd.DataFrame()
    
    # Rechercher tous les fichiers .docx
    docx_files = list(Path(base_path).rglob("*.docx"))
    docx_files += list(Path(base_path).rglob("*.DOCX"))
    
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
                'sources_parsed': sources_list,  # Liste structurée des sources
                'sources_count': len(sources_list),
                'sources_stats': source_stats,  # Statistiques sur le format
                'urls': all_urls,  # Liste des URLs
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
    
    # Créer le DataFrame
    df = pd.DataFrame(data)
    
    return df

def analyze_source_types(df):
    """Analyse détaillée des types de sources"""
    if df.empty:
        return
    
    print("\n" + "="*60)
    print("ANALYSE DES TYPES DE SOURCES")
    print("="*60)
    
    # Collecter toutes les sources parsées
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
    
    # Créer un DataFrame des sources
    sources_df = pd.DataFrame(all_sources)
    
    # Statistiques par type de source
    print("\n📊 RÉPARTITION PAR TYPE DE SOURCE:")
    type_counts = sources_df['source_type'].value_counts()
    for source_type, count in type_counts.items():
        percentage = count / len(sources_df) * 100
        print(f"  • {source_type:<15}: {count:>3} ({percentage:.1f}%)")
    
    # Sources les plus fréquentes
    print("\n🏆 TOP 10 DES SOURCES LES PLUS FRÉQUENTES:")
    source_counts = sources_df['source_name'].value_counts().head(10)
    for source_name, count in source_counts.items():
        if source_name:
            print(f"  • {source_name[:40]:<40}: {count:>2} occurrences")
    
    # Analyse des URLs
    print(f"\n🌐 ANALYSE DES URLs:")
    print(f"  • Documents avec URLs: {len(df[df['url_count'] > 0])}/{len(df)}")
    print(f"  • URLs totales: {df['url_count'].sum()}")
    
    # Domains les plus fréquents
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
    
    # Prendre des documents avec sources structurées
    docs_with_sources = df[df['has_structured_sources']].head(num_examples)
    
    for idx, row in docs_with_sources.iterrows():
        print(f"\n📄 {row['site']} - {row['title']}:")
        print(f"   Format: {row['sources_stats']['bullet_type'] or 'texte'} | Sources: {row['sources_count']} | URLs: {row['url_count']}")
        
        if row['sources_parsed']:
            for i, source in enumerate(row['sources_parsed'][:3], 1):
                if source['url']:
                    print(f"   {i}. {source['source_name']} - {source['description'][:60]}...")
                    print(f"      URL: {source['url'][:80]}...")
                else:
                    print(f"   {i}. {source['description'][:80]}...")
        
        if len(row['sources_parsed']) > 3:
            print(f"   ... et {len(row['sources_parsed']) - 3} autres sources")

def save_dataset_with_excel(df, output_base="data/df_unified"):
    """
    Sauvegarde le dataset en CSV et Excel avec feuilles séparées
    """
    if df.empty:
        print("Le DataFrame est vide, impossible de sauvegarder.")
        return
    
    os.makedirs(os.path.dirname(output_base), exist_ok=True)
    
    # 1. Sauvegarder le DataFrame principal en CSV
    csv_path = f"{output_base}.csv"
    
    # Pour sauvegarder en CSV, on doit simplifier certaines colonnes
    df_for_csv = df.copy()
    
    # Convertir les listes en strings pour CSV
    df_for_csv['sources_parsed_str'] = df_for_csv['sources_parsed'].apply(
        lambda x: ' | '.join([str(s) for s in x]) if x else ""
    )
    df_for_csv['urls_str'] = df_for_csv['urls'].apply(
        lambda x: ' | '.join(x) if x else ""
    )
    df_for_csv['images_str'] = df_for_csv['images'].apply(
        lambda x: ' | '.join(x) if x else ""
    )
    
    # Colonnes à exclure du CSV
    cols_to_drop = ['sources_parsed', 'urls', 'images', 'sources_stats']
    df_csv = df_for_csv.drop(columns=[c for c in cols_to_drop if c in df_for_csv.columns])
    
    df_csv.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n✅ Dataset principal sauvegardé: {csv_path}")
    
    # 2. Sauvegarder en Excel avec plusieurs feuilles
    excel_path = f"{output_base}.xlsx"
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Feuille 1: Données principales
        df_csv.to_excel(writer, sheet_name='Documents', index=False)
        
        # Feuille 2: Sources détaillées
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
        
        # Feuille 3: Statistiques
        stats_data = {
            'Métrique': [
                'Total documents',
                'Documents avec sources',
                'Documents sans sources',
                'Documents avec sources structurées',
                'Sources totales extraites',
                'URLs totales',
                'Images totales référencées',
                'Mots totaux (contenu)',
                'Mots totaux (sources)'
            ],
            'Valeur': [
                len(df),
                len(df[df['has_sources']]),
                len(df[~df['has_sources']]),
                len(df[df['has_structured_sources']]),
                df['sources_count'].sum(),
                df['url_count'].sum(),
                df['image_count'].sum(),
                df['word_count_main'].sum(),
                df['word_count_sources'].sum()
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
        
        # Feuille 4: Par site
        site_stats = df.groupby('site').agg({
            'filename_doc': 'count',
            'has_sources': 'sum',
            'has_structured_sources': 'sum',
            'sources_count': 'sum',
            'url_count': 'sum',
            'image_count': 'sum',
            'word_count_main': 'sum'
        }).reset_index()
        
        site_stats.columns = ['Site', 'Documents', 'Avec sources', 'Avec sources structurées', 
                             'Nombre sources', 'URLs', 'Images', 'Mots']
        site_stats.to_excel(writer, sheet_name='Par_site', index=False)
    
    print(f"✅ Dataset Excel complet sauvegardé: {excel_path}")
    
    return csv_path, excel_path

if __name__ == "__main__":
    # Configuration
    BASE_PATH = "Donnees_soutenance"
    
    print("📁 CRÉATION DU DATASET AVEC SOURCES STRUCTURÉES")
    print("="*70)
    print("Format attendu: • Wikipédia (FR) — Amazones du Dahomey / Agodjié, https://...")
    print("="*70)
    
    # Créer le dataset
    df = create_dataset_from_structure(BASE_PATH)
    
    if not df.empty:
        # Sauvegarder
        csv_path, excel_path = save_dataset_with_excel(df)
        
        # Analyses
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
        
        # Analyse par site
        print(f"\n📍 PAR SITE:")
        for site in df['site'].unique():
            site_df = df[df['site'] == site]
            structured = len(site_df[site_df['has_structured_sources']])
            total = len(site_df)
            print(f"  • {site:<12}: {total:>2} docs | {structured:>2} structurés ({structured/total*100:.0f}%) | {site_df['sources_count'].sum():>3} sources")
        
        # Analyse détaillée des sources
        sources_df = analyze_source_types(df)
        
        # Afficher des exemples
        display_source_examples(df)
        
        # Aperçu du dataset
        print("\n" + "="*70)
        print("APERÇU DU DATASET (premières lignes)")
        print("="*70)
        print(df[['site', 'title', 'sources_count', 'url_count', 'image_count']].head(10).to_string())
        
        print("\n" + "="*70)
        print("✅ DATASET CRÉÉ AVEC SUCCÈS !")
        print("="*70)
        print(f"Fichiers créés:")
        print(f"  1. {csv_path} - Dataset principal")
        print(f"  2. {excel_path} - Version Excel complète avec feuilles multiples")
        
    else:
        print("\n❌ Aucun document n'a été traité.")
        print(f"Vérifiez que le dossier '{BASE_PATH}' existe et contient des fichiers .docx")