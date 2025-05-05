import requests
from bs4 import BeautifulSoup
import pymongo
from datetime import datetime
import time
import random
import logging
import sys
import concurrent.futures

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurer la connexion MongoDB
client = pymongo.MongoClient('localhost', 27017)  # Remplacer par ton adresse MongoDB
db = client['blogdumoderateur']
collection = db['articles']

# Headers pour simuler un navigateur
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
}

# Liste des catégories principales du Blog du Modérateur
CATEGORIES = ["web", "marketing", "social", "tech", "tools"]

# Réduire les délais entre les requêtes (ATTENTION: rester respectueux du serveur)
MIN_DELAY = 0.2  # 200ms
MAX_DELAY = 0.5  # 500ms
PAGE_DELAY = 0.5  # 500ms

# Nombre maximum de threads pour le scraping parallèle
MAX_WORKERS = 8

# Fonction pour scraper un article
def scrape_article(url, category=None, favtag=None, thumbnail_url=None, save_to_db=True):
    try:
        logger.info(f"Scraping de l'article : {url}")
        
        # Vérifier si l'URL existe déjà dans la base de données - avant même de faire la requête
        if save_to_db and collection.find_one({"url": url}):
            logger.info(f"L'article existe déjà dans la base de données : {url}")
            return None
            
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Vérifier si la requête a réussi
        
        soup = BeautifulSoup(response.text, 'html.parser')
        article_data = {}
        
        # URL de l'article
        article_data['url'] = url

        # 1. Le titre de l'article
        title = soup.find('h1', class_='entry-title')
        article_data['title'] = title.get_text().strip() if title else None

        # 2. L'image miniature (thumbnail) principale
        # Si on a déjà récupéré le thumbnail depuis la liste d'articles, l'utiliser
        if thumbnail_url:
            article_data['thumbnail'] = thumbnail_url
        else:
            # Méthode améliorée pour trouver le thumbnail
            thumbnail = None
            # Essayer différentes classes et attributs
            thumbnail_candidates = [
                soup.find('img', class_='attachment-full'),
                soup.find('img', class_='wp-post-image'),
                soup.find('img', class_='attachment-thumbnail'),
                soup.find('img', class_='size-thumbnail')
            ]
            
            # Rechercher dans le contenu de l'article
            post_thumbnail = soup.find('div', class_='post-thumbnail')
            if post_thumbnail and post_thumbnail.find('img'):
                thumbnail_candidates.append(post_thumbnail.find('img'))
            
            # Utiliser le premier candidat valide trouvé
            for candidate in thumbnail_candidates:
                if candidate:
                    thumbnail = candidate
                    break
            
            # Extraire l'URL de l'image
            if thumbnail:
                # Essayer différents attributs pour l'URL
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    if thumbnail.get(attr):
                        article_data['thumbnail'] = thumbnail.get(attr)
                        break
                if 'thumbnail' not in article_data:
                    article_data['thumbnail'] = None
            else:
                article_data['thumbnail'] = None

        # 3. La catégorie principale (Web, Marketing, Social, Tech)
        article_data['category'] = category if category else None
        
        # 4. Le favtag principal
        article_data['favtag'] = favtag if favtag else None
        
        # 5. Récupérer d'autres tags éventuels
        article_data['tags'] = []
        if favtag and favtag not in article_data['tags']:
            article_data['tags'].append(favtag)
            
        # Chercher d'autres tags dans l'article
        tag_elements = soup.find_all('a', class_='post-tag')
        for tag in tag_elements:
            tag_text = tag.get_text().strip()
            if tag_text and tag_text not in article_data['tags']:
                article_data['tags'].append(tag_text)

        # 6. Le résumé (extrait ou chapô de l'article)
        summary = soup.find('div', class_='article-hat')
        if summary:
            summary = summary.find('p')
        if not summary:
            summary = soup.find('div', class_='entry-summary')
        article_data['summary'] = summary.get_text().strip() if summary else None

        # 7. La date de publication
        date = soup.find('time', class_='updated')
        if date and 'datetime' in date.attrs:
            try:
                # Essayer de parser le format ISO
                article_data['publication_date'] = datetime.fromisoformat(date['datetime'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except ValueError:
                # Si le format ISO échoue, essayer un autre format
                try:
                    date_text = date.get_text().strip()
                    if date_text:
                        # Extraire la date au format "22 mai 2023 à 9h56"
                        date_parts = date_text.split(' à ')[0].split(' ')
                        day = date_parts[0]
                        month_fr = date_parts[1]
                        year = date_parts[2]
                        
                        # Convertir le mois français en chiffre
                        months_fr = {
                            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        
                        month = months_fr.get(month_fr.lower(), '01')
                        article_data['publication_date'] = f"{year}-{month}-{day.zfill(2)}"
                    else:
                        article_data['publication_date'] = None
                except Exception as e:
                    logger.error(f"Erreur de parsing de la date: {e}")
                    article_data['publication_date'] = None
        else:
            article_data['publication_date'] = None

        # 8. L'auteur de l'article
        author = soup.find('span', class_='byline')
        if author:
            author = author.find('a')
        if not author:
            author = soup.find('a', rel='author')
        article_data['author'] = author.get_text().strip() if author else None

        # 9. Dictionnaire des images dans l'article
        content = soup.find('div', class_='entry-content')
        images = []
        
        if content:
            for idx, img in enumerate(content.find_all('img')):
                img_url = img.get('src') or img.get('data-lazy-src')
                alt_text = img.get('alt', '')
                
                if img_url and not img_url.startswith('data:'):
                    images.append({
                        'url': img_url,
                        'alt_text': alt_text,
                        'position': idx
                    })
        
        article_data['images'] = images

        # 10. Contenu textuel complet de l'article
        content_html = soup.find('div', class_='entry-content')
        if content_html:
            # Supprimer les éléments qu'on ne veut pas dans le contenu textuel
            for element in content_html.select('script, style, iframe, .related-posts, .sharedaddy, .jp-relatedposts'):
                if element:
                    element.extract()
            
            # Obtenir tous les paragraphes et éléments de texte importants
            paragraphs = []
            for element in content_html.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote']):
                text = element.get_text().strip()
                if text:  # Ne pas ajouter les paragraphes vides
                    paragraphs.append(text)
            
            # Joindre tous les paragraphes avec des sauts de ligne
            article_data['content'] = '\n\n'.join(paragraphs)
        else:
            article_data['content'] = None

        # 11. Sauvegarder les données dans MongoDB
        if save_to_db:
            # Ajouter un timestamp pour la date de scraping
            article_data['scraped_at'] = datetime.now()
            
            # Éviter les doublons basés sur l'URL
            result = collection.update_one(
                {"url": url},
                {"$set": article_data},
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Nouvel article '{article_data['title']}' enregistré dans la base MongoDB.")
            else:
                logger.info(f"Article '{article_data['title']}' mis à jour dans la base MongoDB.")
        
        return article_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête HTTP pour {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors du scraping de {url}: {e}")
        return None

# Fonction pour scraper une catégorie ou sous-catégorie
def scrape_category(category, max_pages=10):  # Limité à 10 pages pour les tests
    """
    Scrape tous les articles d'une catégorie ou sous-catégorie avec multithreading
    
    Args:
        category (str): Nom de la catégorie/sous-catégorie à scraper
        max_pages (int): Limite haute du nombre de pages à scraper
        
    Returns:
        int: Nombre d'articles scrapés
    """
    scraped_count = 0
    base_url = f"https://www.blogdumoderateur.com/{category}/"
    
    page = 1
    no_articles_count = 0  # Compteur pour les pages sans articles
    all_article_data = []  # Liste pour stocker les liens et les favtags des articles
    
    print(f"Récupération des liens d'articles pour la catégorie {category}...")
    
    # Première phase : récupérer tous les liens d'articles
    while page <= max_pages:
        try:
            # Pour la première page, utiliser base_url, sinon ajouter page/N/
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}page/{page}/"
                
            logger.info(f"Récupération des liens de la page {page} de {category}: {url}")
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    logger.info(f"Page {page} non trouvée, fin du scraping pour {category}")
                    break
                else:
                    logger.error(f"Erreur HTTP {response.status_code} pour {url}: {e}")
                    if no_articles_count >= 2:
                        break
                    no_articles_count += 1
                    time.sleep(PAGE_DELAY)
                    continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article', class_='post')
            
            if not articles:
                logger.warning(f"Aucun article trouvé sur la page {page} de {category}")
                no_articles_count += 1
                
                if no_articles_count >= 2:
                    logger.info(f"Plusieurs pages sans articles, fin du scraping pour {category}")
                    break
            else:
                no_articles_count = 0
                page_links = []
                
                for article in articles:
                    article_link = None
                    favtag = None
                    thumbnail_url = None
                    
                    # Récupérer le lien de l'article
                    if article.find('a'):
                        article_link = article.find('a').get('href')
                    elif article.parent and article.parent.name == 'a':
                        article_link = article.parent.get('href')
                    
                    # Récupérer le favtag (tag principal)
                    favtag_element = article.find('span', class_='favtag')
                    if favtag_element:
                        favtag = favtag_element.get_text().strip()
                    
                    # Récupérer le thumbnail directement depuis la liste d'articles
                    img = article.find('img')
                    if img:
                        # Essayer plusieurs attributs possibles pour l'URL de l'image
                        for attr in ['src', 'data-src', 'data-lazy-src']:
                            if img.get(attr):
                                thumbnail_url = img.get(attr)
                                break
                    
                    # Stocker le lien, le favtag et le thumbnail
                    if article_link:
                        article_url = article_link
                        # Vérifier si cet URL est déjà dans notre liste
                        if not any(item['url'] == article_url for item in all_article_data):
                            article_info = {
                                'url': article_url,
                                'category': category,
                                'favtag': favtag,
                                'thumbnail': thumbnail_url
                            }
                            all_article_data.append(article_info)
                            page_links.append(article_url)
                
                logger.info(f"Page {page}: {len(page_links)} liens d'articles trouvés")
            
            page += 1
            time.sleep(PAGE_DELAY)  # Pause réduite entre les pages
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des liens sur la page {page} de {category}: {e}")
            if no_articles_count >= 2:
                break
            no_articles_count += 1
            time.sleep(PAGE_DELAY)
            continue
    
    print(f"Total de {len(all_article_data)} liens d'articles trouvés pour la catégorie {category}")
    print(f"Début du scraping des articles avec {MAX_WORKERS} threads parallèles...")
    
    # Deuxième phase : scraper tous les articles en parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Soumettre tous les liens pour scraping avec leurs catégories, favtags et thumbnails
        future_to_article = {
            executor.submit(
                scrape_article, 
                article_info['url'], 
                article_info['category'],
                article_info['favtag'],
                article_info.get('thumbnail')  # Passer le thumbnail
            ): article_info['url'] for article_info in all_article_data
        }
        
        # Traiter les résultats au fur et à mesure qu'ils arrivent
        for i, future in enumerate(concurrent.futures.as_completed(future_to_article)):
            url = future_to_article[future]
            try:
                result = future.result()
                if result:
                    scraped_count += 1
                
                # Afficher la progression
                if (i+1) % 10 == 0 or i+1 == len(all_article_data):
                    print(f"Progression: {i+1}/{len(all_article_data)} articles traités ({scraped_count} nouveaux)")
                
            except Exception as e:
                logger.error(f"Erreur lors du scraping de {url}: {e}")
    
    logger.info(f"Scraping terminé pour la catégorie {category}. {scraped_count} articles scrapés.")
    return scraped_count

def scrape_all_categories():
    """
    Scrape toutes les catégories principales du site
    """
    total_articles = 0
    
    print("=== DÉBUT DU SCRAPING COMPLET DU BLOG DU MODÉRATEUR ===")
    print(f"Catégories à scraper: {', '.join(CATEGORIES)}")
    
    for category in CATEGORIES:
        print(f"\n>>> Scraping de la catégorie: {category}")
        category_count = scrape_category(category)
        total_articles += category_count
        print(f">>> Terminé: {category_count} articles scrapés dans la catégorie {category}")
        
        # Pause plus courte entre les catégories
        if category != CATEGORIES[-1]:
            sleep_time = 1.0  # Réduit à 1 seconde fixe
            print(f"Pause de {sleep_time} seconde avant la prochaine catégorie...")
            time.sleep(sleep_time)
    
    print("\n=== SCRAPING TERMINÉ ===")
    print(f"Total: {total_articles} articles scrapés et enregistrés dans MongoDB")
    
    return total_articles

# Script principal - pas de choix interactif, on scrape tout
if __name__ == "__main__":
    try:
        start_time = datetime.now()
        print(f"Début du scraping: {start_time}")
        
        # Obtenir le nombre d'articles déjà dans la base
        existing_articles = collection.count_documents({})
        print(f"Nombre d'articles actuellement dans la base: {existing_articles}")
        
        # Lancer le scraping complet
        total_new = scrape_all_categories()
        
        # Afficher les statistiques finales
        end_time = datetime.now()
        duration = end_time - start_time
        total_articles = collection.count_documents({})
        
        print("\n=== STATISTIQUES FINALES ===")
        print(f"Durée totale: {duration}")
        print(f"Articles avant: {existing_articles}")
        print(f"Nouveaux articles: {total_new}")
        print(f"Total articles dans MongoDB: {total_articles}")
        
    except KeyboardInterrupt:
        print("\nScraping interrompu par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur lors du scraping: {e}")
        print(f"\nUne erreur s'est produite: {e}")
        sys.exit(1)