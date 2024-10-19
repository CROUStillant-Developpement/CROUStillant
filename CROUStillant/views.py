from .logger import Logger
from asyncpg import Pool
from dotenv import load_dotenv
from os import listdir, environ


load_dotenv(dotenv_path='/CROUStillant/.env')


class Views:
    def __init__(self, logger: Logger, pool: Pool) -> None:
        """
        Initialisation de la classe

        :param logger: Logger de l'application
        :type logger: Logger
        :param pool: Pool de connexions à la base de données
        :type pool: Pool
        """
        self.logger = logger
        self.pool = pool


    async def createSchema(self):
        """
        Création du schéma de la base de données pour l'API
        """
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                    CREATE SCHEMA IF NOT EXISTS {SCHEMA};

                    CREATE TABLE IF NOT EXISTS PUBLIC.EMPTY ();
                """.format(
                    SCHEMA=environ["PGRST_DB_SCHEMA"],
                )
            )

            await connection.execute("""COMMENT ON SCHEMA {SCHEMA} IS
$$CROUStillant - PostgREST API

![banner](https://raw.githubusercontent.com/CROUStillant-Developpement/CROUStillantAssets/main/images/banner.png)

CROUStillant est un projet qui a pour but de fournir les menus des restaurants universitaires en France et en Outre-Mer.  
Cette API contient les données brutes sauvegardées dans la base de données de CROUStillant.  
Pour l'API publique, veuillez vous référer à : https://api.croustillant.bayfield.dev/$$;""".format(
                SCHEMA=environ["PGRST_DB_SCHEMA"],
            ))

            user = await connection.fetchval(
                """
                    SELECT 1
                    FROM pg_roles
                    WHERE rolname = '{USER}';
                """.format(
                    USER=environ["PGRST_USER"]
                )
            )

            if not user:
                await connection.execute(
                    """
                        CREATE USER {USER} WITH ENCRYPTED PASSWORD '{PASSWORD}';
                        GRANT CONNECT ON DATABASE "CROUStillant" TO {USER};
                        GRANT USAGE ON SCHEMA {SCHEMA} TO {USER};
                    """.format(
                        USER=environ["PGRST_USER"],
                        PASSWORD=environ["PGRST_PASSWORD"],
                        SCHEMA=environ["PGRST_DB_SCHEMA"],
                    )
                )


    async def createViews(self):
        """
        Création des vues de la base de données pour l'API
        """
        for view in listdir("/CROUStillant/views"):
            if view.endswith(".sql") and view.startswith("v_"):
                self.logger.debug(f"Création de la vue {view}...")

                async with self.pool.acquire() as connection:
                    await connection.execute(open(f"/CROUStillant/views/{view}", "r").read().format(
                        USER=environ["PGRST_USER"],
                        SCHEMA=environ["PGRST_DB_SCHEMA"],
                    ))


    async def run(self):
        """
        Lancement de la création du schéma et des vues
        """
        self.logger.info("Vérification du schéma et des vues...")

        self.logger.warning("Création du schéma...")
        await self.createSchema()

        self.logger.warning("Création des vues...")
        await self.createViews()
