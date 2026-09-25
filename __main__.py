import asyncio
import sys

from aiohttp import ClientSession
from CrousPy import Crous
from dotenv import load_dotenv

from CROUStillant.database import advisoryLock, createPool
from CROUStillant.logger import Logger
from CROUStillant.notifier import Notifier
from CROUStillant.tasks import TASKS

load_dotenv(dotenv_path="/CROUStillant/.env")


async def main(mode: str):
    """
    Main function

    :param mode: ``full`` (tâche complète, une fois par jour) ou ``feed`` (synchronisation
        des menus via les flux régionaux, toutes les 15 minutes)
    :type mode: str
    """

    # Création de la session et du logger
    session = ClientSession()
    logger = Logger("background")
    crous = Crous(session)
    notifier = Notifier(session)

    # Connexion à la base de données
    logger.info("Connexion à la base de données...")
    pool = await createPool()
    logger.info("Connexion à la base de données établie !")

    try:
        async with advisoryLock(pool) as acquired:
            if not acquired:
                logger.warning("Une autre tâche est déjà en cours, abandon.")
                return

            await TASKS[mode](logger, pool, crous, notifier)
    finally:
        # Fermeture de la session et de la connexion à la base de données
        await pool.close()
        await session.close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode not in TASKS:
        sys.exit(f"Mode inconnu : {mode} (attendu : {', '.join(TASKS)})")

    asyncio.run(main(mode))
