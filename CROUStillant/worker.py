from CrousPy import Crous, Region, RU
from CROUStillant.logger import Logger
from asyncpg import Pool, Connection
from json import dumps


class Worker:
    def __init__(self, logger: Logger, pool: Pool, client: Crous) -> None:
        """
        Constructeur de la classe Worker.
        
        :param logger: Le logger
        :type logger: Logger
        :param pool: Le pool de connexions
        :type pool: Pool
        :param client: Le client Crous
        :type client: Crous
        """
        self.logger = logger
        self.pool = pool
        self.client = client


    async def getStats(self) -> dict:
        """
        Récupère les statistiques.

        :return: Les statistiques
        :rtype: dict
        """
        async with self.pool.acquire() as connection:
            connection: Connection

            stats = await connection.fetchrow(
                """
                    SELECT
                        (SELECT COUNT(*) FROM REGION) AS regions,
                        (SELECT COUNT(*) FROM RESTAURANT) AS restaurants,
                        (SELECT COUNT(*) FROM TYPE_RESTAURANT) AS types_restaurants,
                        (SELECT COUNT(*) FROM MENU) AS menus,
                        (SELECT COUNT(*) FROM REPAS) AS repas,
                        (SELECT COUNT(*) FROM CATEGORIE) AS categories,
                        (SELECT COUNT(*) FROM PLAT) AS plats,
                        (SELECT COUNT(*) FROM COMPOSITION) AS compositions
                """
            )

        return dict(stats)


    async def loadRegions(self) -> list[Region]:
        """
        Charge les régions et les enregistre dans la base de données.
        
        :return: Les régions
        :rtype: list[Region]
        """
        self.logger.info("Chargement des régions...")

        regions = await self.client.region.get()

        self.logger.info(f"{len(regions)} régions chargées !")

        async with self.pool.acquire() as connection:
            connection: Connection
            for region in regions:
                await connection.execute(
                    """
                        INSERT INTO region (IDREG, LIBELLE) 
                        VALUES ($1, $2) 
                        ON CONFLICT DO NOTHING
                    """, 
                    region.id, 
                    region.name
                )

        self.logger.info("Régions enregistrées !")

        return regions


    async def loadRestaurants(self, regions: list[Region]) -> None:
        """
        Charge les restaurants et les enregistre dans la base de données.
        
        :param regions: Les régions
        :type regions: list[Region]
        """
        self.logger.info("Chargement des restaurants...")

        async with self.pool.acquire() as connection:
            connection: Connection

            for region in regions:
                self.logger.info(f"Chargement des restaurants pour la région {region.name}...")

                restaurants = await self.client.ru.get(region.id)

                self.logger.info(f"{len(restaurants)} restaurants chargés pour la région {region.name} !")

                for restaurant in restaurants:
                    restaurant: RU

                    tpRestaurantID = await connection.fetchval("SELECT IDTPR FROM TYPE_RESTAURANT WHERE LIBELLE = $1", restaurant.type)

                    if not tpRestaurantID:
                        await connection.execute(
                            """
                                INSERT INTO type_restaurant (LIBELLE) 
                                VALUES ($1) 
                                ON CONFLICT DO NOTHING
                            """, 
                            restaurant.type
                        )

                        tpRestaurantID = await connection.fetchval("SELECT IDTPR FROM TYPE_RESTAURANT WHERE LIBELLE = $1", restaurant.type)

                    async with connection.transaction():
                        await connection.execute(
                            """
                                INSERT INTO restaurant (RID, IDREG, IDTPR, NOM, ADRESSE, LATITUDE, LONGITUDE, HORAIRES, JOURS_OUVERT, IMAGE_URL, EMAIL, TELEPHONE, ISPMR, ZONE, PAIEMENT, ACCES) 
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16) 
                                ON CONFLICT (RID) DO UPDATE SET
                                    IDTPR = $3,
                                    NOM = $4,
                                    ADRESSE = $5,
                                    LATITUDE = $6,
                                    LONGITUDE = $7,
                                    HORAIRES = $8,
                                    JOURS_OUVERT = $9,
                                    IMAGE_URL = $10,
                                    EMAIL = $11,
                                    TELEPHONE = $12,
                                    ISPMR = $13,
                                    ZONE = $14,
                                    PAIEMENT = $15,
                                    ACCES = $16
                            """, 
                            restaurant.id, 
                            region.id, 
                            tpRestaurantID, 
                            restaurant.title, 
                            restaurant.contact.address, 
                            restaurant.lat,
                            restaurant.lon, 
                            dumps(restaurant.infos.horaires) if restaurant.infos.horaires else None,
                            restaurant.opening,
                            restaurant.image_url, 
                            restaurant.contact.email,
                            restaurant.contact.phone,
                            restaurant.infos.pmr,
                            restaurant.zone, 
                            dumps(restaurant.infos.paiements) if restaurant.infos.paiements else None,
                            dumps(restaurant.infos.acces) if restaurant.infos.acces else None
                        )

                    await self.loadMenus(region, restaurant)


    async def loadMenus(self, region: Region, ru: RU) -> None:
        """
        Charge les menus et les enregistre dans la base de données.
        
        :param region: La région
        :type region: Region
        :param ru: Le restaurant universitaire
        :type ru: RU
        """
        self.logger.info(f"Chargement des menus pour le restaurant {ru.title}...")

        menus = await self.client.menu.get(region.id, ru.id)

        self.logger.info(f"{len(menus)} menus chargés pour le restaurant {ru.title} !")

        async with self.pool.acquire() as connection:
            connection: Connection

            async with connection.transaction():
                for menu in menus:
                    await connection.execute(
                        """
                            INSERT INTO MENU (MID, RID, DATE)
                            VALUES ($1, $2, $3) 
                            ON CONFLICT DO NOTHING
                        """, 
                        menu.id,
                        ru.id,
                        menu.date
                    )

                    for meal in menu.meals:
                        repasExist = await connection.fetchval("SELECT COUNT(*) FROM REPAS WHERE TPR = $1 AND MID = $2", meal.name, menu.id)
                        
                        if repasExist == 0:
                            await connection.execute(
                                """
                                    INSERT INTO REPAS (TPR, MID)
                                    VALUES ($1, $2) 
                                    ON CONFLICT DO NOTHING
                                """, 
                                meal.name,
                                menu.id,  
                            )

                            rpid = await connection.fetchval("SELECT RPID FROM REPAS WHERE TPR = $1 AND MID = $2", meal.name, menu.id)

                            for ordreCategory, category in enumerate(meal.categories):
                                categoryExist = await connection.fetchval("SELECT COUNT(*) FROM CATEGORIE WHERE TPCAT = $1 AND RPID = $2", category.name, rpid)

                                if categoryExist == 0:
                                    await connection.execute(
                                        """
                                            INSERT INTO CATEGORIE (TPCAT, ORDRE, RPID)
                                            VALUES ($1, $2, $3) 
                                            ON CONFLICT DO NOTHING
                                        """, 
                                        category.name,
                                        ordreCategory,
                                        rpid
                                    )

                                catid = await connection.fetchval("SELECT CATID FROM CATEGORIE WHERE TPCAT = $1 AND RPID = $2", category.name, rpid)

                                for ordreDish, dish in enumerate(category.dishes):
                                    dishExist = await connection.fetchval("SELECT COUNT(*) FROM PLAT WHERE LIBELLE = $1", dish.name)
                                    
                                    if dishExist == 0:
                                        await connection.execute(
                                            """
                                                INSERT INTO PLAT (LIBELLE)
                                                VALUES ($1) 
                                                ON CONFLICT DO NOTHING
                                            """, 
                                            dish.name
                                        )

                                    platid = await connection.fetchval("SELECT PLATID FROM PLAT WHERE LIBELLE = $1", dish.name)
                                    
                                    compositionExist = await connection.fetchval("SELECT COUNT(*) FROM COMPOSITION WHERE CATID = $1 AND PLATID = $2", catid, platid)
                                    
                                    if compositionExist == 0:
                                        await connection.execute(
                                            """
                                                INSERT INTO COMPOSITION (CATID, ORDRE, PLATID)
                                                VALUES ($1, $2, $3) 
                                                ON CONFLICT DO NOTHING
                                            """, 
                                            catid,
                                            ordreDish,
                                            platid
                                        )
