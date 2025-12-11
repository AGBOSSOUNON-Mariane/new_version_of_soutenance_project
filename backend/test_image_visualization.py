import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

def test_new_dataset():
    """
    Teste le nouveau dataset avec le séparateur |||
    """
    print("🧪 TEST DU NOUVEAU DATASET AVEC '|||'")
    print("="*60)
    
    # Charger le nouveau dataset
    df = pd.read_csv("data/df_unified.csv")
    print(f"📁 Dataset chargé: {len(df)} documents")
    
    # Vérifier la structure de la colonne images_list
    sample = df['images_list'].iloc[0] if not df['images_list'].isna().all() else ""
    print(f"\n📝 Exemple de chaîne d'images (premier document):")
    print(f"   '{sample[:100]}...'")
    
    if '|||' in str(sample):
        print("✅ Le séparateur '|||' est bien présent !")
    else:
        print("⚠️  Le séparateur '|||' n'est pas présent. Vérifie la modification du code.")
        return
    
    # Tester le parsing
    print(f"\n🔍 TEST DE PARSING SUR 10 DOCUMENTS AVEC IMAGES")
    print("="*60)
    
    success_count = 0
    total_tested = 0
    
    for idx, row in df.iterrows():
        images_str = row.get('images_list', '')
        
        if pd.isna(images_str) or images_str == "Aucune":
            continue
        
        if total_tested >= 10:  # Tester seulement 10 documents
            break
        
        total_tested += 1
        
        print(f"\n{total_tested}. {row['title'][:40]}")
        print(f"   Dossier: {row['directory']}")
        
        # Parser avec '|||'
        images = [img.strip() for img in str(images_str).split('|||') if img.strip()]
        print(f"   Images parsées: {len(images)}")
        
        # Vérifier si les fichiers existent
        if os.path.exists(row['directory']):
            found_images = []
            
            for img_name in images:
                img_path = os.path.join(row['directory'], img_name)
                if os.path.exists(img_path):
                    found_images.append(img_name)
                    print(f"   ✅ {img_name}")
                else:
                    print(f"   ❌ {img_name} (non trouvé)")
            
            if len(found_images) == len(images):
                success_count += 1
                print(f"   🎉 TOUTES les images trouvées !")
            else:
                success_rate = len(found_images) / len(images) * 100
                print(f"   📊 Taux de succès: {success_rate:.1f}%")
        else:
            print(f"   ⚠️  Dossier non trouvé")
    
    if total_tested > 0:
        overall_success = (success_count / total_tested) * 100
        print(f"\n📊 RÉSULTATS DU TEST:")
        print(f"   • Documents testés: {total_tested}")
        print(f"   • Documents avec 100% de succès: {success_count}")
        print(f"   • Taux de succès global: {overall_success:.1f}%")

def visualize_random_document():
    """
    Visualise un document aléatoire pour vérifier
    """
    print(f"\n👁️  VISUALISATION D'UN DOCUMENT ALÉATOIRE")
    print("="*60)
    
    df = pd.read_csv("data/df_unified.csv")
    
    # Prendre un document avec images
    docs_with_images = df[df['image_count'] > 0]
    
    if len(docs_with_images) == 0:
        print("❌ Aucun document avec images trouvé")
        return
    
    # Prendre le premier document avec images
    doc = docs_with_images.iloc[0]
    
    print(f"📄 Document: {doc['title']}")
    print(f"📍 Site: {doc['site']}")
    print(f"📁 Dossier: {doc['directory']}")
    print(f"🖼️  Nombre d'images: {doc['image_count']}")
    
    # Parser les images
    images_str = doc.get('images_list', '')
    if pd.isna(images_str) or images_str == "Aucune":
        print("❌ Aucune image dans ce document")
        return
    
    images = [img.strip() for img in str(images_str).split('|||') if img.strip()]
    print(f"\n📋 Images parsées ({len(images)}):")
    
    # Chercher les images
    found_paths = []
    if os.path.exists(doc['directory']):
        for img_name in images:
            img_path = os.path.join(doc['directory'], img_name)
            if os.path.exists(img_path):
                found_paths.append(img_path)
                print(f"  ✅ {img_name}")
            else:
                print(f"  ❌ {img_name} (non trouvée)")
    else:
        print(f"  ⚠️  Dossier non trouvé: {doc['directory']}")
        return
    
    # Afficher les images si elles existent
    if found_paths:
        response = input(f"\nVoulez-vous afficher les {len(found_paths)} images trouvées ? (o/n): ").lower()
        if response == 'o':
            display_images(found_paths, doc['title'])
    else:
        print("\n❌ Aucune image trouvée")

