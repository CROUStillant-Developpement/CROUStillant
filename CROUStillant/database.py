from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from os import environ

from asyncpg import Connection, Pool, create_pool

# Identifiant du verrou consultatif PostgreSQL partagé par toutes les tâches :
# empêche une synchronisation via les flux de tourner en même temps que la tâche complète
LOCK_KEY = 2022_0901

# Durée maximale d'une tâche : au-delà, PostgreSQL coupe la transaction qui porte le verrou
# (idle_in_transaction_session_timeout), ce qui libère le verrou d'une tâche bloquée
LOCK_MAX_DURATION = "2h"


async def createPool() -> Pool:
    """
    Crée le pool de connexions à la base de données.

    :return: Le pool de connexions
    :rtype: Pool
    """
    return await create_pool(
        database=environ["POSTGRES_DATABASE"],
        user=environ["POSTGRES_USER"],
        password=environ["POSTGRES_PASSWORD"],
        host=environ["POSTGRES_HOST"],
        port=environ["POSTGRES_PORT"],
        min_size=10,  # 10 connections
        max_size=10,  # 10 connections
        max_queries=50000,  # 50,000 queries
    )


@asynccontextmanager
async def advisoryLock(pool: Pool) -> AsyncGenerator[bool]:
    """
    Tente d'acquérir le verrou partagé par les tâches, pour toute la durée du bloc.

    Les services se connectent via pgbouncer en mode ``transaction`` : un verrou de
    session serait posé sur une connexion serveur arbitraire et pourrait ne jamais être
    libéré. Le verrou est donc lié à une transaction, maintenue ouverte sur une connexion
    dédiée pendant toute la tâche (pgbouncer garde la même connexion serveur tant que la
    transaction est ouverte). Il est libéré automatiquement à la fin de la transaction,
    y compris si le processus s'arrête brutalement (la connexion est alors fermée).

    :param pool: Le pool de connexions
    :type pool: Pool
    :return: ``True`` si le verrou a été acquis, ``False`` si une autre tâche le détient
    :rtype: bool
    """
    async with pool.acquire() as connection:
        connection: Connection

        async with connection.transaction():
            # La transaction reste inactive pendant la tâche : la limite par défaut
            # du serveur (idle_in_transaction_session_timeout) la couperait trop tôt
            await connection.execute(
                f"SET LOCAL idle_in_transaction_session_timeout = '{LOCK_MAX_DURATION}'"
            )

            yield await connection.fetchval(
                "SELECT pg_try_advisory_xact_lock($1)", LOCK_KEY
            )


async def getActiveRestaurants(pool: Pool) -> list[int]:
    """
    Récupère les RIDs des restaurants actifs.

    :param pool: Le pool de connexions
    :type pool: Pool
    :return: Les RIDs des restaurants actifs
    :rtype: list[int]
    """
    async with pool.acquire() as connection:
        connection: Connection

        restaurants = await connection.fetch(
            "SELECT RID FROM RESTAURANT WHERE ACTIF = TRUE;"
        )

    return [restaurant["rid"] for restaurant in restaurants]


async def insertTask(pool: Pool, start: datetime, stats: dict) -> int:
    """
    Crée une tâche avec les statistiques de départ.

    :param pool: Le pool de connexions
    :type pool: Pool
    :param start: Le début de la tâche
    :type start: datetime
    :param stats: Les statistiques de départ
    :type stats: dict
    :return: L'ID de la tâche
    :rtype: int
    """
    async with pool.acquire() as connection:
        connection: Connection

        return await connection.fetchval(
            """
                INSERT INTO TACHE (
                    DEBUT, DEBUT_REGIONS, DEBUT_RESTAURANTS, DEBUT_TYPES_RESTAURANTS, DEBUT_MENUS, DEBUT_REPAS,
                    DEBUT_CATEGORIES, DEBUT_PLATS, DEBUT_COMPOSITIONS, DEBUT_ACTIFS
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING ID;
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
            stats["actifs"],
        )


async def finishTask(
    pool: Pool, taskId: int, end: datetime, stats: dict, requests: int
) -> None:
    """
    Termine une tâche avec les statistiques de fin.

    :param pool: Le pool de connexions
    :type pool: Pool
    :param taskId: L'ID de la tâche
    :type taskId: int
    :param end: La fin de la tâche
    :type end: datetime
    :param stats: Les statistiques de fin
    :type stats: dict
    :param requests: Le nombre de requêtes effectuées
    :type requests: int
    """
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
            stats["actifs"],
            requests,
            taskId,
        )


async def logTaskRestaurants(pool: Pool, taskId: int, restaurants: list[int]) -> None:
    """
    Associe des restaurants à une tâche.

    :param pool: Le pool de connexions
    :type pool: Pool
    :param taskId: L'ID de la tâche
    :type taskId: int
    :param restaurants: Les RIDs des restaurants
    :type restaurants: list[int]
    """
    async with pool.acquire() as connection:
        connection: Connection

        await connection.executemany(
            "INSERT INTO TACHE_LOG (RID, IDTACHE) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            [(rid, taskId) for rid in restaurants],
        )


async def refreshViews(pool: Pool) -> None:
    """
    Rafraîchit les vues matérialisées.

    :param pool: Le pool de connexions
    :type pool: Pool
    """
    async with pool.acquire() as connection:
        connection: Connection

        # Rafraîchissement de la vue matérialisée des statistiques
        await connection.execute(
            """
                REFRESH MATERIALIZED VIEW CONCURRENTLY v_stats;
            """
        )

        # Rafraîchissement de la vue matérialisée des insights restaurants
        # (couverture, variété, richesse, plats fréquents par restaurant)
        await connection.execute(
            """
                REFRESH MATERIALIZED VIEW CONCURRENTLY v_restaurant_insights_summary;
            """
        )

        # Rafraîchissement de la vue matérialisée du top 100 des plats
        await connection.execute(
            """
                REFRESH MATERIALIZED VIEW CONCURRENTLY v_plats_top;
            """
        )
