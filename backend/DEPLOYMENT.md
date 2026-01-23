# Guide de Déploiement Backend sur AWS - Patrimoine Béninois

## 📋 Vue d'ensemble

Ce guide vous accompagne pour déployer votre API FastAPI sur AWS EC2 avec Docker.

## 🎯 Résultat Final

Après ce déploiement, vous aurez:
- ✅ API accessible publiquement via URL AWS
- ✅ HTTPS sécurisé (optionnel)
- ✅ Auto-restart en cas de crash
- ✅ Logs centralisés
- ✅ Coût: ~$25-30/mois

## 📁 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `Dockerfile` | Configuration Docker multi-stage optimisée |
| `docker-compose.yml` | Orchestration des conteneurs |
| `nginx.conf` | Reverse proxy avec cache et compression |
| `deploy.sh` | Script de déploiement automatisé |
| `aws-setup.md` | Guide détaillé configuration AWS (12 étapes) |
| `.env.production.example` | Template variables d'environnement |

## 🚀 Déploiement Rapide (3 étapes)

### 1️⃣ Test Local (Optionnel mais Recommandé)

```bash
cd backend

# Créer .env avec vos clés
cp .env.production.example .env
nano .env  # Remplir PINECONE_API_KEY et GEMINI_API_KEY

# Tester localement
chmod +x deploy.sh
./deploy.sh

# Vérifier
curl http://localhost:8000/health
```

### 2️⃣ Créer Instance AWS EC2

Suivez le guide détaillé: [aws-setup.md](file:///home/Armel/Nouveau%20dossier/Mariane/new_version_of_soutenance_project/backend/aws-setup.md)

**Résumé rapide**:
1. AWS Console → EC2 → Launch Instance
2. Ubuntu 22.04 LTS, t3.small (ou t2.micro pour test gratuit)
3. Security Group: ports 22, 80, 443, 8000
4. Créer et associer Elastic IP
5. Se connecter via SSH

### 3️⃣ Déployer sur EC2

```bash
# Sur votre EC2 (après connexion SSH)
git clone https://github.com/AGBOSSOUNON-Mariane/new_version_of_soutenance_project.git
cd new_version_of_soutenance_project/backend

# Configurer .env
nano .env  # Remplir avec vos clés + BASE_URL=http://VOTRE_ELASTIC_IP

# Déployer
chmod +x deploy.sh
./deploy.sh production

# Configurer Nginx
sudo cp nginx.conf /etc/nginx/sites-available/benin-heritage
sudo ln -s /etc/nginx/sites-available/benin-heritage /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 🔧 Configuration Frontend

Après déploiement, mettez à jour votre frontend:

```typescript
// frontend/services/api.ts
const API_BASE_URL = 'http://VOTRE_ELASTIC_IP';
// Ou avec domaine:
// const API_BASE_URL = 'https://api.votre-domaine.com';
```

## 📊 Vérification

```bash
# Health check
curl http://VOTRE_IP/health

# Test conversation
curl -X POST http://VOTRE_IP/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Bonjour",
    "generate_audio": false
  }'
```

## 🎓 Options de Déploiement

### Option 1: EC2 + Docker (Recommandée) ⭐
- **Avantages**: Contrôle total, facile à déboguer
- **Coût**: ~$25-30/mois
- **Difficulté**: Moyenne
- **Guide**: [aws-setup.md](file:///home/Armel/Nouveau%20dossier/Mariane/new_version_of_soutenance_project/backend/aws-setup.md)

### Option 2: Elastic Beanstalk
- **Avantages**: Déploiement simplifié, auto-scaling
- **Coût**: ~$30-40/mois
- **Difficulté**: Facile
- **Guide**: Créer application Beanstalk, upload Dockerfile

### Option 3: ECS (Elastic Container Service)
- **Avantages**: Architecture moderne, scalable
- **Coût**: ~$35-50/mois
- **Difficulté**: Avancée
- **Guide**: Créer cluster ECS, task definition, service

## 🛠️ Commandes Utiles

```bash
# Voir les logs
docker-compose logs -f

# Redémarrer
docker-compose restart

# Arrêter
docker-compose down

# Rebuild après modification
docker-compose up -d --build

# Nettoyer les fichiers audio
curl -X POST http://localhost:8000/audio/cleanup
```

## 🔒 Sécurité

### Activer HTTPS (Recommandé)
```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtenir certificat SSL
sudo certbot --nginx -d votre-domaine.com
```

### Bonnes Pratiques
- ✅ Utilisez AWS Secrets Manager pour les clés API
- ✅ Restreignez SSH à votre IP uniquement
- ✅ Activez CloudWatch pour monitoring
- ✅ Configurez des backups automatiques
- ✅ Mettez à jour régulièrement le système

## 💰 Estimation des Coûts

| Configuration | Instance | Coût/mois |
|---------------|----------|-----------|
| **Test** | t2.micro (Free Tier) | $0 (12 mois) |
| **Production** | t3.small | ~$25-30 |
| **Haute Performance** | t3.medium | ~$50-60 |

## 📞 Support

### Problèmes Courants

**API ne démarre pas**:
```bash
docker-compose logs -f
# Vérifier les variables d'environnement
```

**Nginx erreur 502**:
```bash
# Vérifier que le conteneur tourne
docker-compose ps
# Vérifier les logs Nginx
sudo tail -f /var/log/nginx/error.log
```

**Port déjà utilisé**:
```bash
sudo lsof -i :8000
sudo kill -9 PID
```

### Ressources
- [Documentation AWS EC2](https://docs.aws.amazon.com/ec2/)
- [Guide Docker](https://docs.docker.com/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## 📝 Prochaines Étapes

1. ✅ Tester localement avec Docker
2. ✅ Créer instance EC2 sur AWS
3. ✅ Déployer l'application
4. ✅ Configurer Nginx
5. ⬜ Activer HTTPS (optionnel)
6. ⬜ Configurer monitoring (optionnel)
7. ⬜ Mettre à jour frontend avec nouvelle URL

## 🎉 Félicitations!

Votre API est maintenant déployée et accessible publiquement! 

**URL de votre API**: `http://VOTRE_ELASTIC_IP`  
**Documentation**: `http://VOTRE_ELASTIC_IP/docs`

---

**Besoin d'aide?** Consultez le guide détaillé [aws-setup.md](file:///home/Armel/Nouveau%20dossier/Mariane/new_version_of_soutenance_project/backend/aws-setup.md)
