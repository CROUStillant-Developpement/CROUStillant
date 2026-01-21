import asyncio

from CrousPy import Crous
from CROUStillant.logger import Logger
from CROUStillant.worker import Worker
from CROUStillant.views import WorkerView, ErrorView
from asyncpg import create_pool, Connection
from aiohttp import ClientSession
from os import environ
from dotenv import load_dotenv
from discord import Webhook
from discord.ui import LayoutView
from datetime import datetime
from pytz import timezone


load_dotenv(dotenv_path="/CROUStillant/.env")


async def main():
    """
    Main function
    """

    # Création de la session et du logger
    session = ClientSession()
    logger = Logger("background")
    crous = Crous(session)

    # Connexion à la base de données
    logger.info("Connexion à la base de données...")

    pool = await create_pool(
        database=environ["POSTGRES_DATABASE"],
        user=environ["POSTGRES_USER"],
        password=environ["POSTGRES_PASSWORD"],
        host=environ["POSTGRES_HOST"],
        port=environ["POSTGRES_PORT"],
        min_size=10,  # 10 connections
        max_size=10,  # 10 connections
        max_queries=50000,  # 50,000 queries
    )

    logger.info("Connexion à la base de données établie !")

    # Récupération des restaurants actifs dans la base de données
    async with pool.acquire() as connection:
        connection: Connection

        restaurants = await connection.fetch(
            "SELECT RID FROM RESTAURANT WHERE ACTIF = TRUE;"
        )

    # Création du worker
    worker = Worker(
        logger=logger,
        pool=pool,
        client=crous,
        restaurants=[restaurant["rid"] for restaurant in restaurants],
    )

    # Lancement de la tâche de fond
    webhook = Webhook.from_url(environ["WEBHOOK_URL"], session=session)
    year = datetime.now(timezone("Europe/Paris")).year
    stats = await worker.getStats()
    start = datetime.now()

    # Création d'une tâche de fond pour mettre à jour les données
    async with pool.acquire() as connection:
        connection: Connection

        await connection.execute(
            """
                INSERT INTO TACHE (
                    DEBUT, DEBUT_REGIONS, DEBUT_RESTAURANTS, DEBUT_TYPES_RESTAURANTS, DEBUT_MENUS, DEBUT_REPAS, 
                    DEBUT_CATEGORIES, DEBUT_PLATS, DEBUT_COMPOSITIONS, DEBUT_ACTIFS
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
            """,
            start,
            stats["regions"],
            stats["restaurants"],
            stats["types_restaurants"],
            stats["menus"],
            stats["repas"],
            stats["categories"],
            stats["plats"],
            stats["compositions"],
            len(restaurants),
        )

        taskId = await connection.fetchval("SELECT MAX(ID) FROM TACHE;")
        worker.taskId = taskId

    # Startup message
    view = WorkerView(
        content="## Tâche de fond démarrée ! Chargement des données...\n\nTâche **`#{taskId}`**".format(
            taskId=taskId,
        ),
        stats="""
Nombre de régions : `{regions:,d}`
Nombre de restaurants : `{restaurants:,d}`
Nombre de types de restauration : `{types_restaurants:,d}`
Nombre de menus : `{menus:,d}`
Nombre de repas : `{repas:,d}`
Nombre de catégories : `{categories:,d}`
Nombre de plats : `{plats:,d}`
Nombre de compositions : `{compositions:,d}`
Nombre de restaurants actifs : `{actifs:,d}`
        """.format(
            regions=stats["regions"],
            restaurants=stats["restaurants"],
            types_restaurants=stats["types_restaurants"],
            menus=stats["menus"],
            repas=stats["repas"],
            categories=stats["categories"],
            plats=stats["plats"],
            compositions=stats["compositions"],
            actifs=len(restaurants),
        ),
        thumbnail_url=environ["THUMBNAIL_URL"],
        banner_url=environ["IMAGE_URL"],
        footer_text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.".format(year=year),
    )

    await sendWebhook(webhook=webhook, view=view)

    # Chargement des données
    logger.info("Chargement des données...")

    try:
        regions = await worker.loadRegions()
    except Exception as e:
        logger.error(f"Erreur lors du chargement des régions : {e}")

        view = ErrorView(
            content="## Erreur lors du chargement des régions. L'API du CROUS est indisponible ?\n\nTâche **`#{taskId}`**".format(
                taskId=taskId,
            ),
            thumbnail_url=environ["THUMBNAIL_URL"],
            banner_url=environ["IMAGE_URL"],
            footer_text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.".format(year=year),
        )

        await sendWebhook(
            webhook=webhook,
            view=view,
        )

        async with pool.acquire() as connection:
            connection: Connection

            await connection.execute(
                """
                    UPDATE TACHE
                    SET FIN = $1, FIN_REGIONS = $2, FIN_RESTAURANTS = $3, FIN_TYPES_RESTAURANTS = $4, FIN_MENUS = $5, 
                        FIN_REPAS = $6, FIN_CATEGORIES = $7, FIN_PLATS = $8, FIN_COMPOSITIONS = $9, FIN_ACTIFS = $10,
                        REQUETES = $11
                    WHERE ID = $12;
                """,
                datetime.now(),
                stats["regions"],
                stats["restaurants"],
                stats["types_restaurants"],
                stats["menus"],
                stats["repas"],
                stats["categories"],
                stats["plats"],
                stats["compositions"],
                len(restaurants),
                0,
                taskId,
            )

        return

    try:
        await worker.loadRestaurants(regions=regions)
    except Exception as e:
        logger.error(f"Erreur lors du chargement des restaurants : {e}")

        view = ErrorView(
            content="## Erreur lors du chargement des restaurants. L'API du CROUS est indisponible ?\n\nTâche **`#{taskId}`**".format(
                taskId=taskId,
            ),
            thumbnail_url=environ["THUMBNAIL_URL"],
            banner_url=environ["IMAGE_URL"],
            footer_text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.".format(year=year),
        )

        await sendWebhook(
            webhook=webhook,
            view=view,
        )

        async with pool.acquire() as connection:
            connection: Connection

            await connection.execute(
                """
                    UPDATE TACHE
                    SET FIN = $1, FIN_REGIONS = $2, FIN_RESTAURANTS = $3, FIN_TYPES_RESTAURANTS = $4, FIN_MENUS = $5, 
                        FIN_REPAS = $6, FIN_CATEGORIES = $7, FIN_PLATS = $8, FIN_COMPOSITIONS = $9, FIN_ACTIFS = $10,
                        REQUETES = $11
                    WHERE ID = $12;
                """,
                datetime.now(),
                stats["regions"],
                stats["restaurants"],
                stats["types_restaurants"],
                stats["menus"],
                stats["repas"],
                stats["categories"],
                stats["plats"],
                stats["compositions"],
                len(restaurants),
                0,
                taskId,
            )

        return

    logger.info("Données chargées !")

    # Mise à jour des statuts des restaurants inactifs
    await worker.updateRestaurantsStatus()

    # Récupération des restaurants actifs dans la base de données
    async with pool.acquire() as connection:
        connection: Connection

        restaurants = await connection.fetch(
            "SELECT RID FROM RESTAURANT WHERE ACTIF = TRUE;"
        )

    # Fin de la tâche de fond
    end = datetime.now()
    elapsed = end - start

    # Mise à jour des données
    async with pool.acquire() as connection:
        connection: Connection

        # Rafraîchissement de la vue matérialisée des statistiques
        await connection.execute(
            """
                REFRESH MATERIALIZED VIEW CONCURRENTLY v_stats;
            """
        )

    # Récupération des statistiques finales
    stats = await worker.getStats()

    # Mise à jour de la tâche
    async with pool.acquire() as connection:
        connection: Connection

        await connection.execute(
            """
                UPDATE TACHE
                SET FIN = $1, FIN_REGIONS = $2, FIN_RESTAURANTS = $3, FIN_TYPES_RESTAURANTS = $4, FIN_MENUS = $5, 
                    FIN_REPAS = $6, FIN_CATEGORIES = $7, FIN_PLATS = $8, FIN_COMPOSITIONS = $9, FIN_ACTIFS = $10,
                    REQUETES = $11
                WHERE ID = $12;
            """,
            end,
            stats["regions"],
            stats["restaurants"],
            stats["types_restaurants"],
            stats["menus"],
            stats["repas"],
            stats["categories"],
            stats["plats"],
            stats["compositions"],
            len(restaurants),
            worker.requests,
            taskId,
        )

    # Envoi du message de fin
    view = WorkerView(
        content="## Tâche de fond terminée ! Données chargées.\nTemps écoulé : `{elapsed}` secondes.\n\nTâche **`#{taskId}`**".format(
            elapsed=round(elapsed.total_seconds(), 2),
            taskId=taskId,
        ),
        stats="""
Nombre de régions : `{regions:,d}`
Nombre de restaurants : `{restaurants:,d}`
Nombre de types de restauration : `{types_restaurants:,d}`
Nombre de menus : `{menus:,d}`
Nombre de repas : `{repas:,d}`
Nombre de catégories : `{categories:,d}`
Nombre de plats : `{plats:,d}`
Nombre de compositions : `{compositions:,d}`
Nombre de restaurants actifs : `{actifs:,d}`
        """.format(
            regions=stats["regions"],
            restaurants=stats["restaurants"],
            types_restaurants=stats["types_restaurants"],
            menus=stats["menus"],
            repas=stats["repas"],
            categories=stats["categories"],
            plats=stats["plats"],
            compositions=stats["compositions"],
            actifs=len(restaurants),
        ),
        thumbnail_url=environ["THUMBNAIL_URL"],
        banner_url=environ["IMAGE_URL"],
        footer_text="CROUStillant Développement © 2022 - {year} | Tous droits réservés.".format(year=year),
    )

    await sendWebhook(webhook=webhook, view=view)

    # Fermeture de la session et de la connexion à la base de données
    await pool.close()
    await session.close()


async def sendWebhook(webhook: Webhook, view: LayoutView) -> None:
    """
    Fonction pour envoyer un message sur un webhook Discord
    """
    await webhook.send(view=view)


if __name__ == "__main__":
    asyncio.run(main())
