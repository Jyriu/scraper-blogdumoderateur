import streamlit as st
import pymongo
from datetime import datetime, timedelta
import pandas as pd
from bson import ObjectId
import time

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Blog du Modérateur - Explorateur d'articles",
    page_icon="📰",
    layout="wide"
)

# Connexion à MongoDB (même configuration que dans scraper.py)
@st.cache_resource
def get_database_connection():
    client = pymongo.MongoClient('localhost', 27017)
    db = client['blogdumoderateur']
    return db

db = get_database_connection()
collection = db['articles']

# Titre et description
st.title("📰 Explorateur d'articles du Blog du Modérateur")
st.markdown("Recherchez et explorez les articles scrapés du Blog du Modérateur")

# Fonctions de récupération de données
@st.cache_data(ttl=300)  # Mise en cache pendant 5 minutes
def get_article_stats():
    total_articles = collection.count_documents({})
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    categories = list(collection.aggregate(pipeline))
    
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100}  # Limiter aux 100 tags les plus fréquents
    ]
    tags = list(collection.aggregate(pipeline))
    
    # Obtenir la plage de dates
    oldest = collection.find_one({}, sort=[("publication_date", 1)])
    newest = collection.find_one({}, sort=[("publication_date", -1)])
    
    oldest_date = oldest.get("publication_date") if oldest else None
    newest_date = newest.get("publication_date") if newest else None
    
    return {
        "total": total_articles,
        "categories": categories,
        "tags": tags,
        "date_range": (oldest_date, newest_date)
    }

@st.cache_data
def search_articles(query=None, category=None, tag=None, start_date=None, end_date=None, limit=50, offset=0):
    """Recherche des articles avec différents filtres"""
    filters = {}
    
    # Filtre par catégorie
    if category and category != "Toutes":
        filters["category"] = category
    
    # Filtre par tag
    if tag and tag != "Tous":
        filters["tags"] = tag
    
    # Filtre par date
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    
    if date_filter:
        filters["publication_date"] = date_filter
    
    # Recherche textuelle
    if query:
        filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"summary": {"$regex": query, "$options": "i"}},
            {"content": {"$regex": query, "$options": "i"}},
            {"tags": {"$regex": query, "$options": "i"}}
        ]
    
    # Exécuter la requête avec pagination
    cursor = collection.find(
        filters,
        {"title": 1, "thumbnail": 1, "category": 1, "favtag": 1, "tags": 1, 
         "summary": 1, "publication_date": 1, "url": 1, "author": 1}
    ).sort("publication_date", -1).skip(offset).limit(limit)
    
    total = collection.count_documents(filters)
    
    return list(cursor), total

# Obtenir les statistiques pour les filtres
stats = get_article_stats()

