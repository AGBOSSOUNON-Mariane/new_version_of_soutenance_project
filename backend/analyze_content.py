import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_rag_dataset():
    
    """
    Analyse détaillée du dataset RAG créé
    """
    df = pd.read_csv("data/df_unified.csv")
    print("📁 CHARGEMENT DU DATASET ORIGINAL")
    
    print("\n" + "="*60)
    print("ANALYSE DÉTAILLÉE DU DATASET TOURISTIQUE")
    print("="*60)
    
    # 1. Répartition par site
    print("\n📍 RÉPARTITION PAR SITE TOURISTIQUE:")
    site_counts = df['site'].value_counts()
    total_docs = len(df)
    
    for site, count in site_counts.items():
        percentage = (count / total_docs) * 100
        print(f"   • {site:<12}: {count:>2} documents ({percentage:5.1f}%)")
    
    # 2. Analyse de la longueur du contenu
    print("\n📊 ANALYSE DU CONTENU TEXTUEL:")
    
    # Vérifier quelles colonnes sont disponibles
    if 'word_count_main' in df.columns:
        print(f"   • Mots (contenu principal): {df['word_count_main'].mean():.0f} en moyenne")
        print(f"   • Mots (sources): {df['word_count_sources'].mean():.0f} en moyenne")
        print(f"   • Mots totaux: {df['total_word_count'].mean():.0f} en moyenne")
        print(f"   • Document le plus court: {df['word_count_main'].min()} mots")
        print(f"   • Document le plus long: {df['word_count_main'].max()} mots")
    elif 'word_count' in df.columns:
        print(f"   • Longueur moyenne (mots): {df['word_count'].mean():.0f}")
    
    # 3. Statistiques par site
    print("\n📈 STATISTIQUES PAR SITE:")
    for site in df['site'].unique():
        site_data = df[df['site'] == site]
        
        print(f"\n   • {site.upper()}:")
        print(f"     Documents: {len(site_data)}")
        
        if 'word_count_main' in site_data.columns:
            print(f"     Mots moyens (contenu): {site_data['word_count_main'].mean():.0f}")
            print(f"     Mots moyens (sources): {site_data['word_count_sources'].mean():.0f}")
        
        if 'image_count' in site_data.columns:
            print(f"     Images totales: {site_data['image_count'].sum()}")
            print(f"     Images/doc moyen: {site_data['image_count'].mean():.1f}")
        
        if 'url_count' in site_data.columns:
            print(f"     URLs totales: {site_data['url_count'].sum()}")
    
    # 4. Analyse des sources
    print("\n🔗 ANALYSE DES SOURCES:")
    
    if 'has_sources' in df.columns:
        docs_with_sources = df[df['has_sources']]
        print(f"   • Documents avec sources: {len(docs_with_sources)}/{total_docs} ({len(docs_with_sources)/total_docs*100:.1f}%)")
    
    if 'url_count' in df.columns:
        print(f"   • URLs totales trouvées: {df['url_count'].sum()}")
        print(f"   • Documents avec URLs: {len(df[df['url_count'] > 0])}/{total_docs}")
    
    # 5. Analyse des images
    print("\n🖼️ ANALYSE DES IMAGES:")
    
    if 'image_count' in df.columns:
        total_images = df['image_count'].sum()
        docs_with_images = df[df['image_count'] > 0]
        
        print(f"   • Images totales référencées: {total_images}")
        print(f"   • Documents avec images: {len(docs_with_images)}/{total_docs} ({len(docs_with_images)/total_docs*100:.1f}%)")
        print(f"   • Images par document (moyenne): {df['image_count'].mean():.1f}")
        
        # Top 5 des documents avec le plus d'images
        if len(df) > 0:
            print(f"\n   📸 TOP 5 DES DOCUMENTS AVEC LE PLUS D'IMAGES:")
            top_images = df.nlargest(5, 'image_count')
            for idx, row in top_images.iterrows():
                print(f"     • {row['site']} - {row['title'][:30]:<30}: {row['image_count']} images")
    
    # 6. Catégories et sous-catégories
    print("\n🏷️ STRUCTURE DES DONNÉES:")
    print(f"   • Sites touristiques: {df['site'].nunique()}")
    print(f"   • Catégories principales: {df['category'].nunique()}")
    print(f"   • Sous-catégories: {df['subcategory'].nunique()}")
    
    # 7. Échantillons de contenu
    print("\n📝 ÉCHANTILLONS DE CONTENU:")
    
    for site in df['site'].unique():
        site_data = df[df['site'] == site]
        if len(site_data) > 0:
            sample = site_data.iloc[0]
            print(f"\n   {site.upper()}:")
            print(f"     Titre: {sample['title']}")
            
            # Afficher un extrait du contenu
            if 'content_main' in sample:
                content_preview = str(sample['content_main'])[:150] + "..."
            elif 'content' in sample:
                content_preview = str(sample['content'])[:150] + "..."
            else:
                content_preview = "Contenu non disponible"
            
            print(f"     Extrait: {content_preview}")
    
    return df