def display_images(image_paths, title):
    """
    Affiche les images avec matplotlib
    """
    n_images = len(image_paths)
    if n_images == 0:
        return
    
    # Limiter à 12 images max
    image_paths = image_paths[:12]
    
    # Calculer la disposition
    cols = min(3, n_images)
    rows = min(4, (n_images + cols - 1) // cols)
    
    fig, axes = plt.subplots(rows, cols, figsize=(15, 4*rows))
    fig.suptitle(f'Images: {title}', fontsize=16, fontweight='bold')
    
    # Aplatir les axes
    if rows > 1 or cols > 1:
        axes_flat = axes.flatten()
    else:
        axes_flat = [axes]
    
    # Afficher chaque image
    for idx, img_path in enumerate(image_paths):
        if idx >= len(axes_flat):
            break
        
        try:
            img = mpimg.imread(img_path)
            axes_flat[idx].imshow(img)
            
            # Titre court
            img_name = os.path.basename(img_path)
            display_name = img_name[:20] + '...' if len(img_name) > 20 else img_name
            axes_flat[idx].set_title(f'{idx+1}: {display_name}', fontsize=9)
            axes_flat[idx].axis('off')
            
        except Exception as e:
            axes_flat[idx].text(0.5, 0.5, f'Erreur\n{img_name[:15]}', 
                              ha='center', va='center', fontsize=10, color='red')
            axes_flat[idx].axis('off')
            print(f"⚠️  Erreur avec l'image {img_path}: {e}")
    
    # Cacher les axes non utilisés
    for idx in range(len(image_paths), len(axes_flat)):
        axes_flat[idx].axis('off')
    
    plt.tight_layout()
    plt.show()

def check_dataset_columns():
    """
    Vérifie les colonnes du nouveau dataset
    """
    print("\n📊 VÉRIFICATION DES COLONNES DU DATASET")
    print("="*60)
    
    df = pd.read_csv("data/df_unified.csv")
    
    print(f"Colonnes disponibles ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    # Vérifier spécifiquement les colonnes d'images
    print(f"\n🔍 COLONNES D'IMAGES:")
    image_cols = [col for col in df.columns if 'image' in col.lower()]
    for col in image_cols:
        print(f"  • {col}: {df[col].dtype}")
        if col == 'images_list':
            # Vérifier le séparateur
            non_na = df[col].dropna()
            if len(non_na) > 0:
                sample = str(non_na.iloc[0])
                if '|||' in sample:
                    print(f"    ✅ Contient '|||' comme séparateur")
                else:
                    print(f"    ⚠️  Ne contient PAS '|||'")
    
    # Statistiques
    print(f"\n📈 STATISTIQUES D'IMAGES:")
    print(f"  • Documents avec images: {len(df[df['image_count'] > 0])}/{len(df)}")
    print(f"  • Images totales: {df['image_count'].sum()}")
    
    # Compter les images réellement listées
    total_listed_images = 0
    for idx, row in df.iterrows():
        images_str = row.get('images_list', '')
        if pd.notna(images_str) and images_str != "Aucune":
            images = [img.strip() for img in str(images_str).split('|||') if img.strip()]
            total_listed_images += len(images)
    
    print(f"  • Images listées: {total_listed_images}")
    
    if df['image_count'].sum() > 0:
        discrepancy = abs(total_listed_images - df['image_count'].sum())
        print(f"  • Différence: {discrepancy} images")

if __name__ == "__main__":
    print("🔍 TEST COMPLET DU NOUVEAU DATASET")
    print("="*60)
    
    # 1. Vérifier les colonnes
    check_dataset_columns()
    
    # 2. Tester le parsing
    test_new_dataset()
    
    # 3. Visualiser un document
    response = input(f"\nVoulez-vous visualiser un document aléatoire ? (o/n): ").lower()
    if response == 'o':
        visualize_random_document()
    
    print("\n" + "="*60)
    print("✅ TEST TERMINÉ")
    print("="*60)
    
    print(f"\n💡 RECOMMANDATIONS:")
    print(f"   1. Si le taux de succès est < 95%, vérifie que:")
    print(f"      - Le séparateur '|||' est bien dans images_list")
    print(f"      - Les noms d'images dans le CSV correspondent aux fichiers")
    print(f"   2. Si tout est bon, lance ton analyse RAG ! 🚀")