# Créer le layout avec une barre latérale pour les filtres
with st.sidebar:
    st.header("Filtres")
    
    # Barre de recherche
    query = st.text_input("Rechercher par mots-clés", "")
    
    # Filtre par catégorie
    categories = ["Toutes"] + [cat["_id"] for cat in stats["categories"] if cat["_id"]]
    selected_category = st.selectbox("Catégorie", categories)
    
    # Filtre par tag
    tags = ["Tous"] + [tag["_id"] for tag in stats["tags"] if tag["_id"]]
    selected_tag = st.selectbox("Tag", tags[:50])  # Limiter à 50 pour l'interface
    
    # Filtre par date
    if stats["date_range"][0] and stats["date_range"][1]:
        min_date = datetime.strptime(stats["date_range"][0], "%Y-%m-%d").date()
        max_date = datetime.strptime(stats["date_range"][1], "%Y-%m-%d").date()
    else:
        min_date = datetime.now().date() - timedelta(days=365)
        max_date = datetime.now().date()
    
    date_range = st.date_input(
        "Plage de dates",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date = date_range[0].strftime("%Y-%m-%d")
        end_date = date_range[1].strftime("%Y-%m-%d")
    else:
        start_date = min_date.strftime("%Y-%m-%d")
        end_date = max_date.strftime("%Y-%m-%d")
    
    # Informations générales
    st.header("Statistiques")
    st.metric("Total d'articles", stats["total"])
    st.metric("Catégories", len(stats["categories"]))
    st.metric("Tags uniques", len(stats["tags"]))

# Recherche avec les filtres sélectionnés
articles, total_filtered = search_articles(
    query=query,
    category=selected_category,
    tag=selected_tag,
    start_date=start_date,
    end_date=end_date
)

# Afficher les résultats
st.subheader(f"Résultats ({total_filtered} articles trouvés)")

# Pagination
page_size = 10
page_numbers = (total_filtered // page_size) + (1 if total_filtered % page_size > 0 else 0)
current_page = st.selectbox("Page", range(1, page_numbers + 1)) if page_numbers > 0 else 1

offset = (current_page - 1) * page_size

# Actualiser les résultats avec pagination
if page_numbers > 0:
    articles, _ = search_articles(
        query=query,
        category=selected_category,
        tag=selected_tag,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset
    )

# Afficher les articles
if not articles:
    st.warning("Aucun article trouvé avec ces critères.")
else:
    # Sélectionner l'affichage : carte ou tableau
    display_mode = st.radio("Mode d'affichage", ["Cartes", "Tableau"])
    
    if display_mode == "Tableau":
        # Créer une liste de dictionnaires pour le DataFrame
        df_data = []
        for article in articles:
            df_data.append({
                "Titre": article.get("title", ""),
                "Catégorie": article.get("category", ""),
                "Tag principal": article.get("favtag", ""),
                "Date": article.get("publication_date", ""),
                "Auteur": article.get("author", ""),
                "URL": article.get("url", "")
            })
        
        # Créer et afficher le DataFrame
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    else:
        # Affichage en cartes
        for i, article in enumerate(articles):
            with st.container():
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    # Afficher la miniature si disponible
                    if article.get("thumbnail"):
                        st.image(article["thumbnail"], width=200)
                    else:
                        st.image("https://via.placeholder.com/200x150?text=Image+non+disponible", width=200)
                
                with col2:
                    # Titre avec lien
                    st.markdown(f"### [{article.get('title', 'Sans titre')}]({article.get('url', '#')})")
                    
                    # Métadonnées
                    meta_col1, meta_col2, meta_col3 = st.columns(3)
                    with meta_col1:
                        st.caption(f"📅 {article.get('publication_date', 'Date inconnue')}")
                    with meta_col2:
                        st.caption(f"📂 {article.get('category', 'Sans catégorie')}")
                    with meta_col3:
                        st.caption(f"🔖 {article.get('favtag', 'Sans tag')}")
                    
                    # Résumé
                    if article.get("summary"):
                        st.markdown(f"{article['summary'][:300]}...")
                    
                    # Tags
                    if article.get("tags"):
                        st.markdown(f"**Tags**: {', '.join(article['tags'][:5])}")
                    
                    # Bouton pour voir les détails
                    if st.button(f"Voir détails", key=f"details_{i}"):
                        # Récupérer l'article complet
                        full_article = collection.find_one({"_id": article["_id"]})
                        
                        with st.expander("Contenu complet", expanded=True):
                            st.markdown(f"## {full_article.get('title', 'Sans titre')}")
                            st.markdown(f"*Par {full_article.get('author', 'Auteur inconnu')} - {full_article.get('publication_date', 'Date inconnue')}*")
                            
                            if full_article.get("content"):
                                st.markdown(full_article["content"].replace("\n", "\n\n"))
                            else:
                                st.warning("Le contenu complet n'est pas disponible.")
            
            # Séparateur entre les articles
            st.markdown("---")

# Pied de page
st.sidebar.markdown("---")
st.sidebar.markdown("Créé avec Streamlit et MongoDB")
st.sidebar.markdown(f"Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
