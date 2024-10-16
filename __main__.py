import asyncio

from CrousPy import Crous
from logger import Logger
from worker import Worker
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
    session = ClientSession()

    logger = Logger()

    crous = Crous(session)

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

    webhook = Webhook.from_url(environ["WEBHOOK_URL"], session=session)
    year = datetime.now().year
    
    start = datetime.now()

    # Startup message
    embed = Embed(
        title="CROUStillant",
        description="Tâche de fond démarrée ! Chargement des données...",
        color=int(environ['EMBED_COLOR'], base=16),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=environ["THUMBNAIL_URL"])
    embed.set_image(url=environ["IMAGE_URL"])
    embed.set_footer(text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.")

    await sendWebhook(webhook=webhook, embed=embed)

    worker = Worker(
        logger=logger,
        pool=pool,
        client=crous,
    )

    logger.info("Chargement des données...")

    regions = await worker.loadRegions()
    await worker.loadRestaurants(regions=regions)
    
    end = datetime.now()
    elapsed = end - start

    # Shutdown message
    embed = Embed(
        title="CROUStillant",
        description=f"Tâche de fond terminée ! Données chargées.\nTemps écoulé : `{round(elapsed.total_seconds(), 2)}` secondes.",
        color=int(environ['EMBED_COLOR'], base=16),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=environ["THUMBNAIL_URL"])
    embed.set_image(url=environ["IMAGE_URL"])
    embed.set_footer(text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.")
    
    await sendWebhook(webhook=webhook, embed=embed)

    await session.close()


async def sendWebhook(webhook: Webhook, embed: Embed) -> None:
    """
    Fonction pour envoyer un message sur un webhook Discord
    """
    await webhook.send(embed=embed)


if __name__ == "__main__":
    asyncio.run(main())
