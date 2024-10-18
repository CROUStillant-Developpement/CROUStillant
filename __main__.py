import asyncio

from CrousPy import Crous
from CROUStillant.logger import Logger
from CROUStillant.worker import Worker
from CROUStillant.views import Views
from asyncpg import create_pool
from aiohttp import ClientSession
from os import environ
from dotenv import load_dotenv
from discord import Embed, Webhook
from datetime import datetime


load_dotenv(dotenv_path='/CROUStillant/.env')


async def main():
    """
    Main function
    """

    # Création de la session et du logger
    session = ClientSession()
    logger = Logger()
    crous = Crous(session)


    # Connexion à la base de données
    logger.info("Connexion à la base de données...")

    pool = await create_pool(
        database=environ["POSTGRES_DATABASE"], 
        user=environ["POSTGRES_USER"], 
        password=environ["POSTGRES_PASSWORD"], 
        host=environ["POSTGRES_HOST"],
        port=environ["POSTGRES_PORT"],
        min_size=10,        # 10 connections
        max_size=10,        # 10 connections
        max_queries=50000   # 50,000 queries
    )

    logger.info("Connexion à la base de données établie !")


    # Création du worker
    worker = Worker(
        logger=logger,
        pool=pool,
        client=crous,
    )


    # Création des vues
    views = Views(
        logger=logger,
        pool=pool
    )
    await views.run()


    # Lancement de la tâche de fond
    webhook = Webhook.from_url(environ["WEBHOOK_URL"], session=session)
    year = datetime.now().year
    stats = await worker.getStats()
    start = datetime.now()


    # Startup message
    embed = Embed(
        title="CROUStillant",
        description="Tâche de fond démarrée ! Chargement des données...",
        color=int(environ['EMBED_COLOR'], base=16),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="Statistiques", 
        value=f"""
Nombre de régions : `{stats['regions']:,d}`
Nombre de restaurants : `{stats['restaurants']:,d}`
Nombre de types de restauration : `{stats['types_restaurants']:,d}`
Nombre de menus : `{stats['menus']:,d}`
Nombre de repas : `{stats['repas']:,d}`
Nombre de catégories : `{stats['categories']:,d}`
Nombre de plats : `{stats['plats']:,d}`
Nombre de compositions : `{stats['compositions']:,d}`
    """)
    embed.set_thumbnail(url=environ["THUMBNAIL_URL"])
    embed.set_image(url=environ["IMAGE_URL"])
    embed.set_footer(text=f"CROUStillant Développement © 2022 - {year} | Tous droits réservés.")

    await sendWebhook(webhook=webhook, embed=embed)


    # Chargement des données
    logger.info("Chargement des données...")

    regions = await worker.loadRegions()
    await worker.loadRestaurants(regions=regions)

    logger.info("Données chargées !")


    # Shutdown message
    end = datetime.now()
    elapsed = end - start
    stats = await worker.getStats()

    embed = Embed(
        title="CROUStillant",
        description=f"Tâche de fond terminée ! Données chargées.\nTemps écoulé : `{round(elapsed.total_seconds(), 2)}` secondes.",
        color=int(environ['EMBED_COLOR'], base=16),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="Statistiques", 
        value=f"""
Nombre de régions : `{stats['regions']:,d}`
Nombre de restaurants : `{stats['restaurants']:,d}`
Nombre de types de restauration : `{stats['types_restaurants']:,d}`
Nombre de menus : `{stats['menus']:,d}`
Nombre de repas : `{stats['repas']:,d}`
Nombre de catégories : `{stats['categories']:,d}`
Nombre de plats : `{stats['plats']:,d}`
Nombre de compositions : `{stats['compositions']:,d}`
    """)
    embed.set_thumbnail(url=environ["THUMBNAIL_URL"])
    embed.set_image(url=environ["IMAGE_URL"])
    embed.set_footer(text=f"CROUStillant Développement © 2022 - {year} | Tous droits réservés.")
    
    await sendWebhook(webhook=webhook, embed=embed)


    # Fermeture de la session et de la connexion à la base de données
    await pool.close()
    await session.close()


async def sendWebhook(webhook: Webhook, embed: Embed) -> None:
    """
    Fonction pour envoyer un message sur un webhook Discord
    """
    await webhook.send(embed=embed)


if __name__ == "__main__":
    asyncio.run(main())
