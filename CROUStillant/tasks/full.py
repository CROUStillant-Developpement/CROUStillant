from datetime import datetime

from asyncpg import Pool
from CrousPy import Crous

from CROUStillant.database import (
    finishTask,
    getActiveRestaurants,
    insertTask,
    refreshViews,
)
from CROUStillant.logger import Logger
from CROUStillant.notifier import Notifier
from CROUStillant.worker import Worker


async def runFull(logger: Logger, pool: Pool, crous: Crous, notifier: Notifier) -> None:
    """
    Tâche complète (une fois par jour) : régions, restaurants et menus de chaque
    restaurant via l'API. Enregistre aussi l'empreinte des menus utilisée par la
    synchronisation via les flux.

    :param logger: Le logger
    :type logger: Logger
    :param pool: Le pool de connexions
    :type pool: Pool
    :param crous: Le client Crous
    :type crous: Crous
    :param notifier: Le notifier Discord
    :type notifier: Notifier
    """
    # Récupération des restaurants actifs dans la base de données
    restaurants = await getActiveRestaurants(pool)

    # Création du worker
    worker = Worker(
        logger=logger,
        pool=pool,
        client=crous,
        restaurants=restaurants,
    )

    stats = await worker.getStats()
    start = datetime.now()
    initialStats = {**stats, "actifs": len(restaurants)}

    # Création d'une tâche de fond pour mettre à jour les données
    taskId = await insertTask(pool, start, initialStats)
    worker.taskId = taskId

    await notifier.taskStarted(taskId, start, initialStats)

    # Chargement des données
    logger.info("Chargement des données...")

    try:
        regions = await worker.loadRegions()
    except Exception as e:
        logger.error(f"Erreur lors du chargement des régions : {e}")
        await notifier.error(
            "Erreur lors du chargement des régions", e, start, worker.requests, taskId
        )
        await finishTask(pool, taskId, datetime.now(), initialStats, worker.requests)
        return

    try:
        await worker.loadRestaurants(regions=regions)
    except Exception as e:
        logger.error(f"Erreur lors du chargement des restaurants : {e}")
        await notifier.error(
            "Erreur lors du chargement des restaurants", e, start, worker.requests, taskId
        )
        await finishTask(pool, taskId, datetime.now(), initialStats, worker.requests)
        return

    logger.info("Données chargées !")

    # Mise à jour des statuts des restaurants inactifs
    await worker.updateRestaurantsStatus()

    # Récupération des restaurants actifs dans la base de données
    restaurants = await getActiveRestaurants(pool)

    # Fin de la tâche de fond
    end = datetime.now()

    # Mise à jour des données
    await refreshViews(pool)

    # Récupération des statistiques finales
    stats = await worker.getStats()
    finalStats = {**stats, "actifs": len(restaurants)}

    # Mise à jour de la tâche
    await finishTask(pool, taskId, end, finalStats, worker.requests)

    await notifier.taskFinished(
        taskId, start, end, finalStats, initialStats, worker.requests
    )