def prepare_rag_analysis_updated(df):
    """
    Analyse de préparation pour le RAG (version mise à jour)
    """
    print("\n" + "="*60)
    print("PRÉPARATION POUR LE SYSTÈME RAG")
    print("="*60)
    
    # Déterminer la colonne de mots à utiliser
    if 'total_word_count' in df.columns:
        word_col = 'total_word_count'
    elif 'word_count_main' in df.columns:
        word_col = 'word_count_main'
    elif 'word_count' in df.columns:
        word_col = 'word_count'
    else:
        print("   ⚠️  Colonne de comptage de mots non trouvée")
        return 0
    
    # Paramètres de chunking
    chunk_size = 500  # mots par chunk
    overlap = 50      # mots de chevauchement
    
    # Estimer le nombre de chunks
    total_chunks = 0
    chunks_by_site = {}
    
    for site in df['site'].unique():
        site_data = df[df['site'] == site]
        site_chunks = 0
        
        for _, row in site_data.iterrows():
            word_count = row[word_col]
            
            if word_count <= chunk_size:
                chunks_for_doc = 1
            else:
                chunks_for_doc = max(1, (word_count - overlap) // (chunk_size - overlap))
            
            site_chunks += chunks_for_doc
        
        chunks_by_site[site] = site_chunks
        total_chunks += site_chunks
    
    print(f"\n🔧 ESTIMATION DES CHUNKS:")
    print(f"   • Taille de chunk: {chunk_size} mots")
    print(f"   • Chevauchement: {overlap} mots")
    print(f"   • Chunks totaux estimés: {total_chunks}")
    
    print(f"\n📍 CHUNKS PAR SITE:")
    for site, chunks in chunks_by_site.items():
        percentage = (chunks / total_chunks) * 100
        print(f"   • {site:<12}: {chunks:>3} chunks ({percentage:5.1f}%)")
    
    # Recommandations pour le chunking
    print(f"\n💡 RECOMMANDATIONS POUR LE CHUNKING:")
    
    # Identifier les documents longs
    long_docs = df[df[word_col] > 2000]
    if len(long_docs) > 0:
        print(f"   • {len(long_docs)} documents longs (>2000 mots):")
        for _, row in long_docs.head(3).iterrows():
            estimated_chunks = max(1, (row[word_col] - overlap) // (chunk_size - overlap))
            print(f"     - {row['site']}: {row['title'][:30]}... ({row[word_col]} mots, ~{estimated_chunks} chunks)")
    
    # Documents moyens
    medium_docs = df[(df[word_col] > 500) & (df[word_col] <= 2000)]
    print(f"   • {len(medium_docs)} documents moyens (500-2000 mots)")
    
    # Documents courts
    short_docs = df[df[word_col] <= 500]
    print(f"   • {len(short_docs)} documents courts (≤500 mots) - 1 chunk chacun")
    
    return total_chunks

def visualize_dataset(df):
    """
    Crée des visualisations pour le dataset
    """
    try:
        # Créer une figure avec plusieurs subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Analyse du Dataset Touristique', fontsize=16, fontweight='bold')
        
        # 1. Répartition par site
        ax1 = axes[0, 0]
        site_counts = df['site'].value_counts()
        colors = plt.cm.Set3(range(len(site_counts)))
        wedges, texts, autotexts = ax1.pie(site_counts.values, labels=site_counts.index, 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('Répartition des Documents par Site', fontweight='bold')
        
        # 2. Longueur des documents
        ax2 = axes[0, 1]
        if 'word_count_main' in df.columns:
            word_data = df['word_count_main']
            ax2.hist(word_data, bins=20, edgecolor='black', alpha=0.7, color='skyblue')
            ax2.set_xlabel('Nombre de mots (contenu principal)')
        elif 'word_count' in df.columns:
            word_data = df['word_count']
            ax2.hist(word_data, bins=20, edgecolor='black', alpha=0.7, color='skyblue')
            ax2.set_xlabel('Nombre de mots')
        ax2.set_ylabel('Nombre de documents')
        ax2.set_title('Distribution de la Longueur des Documents', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # 3. Images par site
        ax3 = axes[1, 0]
        if 'image_count' in df.columns:
            images_by_site = df.groupby('site')['image_count'].sum()
            sites = images_by_site.index
            image_counts = images_by_site.values
            
            bars = ax3.bar(sites, image_counts, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
            ax3.set_xlabel('Site')
            ax3.set_ylabel('Nombre total d\'images')
            ax3.set_title('Images par Site Touristique', fontweight='bold')
            ax3.grid(True, alpha=0.3, axis='y')
            
            # Ajouter les valeurs sur les barres
            for bar, count in zip(bars, image_counts):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(count)}', ha='center', va='bottom')
        
        # 4. Sources avec URLs
        ax4 = axes[1, 1]
        if 'url_count' in df.columns:
            docs_with_urls = len(df[df['url_count'] > 0])
            docs_without_urls = len(df) - docs_with_urls
            
            labels = ['Avec URLs', 'Sans URLs']
            sizes = [docs_with_urls, docs_without_urls]
            colors_pie = ['#FFD166', '#EF476F']
            
            ax4.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_pie,
                   startangle=90, explode=(0.1, 0))
            ax4.set_title('Documents avec/Sans URLs de Source', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('data/dataset_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\n📈 Visualisations sauvegardées: data/dataset_analysis.png")
        
    except Exception as e:
        print(f"\n⚠️  Erreur lors de la création des visualisations: {e}")

def show_rag_test_questions():
    """
    Questions types pour tester le RAG
    """
    print("\n" + "="*60)
    print("QUESTIONS TYPES POUR TESTER LE SYSTÈME RAG")
    print("="*60)
    
    questions_by_site = {
        "Abomey": [
            "Qui étaient les Amazones du Dahomey ?",
            "Quels sont les principaux rois du Dahomey ?",
            "Où se trouvent les Palais Royaux d'Abomey ?",
            "Quelle est l'histoire du Musée Historique d'Abomey ?",
            "Qui était le roi Béhanzin et quel est son héritage ?",
        ],
        "Ouidah": [
            "Qu'est-ce que la Route des Esclaves à Ouidah ?",
            "Quelle est l'histoire de la Porte du Non-Retour ?",
            "Quel est le rôle du Temple des Pythons dans la culture vaudou ?",
            "Qu'est-ce que la Forêt Sacrée de Kpassè ?",
            "Quels sont les principaux monuments de Ouidah ?",
        ],
        "Porto Novo": [
            "Quels sont les principaux musées de Porto-Novo ?",
            "Qui était le roi Toffa Ier ?",
            "Quelle est l'architecture de la Grande Mosquée de Porto-Novo ?",
            "Qu'est-ce que le Musée Honmè ?",
            "Quelle est l'histoire de Porto-Novo comme capitale ?",
        ],
        "Ganvié": [
            "Pourquoi Ganvié est-elle appelée la 'Venise de l'Afrique' ?",
            "Comment vit la population de Ganvié sur l'eau ?",
            "Quelle est l'histoire de la création de Ganvié ?",
            "Comment fonctionne le marché flottant de Ganvié ?",
            "Quelle est la légende du roi Agbogdobé ?",
        ]
    }
    
    print("\nVoici des questions pour tester chaque site touristique:\n")
    
    for site, questions in questions_by_site.items():
        print(f"📍 {site.upper()}:")
        for i, question in enumerate(questions, 1):
            print(f"   {i}. {question}")
        print()

def generate_rag_report(df, total_chunks):
    """
    Génère un rapport complet pour le RAG
    """
    report = f"""
# 📊 RAPPORT D'ANALYSE POUR LE SYSTÈME RAG

## 📁 DATASET
- **Documents totaux**: {len(df)}
- **Sites couverts**: {df['site'].nunique()} ({', '.join(df['site'].unique())})
- **Catégories**: {df['category'].nunique()}
- **Sous-catégories**: {df['subcategory'].nunique()}

## 📝 CONTENU
"""
    
    if 'word_count_main' in df.columns:
        report += f"- **Mots totaux (contenu)**: {df['word_count_main'].sum():,}\n"
        report += f"- **Mots moyens par document**: {df['word_count_main'].mean():.0f}\n"
    
    if 'word_count_sources' in df.columns:
        report += f"- **Mots totaux (sources)**: {df['word_count_sources'].sum():,}\n"
    
    report += f"""
## 🖼️ IMAGES
- **Images totales référencées**: {df['image_count'].sum() if 'image_count' in df.columns else 'N/A'}
- **Documents avec images**: {len(df[df['image_count'] > 0]) if 'image_count' in df.columns else 'N/A'}

## 🔗 SOURCES
- **Documents avec sources**: {len(df[df['has_sources']]) if 'has_sources' in df.columns else 'N/A'}
- **URLs totales**: {df['url_count'].sum() if 'url_count' in df.columns else 'N/A'}

## 🔧 CHUNKING RAG
- **Chunks estimés**: {total_chunks}
- **Taille de chunk recommandée**: 500 mots
- **Chevauchement recommandé**: 50 mots

## 📍 RÉPARTITION PAR SITE
"""
    
    for site in df['site'].unique():
        site_data = df[df['site'] == site]
        report += f"\n### {site}\n"
        report += f"- Documents: {len(site_data)}\n"
        
        if 'word_count_main' in site_data.columns:
            report += f"- Mots totaux: {site_data['word_count_main'].sum():,}\n"
        
        if 'image_count' in site_data.columns:
            report += f"- Images: {site_data['image_count'].sum()}\n"
        
        if 'url_count' in site_data.columns:
            report += f"- URLs: {site_data['url_count'].sum()}\n"
    
    # Sauvegarder le rapport
    with open('data/rag_analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📋 Rapport généré: data/rag_analysis_report.md")
    
    return report

if __name__ == "__main__":
    print("🔍 ANALYSE DU DATASET POUR LE SYSTÈME RAG")
    print("="*60)
    
    # 1. Analyser le dataset
    dataset = analyze_rag_dataset()
    
    # 2. Préparation RAG
    total_chunks = prepare_rag_analysis_updated(dataset)
    
    # 3. Générer des visualisations (optionnel)
    try:
        visualize_dataset(dataset)
    except:
        print("\n⚠️  Les visualisations nécessitent matplotlib et seaborn")
        print("   Installer avec: pip install matplotlib seaborn")
    
    # 4. Questions pour tester le RAG
    show_rag_test_questions()
    
    # 5. Générer un rapport
    report = generate_rag_report(dataset, total_chunks)
    
    print("\n" + "="*60)
    print("✅ ANALYSE TERMINÉE AVEC SUCCÈS !")
    print("="*60)
    print(f"\n📊 RÉSUMÉ FINAL:")
    print(f"   • Documents analysés: {len(dataset)}")
    print(f"   • Sites touristiques: {dataset['site'].nunique()}")
    print(f"   • Chunks RAG estimés: {total_chunks}")
    print(f"   • Images référencées: {dataset['image_count'].sum() if 'image_count' in dataset.columns else 'N/A'}")
    print(f"   • URLs de sources: {dataset['url_count'].sum() if 'url_count' in dataset.columns else 'N/A'}")
    
    print(f"\n📁 FICHIERS CRÉÉS:")
    print(f"   1. data/rag_analysis_report.md - Rapport complet")
    print(f"   2. data/dataset_analysis.png - Visualisations (si installé)")
    
    print(f"\n🎯 PROCHAINES ÉTAPES:")
    print(f"   1. Implémenter le chunking des documents")
    print(f"   2. Créer l'index vectoriel")
    print(f"   3. Développer le système de recherche")
    print(f"   4. Tester avec les questions fournies")