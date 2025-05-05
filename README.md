# Scraping du Blog du Modérateur

![Logo Blog du Modérateur](https://www.blogdumoderateur.com/wp-content/themes/bdm/img/logo.svg)

Ce projet est un outil de scraping et de visualisation d'articles du [Blog du Modérateur](https://www.blogdumoderateur.com/), un site français d'actualités sur les médias sociaux, le marketing digital et la technologie.

## 📋 Fonctionnalités

### Scraper (`scraper.py`)
- Extraction automatique des articles par catégorie (Web, Marketing, Social, Tech, Tools)
- Stockage des données dans MongoDB
- Récupération des métadonnées complètes:
  - Titre, résumé, contenu textuel
  - Catégorie principale et tags
  - Thumbnail et images
  - Date de publication et auteur
- Multi-threading pour des performances optimisées
- Détection des doublons
- Gestion des erreurs et retries

### Frontend (`frontend.py`)
- Interface utilisateur intuitive avec Streamlit
- Filtres avancés:
  - Recherche par mots-clés
  - Filtrage par catégorie, tag, date
- Visualisation au choix:
  - Mode "cartes" avec images et résumés
  - Mode "tableau" pour une vue d'ensemble
- Pagination des résultats
- Affichage du contenu complet des articles
- Statistiques sur les données collectées

## 🛠️ Technologies utilisées

- **Python 3.8+**
- **BeautifulSoup 4** - pour le parsing HTML
- **Requests** - pour les requêtes HTTP
- **concurrent.futures** - pour le multi-threading
- **MongoDB** - pour la base de données
- **PyMongo** - pour l'interface avec MongoDB
- **Streamlit** - pour le frontend
- **Pandas** - pour la manipulation de données

## 💻 Installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/votre-username/scraper-blogdumoderateur.git
   cd scraper-blogdumoderateur
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer MongoDB**
   - Installer MongoDB si ce n'est pas déjà fait
   - S'assurer que MongoDB tourne sur le port 27017 (port par défaut)

## 🚀 Utilisation

### 1. Scraper des articles

```bash
python scraper.py
```

Le script va scraper les 10 premières pages de chaque catégorie principale et stocker les résultats dans MongoDB.

Pour modifier les paramètres:
- Nombre de pages: ajuster la variable `max_pages` dans la fonction `scrape_category`
- Catégories à scraper: modifier la liste `CATEGORIES`

### 2. Lancer le frontend Streamlit

```bash
streamlit run frontend.py
```

L'interface sera accessible à l'adresse http://localhost:8501

## 📂 Structure des données MongoDB

Chaque article est stocké avec la structure suivante:

```json
{
  "url": "https://www.blogdumoderateur.com/...",
  "title": "Titre de l'article",
  "thumbnail": "URL de l'image miniature",
  "category": "web|marketing|social|tech|tools",
  "favtag": "Tag principal",
  "tags": ["Tag1", "Tag2", "..."],
  "summary": "Résumé de l'article",
  "content": "Contenu textuel complet",
  "publication_date": "YYYY-MM-DD",
  "author": "Nom de l'auteur",
  "images": [
    {"url": "URL1", "alt_text": "Texte alternatif", "position": 0},
    {"url": "URL2", "alt_text": "Texte alternatif", "position": 1}
  ],
  "scraped_at": "Date de scraping (ISODate)"
}
```

## ⚠️ Note légale

Ce projet est créé à des fins éducatives et de recherche. Veuillez respecter les conditions d'utilisation du Blog du Modérateur et limiter les requêtes pour ne pas surcharger leur serveur. Les données extraites ne doivent pas être utilisées à des fins commerciales sans l'autorisation explicite des propriétaires du site.

## 📄 Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus d'informations.

## 🙏 Remerciements

- [Blog du Modérateur](https://www.blogdumoderateur.com/) pour leur contenu de qualité
- La communauté open-source pour les bibliothèques utilisées

---

📌 **Créé avec ❤️ par Jyriu** 