#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour récupérer et afficher les articles d'une catégorie ou sous-catégorie spécifique depuis MongoDB.
Ce script est utilisé pour répondre à la partie 8 du TP sur le scraping du Blog du Modérateur.
"""

import sys
import pymongo
import json
from datetime import datetime
from tabulate import tabulate
import argparse

# Fonction pour convertir les objets datetime en chaîne
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} non sérialisable")

def get_articles_from_db(category, limit=10, output_format="table", sort_by_date=True):
    """
    Récupère les articles d'une catégorie ou sous-catégorie depuis MongoDB.
    
    Args:
        category (str): Nom de la catégorie ou sous-catégorie
        limit (int): Nombre maximum d'articles à récupérer
        output_format (str): Format de sortie ('table', 'json', 'compact')
        sort_by_date (bool): Trier par date de publication
        
    Returns:
        None: Affiche les résultats selon le format spécifié
    """
    try:
        # Connexion à MongoDB
        client = pymongo.MongoClient('localhost', 27017)
        db = client['blogdumoderateur']
        collection = db['articles']
        
        # Création de la requête (recherche insensible à la casse)
        query = {
            "$or": [
                {"subcategory": category},
                {"subcategory": {"$regex": category, "$options": "i"}}
            ]
        }
        
        # Définir le tri
        sort_option = [("publication_date", -1)] if sort_by_date else None
        
        # Exécuter la requête
        articles = list(collection.find(query).sort(sort_option).limit(limit))
        
        if not articles:
            print(f"Aucun article trouvé pour la catégorie '{category}'.")
            return
            
        # Formater la sortie selon le format demandé
        if output_format == "json":
            # Format JSON complet
            print(json.dumps(articles, default=json_serial, indent=2, ensure_ascii=False))
            
        elif output_format == "compact":
            # Format compact (une ligne par article)
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'Sans titre')
                date = article.get('publication_date', 'Date inconnue')
                author = article.get('author', 'Auteur inconnu')
                print(f"{i}. {title} - {date} - {author}")
                
        else:  # Format tableau par défaut
            # Préparer les données pour le tableau
            table_data = []
            for article in articles:
                # Extraire et formater les données utiles
                title = article.get('title', 'Sans titre')
                date = article.get('publication_date', 'Date inconnue')
                author = article.get('author', 'Auteur inconnu')
                summary = article.get('summary', '')
                if summary and len(summary) > 100:
                    summary = summary[:97] + '...'
                
                table_data.append([title, date, author, summary])
                
            # Afficher le tableau
            headers = ["Titre", "Date", "Auteur", "Résumé"]
            print(f"\n{len(articles)} articles trouvés pour la catégorie '{category}':\n")
            print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        
    except Exception as e:
        print(f"Erreur lors de la récupération des articles: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configuration de l'analyseur d'arguments
    parser = argparse.ArgumentParser(description='Récupérer les articles par catégorie depuis MongoDB')
    parser.add_argument('category', help='Catégorie ou sous-catégorie à rechercher')
    parser.add_argument('-l', '--limit', type=int, default=10, help='Nombre maximum d\'articles (par défaut: 10)')
    parser.add_argument('-f', '--format', choices=['table', 'json', 'compact'], default='table',
                       help='Format de sortie (par défaut: table)')
    parser.add_argument('-s', '--sort', action='store_true', help='Trier par date de publication (décroissant)')
    
    # Analyser les arguments
    args = parser.parse_args()
    
    # Exécuter la fonction principale
    get_articles_from_db(args.category, args.limit, args.format, args.sort) 