# Guide de Configuration AWS pour Déploiement Backend

## Prérequis

- Compte AWS actif
- AWS CLI installé (optionnel mais recommandé)
- Clés SSH générées
- Nom de domaine (optionnel)

## Étape 1: Créer une Instance EC2

### 1.1 Connexion à AWS Console
1. Connectez-vous à [AWS Console](https://console.aws.amazon.com)
2. Sélectionnez la région la plus proche (ex: `eu-west-1` pour Europe)

### 1.2 Lancer une Instance EC2
1. Naviguez vers **EC2 Dashboard**
2. Cliquez sur **Launch Instance**
3. Configurez:
   - **Name**: `benin-heritage-backend`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance type**: `t3.small` (2 vCPU, 2 GB RAM) - ~$15/mois
     - Pour test: `t2.micro` (Free tier) - limité mais gratuit
   - **Key pair**: Créez une nouvelle paire ou utilisez existante
   - **Network settings**:
     - ✅ Allow SSH traffic from: My IP
     - ✅ Allow HTTP traffic from internet
     - ✅ Allow HTTPS traffic from internet

### 1.3 Configurer le Stockage
- **Root volume**: 30 GB gp3 (SSD)
- Type: General Purpose SSD (gp3)

### 1.4 Lancer l'Instance
Cliquez sur **Launch Instance**

## Étape 2: Configurer Security Group

### 2.1 Règles Inbound
Ajoutez les règles suivantes:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | My IP | Administration |
| HTTP | TCP | 80 | 0.0.0.0/0 | Web traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Secure web |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | FastAPI (temporaire) |

> **Note**: Retirez le port 8000 en production une fois Nginx configuré

## Étape 3: Allouer une Elastic IP

### 3.1 Créer Elastic IP
1. Dans EC2 Dashboard → **Elastic IPs**
2. Cliquez **Allocate Elastic IP address**
3. Cliquez **Allocate**

### 3.2 Associer à l'Instance
1. Sélectionnez l'Elastic IP créée
2. **Actions** → **Associate Elastic IP address**
3. Sélectionnez votre instance
4. Cliquez **Associate**

> **Important**: Notez cette IP publique, elle sera votre `BASE_URL`
54.88.20.85

## Étape 4: Connexion SSH à l'Instance

```bash
# Modifier les permissions de votre clé
chmod 400 votre-cle.pem

# Se connecter
ssh -i votre-cle.pem ubuntu@VOTRE_ELASTIC_IP
```

## Étape 5: Installation des Dépendances sur EC2

### 5.1 Mise à jour du système
```bash
sudo apt update && sudo apt upgrade -y
```

### 5.2 Installer Docker
```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker ubuntu

# Déconnexion/reconnexion pour appliquer
exit
# Reconnectez-vous
```

### 5.3 Installer Docker Compose
```bash
sudo apt install docker-compose -y
```

### 5.4 Installer Git
```bash
sudo apt install git -y
```

### 5.5 Installer Nginx
```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Étape 6: Déployer l'Application

### 6.1 Cloner le Projet
```bash
cd ~
git clone https://github.com/AGBOSSOUNON-Mariane/new_version_of_soutenance_project.git
cd new_version_of_soutenance_project/backend
```

### 6.2 Configurer les Variables d'Environnement
```bash
# Créer le fichier .env
nano .env
```

Copiez le contenu de `.env.production.example` et remplissez vos clés:
```env
PINECONE_API_KEY=votre_cle_pinecone
GEMINI_API_KEY=votre_cle_gemini
INDEX_NAME=benin-heritage
BASE_URL=http://VOTRE_ELASTIC_IP
PORT=8000
```

Sauvegardez avec `Ctrl+O`, `Enter`, `Ctrl+X`

### 6.3 Rendre le Script de Déploiement Exécutable
```bash
chmod +x deploy.sh
```

### 6.4 Lancer le Déploiement
```bash
./deploy.sh production
```

## Étape 7: Configurer Nginx comme Reverse Proxy

### 7.1 Copier la Configuration
```bash
sudo cp nginx.conf /etc/nginx/sites-available/benin-heritage
```

### 7.2 Éditer la Configuration
```bash
sudo nano /etc/nginx/sites-available/benin-heritage
```

Remplacez `server_name _;` par votre domaine ou IP:
```nginx
server_name votre-domaine.com;  # ou VOTRE_ELASTIC_IP
```

### 7.3 Activer le Site
```bash
# Créer le lien symbolique
sudo ln -s /etc/nginx/sites-available/benin-heritage /etc/nginx/sites-enabled/

# Désactiver le site par défaut
sudo rm /etc/nginx/sites-enabled/default

# Tester la configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx
```

## Étape 8: Configurer SSL/TLS avec Let's Encrypt (Optionnel mais Recommandé)

### 8.1 Installer Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 8.2 Obtenir le Certificat
```bash
sudo certbot --nginx -d votre-domaine.com
```

Suivez les instructions interactives.

### 8.3 Renouvellement Automatique
```bash
# Tester le renouvellement
sudo certbot renew --dry-run

# Le renouvellement automatique est déjà configuré via cron
```

## Étape 9: Configuration du Domaine (Si vous avez un nom de domaine)

### 9.1 Configurer Route 53 (AWS)
1. Naviguez vers **Route 53** dans AWS Console
2. Créez une **Hosted Zone** pour votre domaine
3. Créez un **Record Set**:
   - Type: `A`
   - Name: `api` (ou `@` pour domaine racine)
   - Value: Votre Elastic IP

### 9.2 Ou Configurer chez votre Registrar
Ajoutez un enregistrement A pointant vers votre Elastic IP:
```
Type: A
Host: api (ou @)
Value: VOTRE_ELASTIC_IP
TTL: 3600
```

## Étape 10: Vérification et Tests

### 10.1 Tester l'API
```bash
# Health check
curl http://VOTRE_IP_OU_DOMAINE/health

# Test endpoint chat
curl -X POST http://VOTRE_IP_OU_DOMAINE/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour", "generate_audio": false}'
```

### 10.2 Vérifier les Logs
```bash
# Logs Docker
docker-compose logs -f

# Logs Nginx
sudo tail -f /var/log/nginx/benin-heritage-access.log
sudo tail -f /var/log/nginx/benin-heritage-error.log
```

## Étape 11: Configuration Auto-Restart (Systemd)

### 11.1 Créer le Service Systemd
```bash
sudo nano /etc/systemd/system/benin-heritage.service
```

Contenu:
```ini
[Unit]
Description=Benin Heritage API
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/new_version_of_soutenance_project/backend
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=ubuntu

[Install]
WantedBy=multi-user.target
```

### 11.2 Activer le Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable benin-heritage
sudo systemctl start benin-heritage
```

## Étape 12: Monitoring et Maintenance

### 12.1 Configurer CloudWatch (Optionnel)
1. Installez CloudWatch Agent
2. Configurez les métriques (CPU, RAM, Disk)
3. Créez des alarmes pour monitoring

### 12.2 Backup Automatique
```bash
# Créer un script de backup
nano ~/backup.sh
```

Contenu:
```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup audio files
tar -czf $BACKUP_DIR/audio_$DATE.tar.gz /home/ubuntu/new_version_of_soutenance_project/backend/audio_outputs

# Garder seulement les 7 derniers backups
find $BACKUP_DIR -name "audio_*.tar.gz" -mtime +7 -delete
```

Rendre exécutable et ajouter au cron:
```bash
chmod +x ~/backup.sh
crontab -e
```

Ajouter:
```
0 2 * * * /home/ubuntu/backup.sh
```

## Résumé des URLs

Après déploiement, votre API sera accessible via:

- **API Base**: `http://VOTRE_IP_OU_DOMAINE`
- **Documentation**: `http://VOTRE_IP_OU_DOMAINE/docs`
- **Health Check**: `http://VOTRE_IP_OU_DOMAINE/health`
- **Audio**: `http://VOTRE_IP_OU_DOMAINE/audio/{filename}`
- **Images**: `http://VOTRE_IP_OU_DOMAINE/images/{path}`

## Dépannage

### Problème: L'API ne démarre pas
```bash
# Vérifier les logs
docker-compose logs -f

# Vérifier les variables d'environnement
docker-compose config
```

### Problème: Nginx ne démarre pas
```bash
# Tester la configuration
sudo nginx -t

# Vérifier les logs
sudo tail -f /var/log/nginx/error.log
```

### Problème: Port 8000 déjà utilisé
```bash
# Trouver le processus
sudo lsof -i :8000

# Arrêter le processus
sudo kill -9 PID
```

## Coûts Estimés

| Service | Coût Mensuel |
|---------|--------------|
| EC2 t3.small | ~$15 |
| EBS 30GB | ~$3 |
| Elastic IP | Gratuit (si attaché) |
| Transfert données | ~$5-10 |
| **Total** | **~$25-30/mois** |

> **Astuce**: Utilisez t2.micro (Free Tier) pour tester gratuitement pendant 12 mois

## Support

Pour toute question:
- Documentation AWS: https://docs.aws.amazon.com
- Docker: https://docs.docker.com
- FastAPI: https://fastapi.tiangolo.com
