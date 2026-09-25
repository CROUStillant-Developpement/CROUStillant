from datetime import datetime

from asyncpg import Pool
from CrousPy import Crous

from CROUStillant.database import (
    finishTask,
    getActiveRestaurants,
    insertTask,
    logTaskRestaurants,
    refreshViews,
)
from CROUStillant.logger import Logger
from CROUStillant.notifier import Notifier
from CROUStillant.worker import Worker


async def runFeed(logger: Logger, pool: Pool, crous: Crous, notifier: Notifier) -> None:
    """
    Synchronisation des menus via les flux régionaux (toutes les 15 minutes) : seuls
    les restaurants dont les menus ont changé dans les flux sont rechargés depuis l'API.

    Aucune tâche n'est enregistrée et aucun message n'est envoyé si rien n'a changé.

    :param logger: Le logger
    :type logger: Logger
    :param pool: Le pool de connexions
    :type pool: Pool
    :param crous: Le client Crous
    :type crous: Crous
    :param notifier: Le notifier Discord
    :type notifier: Notifier
    """
    restaurants = await getActiveRestaurants(pool)

    worker = Worker(logger=logger, pool=pool, client=crous, restaurants=restaurants)

    stats = await worker.getStats()
    start = datetime.now()
    initialStats = {**stats, "actifs": len(restaurants)}

    try:
        counters = await worker.syncFromFeeds()
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation via les flux : {e}")
        await notifier.error(
            "Erreur lors de la synchronisation via les flux", e, start, worker.requests
        )
        return

    if not worker.updatedRestaurants:
        logger.info("Aucun menu modifié, rien à faire.")
        return

    await refreshViews(pool)

    end = datetime.now()
    stats = await worker.getStats()
    finalStats = {**stats, "actifs": len(restaurants)}

    taskId = await insertTask(pool, start, initialStats)
    await finishTask(pool, taskId, end, finalStats, worker.requests)
    await logTaskRestaurants(pool, taskId, [rid for rid, _ in worker.updatedRestaurants])

    await notifier.menusUpdated(
        taskId,
        start,
        end,
        [name for _, name in worker.updatedRestaurants],
        counters,
        worker.requests,
    )
