import hashlib
import asyncio

from CrousPy import Crous, Region, RU, Menu, Menus
from CROUStillant.logger import Logger
from asyncpg import Pool, Connection
from json import dumps
from datetime import datetime
from io import BytesIO
from PIL import Image


class Worker:
    def __init__(
        self, logger: Logger, pool: Pool, client: Crous, restaurants: list[int]
    ) -> None:
        """
        Constructeur de la classe Worker.

        :param logger: Le logger
        :type logger: Logger
        :param pool: Le pool de connexions
        :type pool: Pool
        :param client: Le client Crous
        :type client: Crous
        :param restaurants: Les restaurants actifs
        :type restaurants: list[int]
        """
        self.logger = logger
        self.pool = pool
        self.client = client
        self.restaurants = restaurants

        self.taskId = None
        self.requests = 0

        # Restaurants dont les menus ont été modifiés (RID, nom)
        self.updatedRestaurants: list[tuple[int, str]] = []

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
                    SELECT * FROM v_stats;
                """
            )

        return dict(stats)

    async def _retry(self, request, label: str, retries: int = 3, delay: float = 1.0):
        """
        Exécute une requête vers le CROUS avec plusieurs tentatives.

        :param request: Fonction sans argument retournant la coroutine de la requête
        :param label: Libellé de la requête (pour les logs)
        :type label: str
        :param retries: Nombre de tentatives
        :type retries: int
        :param delay: Délai de base entre les tentatives (secondes), multiplié par le numéro de la tentative
        :type delay: float
        :return: Le résultat de la requête
        """
        for attempt in range(1, retries + 1):
            try:
                self.logger.debug(f"{label} (attempt {attempt}/{retries})")
                result = await request()
                self.requests += 1
                return result
            except Exception as e:
                self.logger.warning(f"{label} failed (attempt {attempt}/{retries}): {e}")

                if attempt == retries:
                    self.logger.error(f"{label} failed after {retries} attempts")
                    raise

                await asyncio.sleep(delay * attempt)

    async def _retry_region_get(self, retries: int = 3, delay: float = 1.0) -> list[Region]:
        """
        Retry wrapper for self.client.region.get().

        This method logs each attempt, increments the request counter on
        successful calls, and retries the request a limited number of times
        before propagating the last encountered exception.

        :param retries: Number of attempts
        :type retries: int
        :param delay: Delay between attempts (seconds)
        :type delay: float
        :return: List of regions
        :rtype: list[Region]
        """
        last_exception = None

        for attempt in range(1, retries + 1):
            try:
                self.logger.debug(
                    f"GET /regions (attempt {attempt}/{retries})"
                )
                regions = await self.client.region.get()
                self.requests += 1
                return regions
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Failed to load regions "
                    f"(attempt {attempt}/{retries}): {e}"
                )

                if attempt < retries:
                    await asyncio.sleep(delay * attempt)

        self.logger.error(
            f"Failed to load regions after {retries} attempts"
        )

        if last_exception is not None:
            raise last_exception

        raise RuntimeError(
            "Failed to load regions after retries, but no exception was captured"
        )

    async def loadRegions(self) -> list[Region]:
        """
        Charge les régions et les enregistre dans la base de données.

        :return: Les régions
        :rtype: list[Region]
        """
        self.logger.info("Chargement des régions...")

        regions = await self._retry_region_get()

        self.logger.info(f"{len(regions)} régions chargées !")

        async with self.pool.acquire() as connection:
            connection: Connection

            await connection.execute(
                """
                    INSERT INTO region (IDREG, LIBELLE)
                    SELECT U.IDREG, U.LIBELLE
                    FROM unnest($1::int[], $2::text[]) AS U(IDREG, LIBELLE)
                    ON CONFLICT DO NOTHING
                """,
                [region.id for region in regions],
                [region.name for region in regions],
            )

        self.logger.info("Régions enregistrées !")

        return regions

    async def _retry_ru_get(self, region_id: int, retries: int = 3, delay: float = 1.0):
        """
        Retry wrapper for self.client.ru.get()

        :param region_id: Region ID
        :type region_id: int
        :param retries: Number of attempts
        :type retries: int
        :param delay: Delay between attempts (seconds)
        :type delay: float
        :return: List of restaurants for the specified region
        :rtype: list[RU]
        """
        last_exception = None

        for attempt in range(1, retries + 1):
            try:
                self.logger.debug(
                    f"GET /regions/{region_id}/restaurants (attempt {attempt}/{retries})"
                )
                restaurants = await self.client.ru.get(region_id)
                self.requests += 1
                return restaurants
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Failed to load restaurants for region {region_id} "
                    f"(attempt {attempt}/{retries}): {e}"
                )

                if attempt < retries:
                    await asyncio.sleep(delay * attempt)

        self.logger.error(
            f"Failed to load restaurants for region {region_id} after {retries} attempts"
        )

        if last_exception is not None:
            raise last_exception

        raise RuntimeError(
            "Failed to load restaurants after retries, but no exception was captured"
        )

    async def loadRestaurants(self, regions: list[Region]) -> None:
        """
        Charge les restaurants et les enregistre dans la base de données.

        :param regions: Les régions
        :type regions: list[Region]
        """
        self.logger.info("Chargement des restaurants...")

        async with self.pool.acquire() as connection:
            connection: Connection

            # Données de référence chargées une seule fois, plutôt qu'une requête par restaurant
            types: dict[str, int] = {}
            for row in await connection.fetch(
                "SELECT IDTPR, LIBELLE FROM TYPE_RESTAURANT WHERE LIBELLE IS NOT NULL ORDER BY IDTPR"
            ):
                types.setdefault(row["libelle"], row["idtpr"])

            images: dict[str, datetime | None] = {
                row["image_url"]: row["derniere_modification"]
                for row in await connection.fetch(
                    "SELECT IMAGE_URL, DERNIERE_MODIFICATION FROM RESTAURANT_IMAGE"
                )
            }

            feedOwners: dict[int, int] = {
                row["feed_id"]: row["rid"]
                for row in await connection.fetch(
                    "SELECT RID, FEED_ID FROM RESTAURANT WHERE FEED_ID IS NOT NULL"
                )
            }

            for region in regions:
                self.logger.info(
                    f"Chargement des restaurants pour la région {region.name}..."
                )

                restaurants = await self._retry_ru_get(region.id)

                self.logger.info(
                    f"{len(restaurants)} restaurants chargés pour la région {region.name} !"
                )

                # Restaurants traités et empreintes de leurs menus : enregistrés en une fois par région
                processed: list[int] = []
                menusHashes: dict[int, str] = {}

                try:
                    for restaurant in restaurants:
                        restaurant: RU

                        # Vérifie si le restaurant était actif lors de la dernière mise à jour. Limite le nombre de requêtes inutiles.
                        if restaurant.id not in self.restaurants:
                            self.logger.debug(
                                f"Le restaurant {restaurant.title} n'est pas actif !"
                            )
                            continue

                        tpRestaurantID = types.get(restaurant.type)

                        if tpRestaurantID is None and restaurant.type is not None:
                            tpRestaurantID = await connection.fetchval(
                                """
                                    INSERT INTO type_restaurant (LIBELLE)
                                    VALUES ($1)
                                    RETURNING IDTPR
                                """,
                                restaurant.type,
                            )
                            types[restaurant.type] = tpRestaurantID

                        if (
                            restaurant.feedId is not None
                            and feedOwners.get(restaurant.feedId, restaurant.id) != restaurant.id
                        ):
                            async with connection.transaction():
                                # L'API a renuméroté le restaurant : libère l'ID du flux de l'ancien RID
                                await connection.execute(
                                    "UPDATE RESTAURANT SET FEED_ID = NULL WHERE FEED_ID = $1 AND RID <> $2",
                                    restaurant.feedId,
                                    restaurant.id,
                                )

                                await self.saveRestaurant(
                                    connection, region.id, restaurant, tpRestaurantID
                                )
                        else:
                            await self.saveRestaurant(
                                connection, region.id, restaurant, tpRestaurantID
                            )

                        if restaurant.feedId is not None:
                            feedOwners[restaurant.feedId] = restaurant.id

                        if restaurant.image_url:
                            lastUpdate = images.get(restaurant.image_url)

                            if (
                                not lastUpdate or ((datetime.now() - lastUpdate).days >= 7)
                            ) and await self.loadImage(restaurant.image_url):
                                images[restaurant.image_url] = datetime.now()

                        if restaurant.id in self.restaurants:
                            self.restaurants.remove(restaurant.id)

                        processed.append(restaurant.id)

                        # if restaurant.open:
                        #     await self.loadMenus(region, restaurant)
                        # else:
                        #     self.logger.debug(f"Le restaurant {restaurant.title} est fermé ! Aucun menu ne sera chargé.")

                        # Le restaurant peut être fermé aujourd'hui mais les menus peuvent être disponibles pour les jours suivants
                        menus, _ = await self.loadMenus(region.id, restaurant.id, restaurant.title)

                        # Empreinte des menus : la synchronisation via les flux
                        # ne rechargera ce restaurant que si ses menus changent dans le flux
                        menusHashes[restaurant.id] = self.computeMenusHash(menus)
                finally:
                    # Y compris en cas d'erreur, pour garder la trace des restaurants déjà traités
                    await self.saveRegionProgress(connection, processed, menusHashes)

    async def saveRestaurant(
        self, connection: Connection, regionId: int, restaurant: RU, tpRestaurantID: int | None
    ) -> None:
        """
        Enregistre (ou met à jour) un restaurant dans la base de données.

        :param connection: La connexion à la base de données
        :type connection: Connection
        :param regionId: L'ID de la région
        :type regionId: int
        :param restaurant: Le restaurant
        :type restaurant: RU
        :param tpRestaurantID: L'ID du type de restaurant
        :type tpRestaurantID: int | None
        """
        await connection.execute(
            """
                INSERT INTO restaurant (RID, IDREG, IDTPR, NOM, ADRESSE, LATITUDE, LONGITUDE, HORAIRES, JOURS_OUVERT, IMAGE_URL, EMAIL, TELEPHONE, ISPMR, ZONE, PAIEMENT, ACCES, OPENED, AJOUT, FEED_ID)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
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
                    ACCES = $16,
                    OPENED = $17,
                    MIS_A_JOUR = $18,
                    FEED_ID = $19
            """,
            restaurant.id,
            regionId,
            tpRestaurantID,
            restaurant.title,
            restaurant.contact.address,
            restaurant.lat,
            restaurant.lon,
            dumps(restaurant.infos.horaires)
            if restaurant.infos.horaires
            else None,
            restaurant.opening,
            restaurant.image_url,
            restaurant.contact.email,
            restaurant.contact.phone,
            restaurant.infos.pmr,
            restaurant.zone,
            dumps(restaurant.infos.paiements)
            if restaurant.infos.paiements
            else None,
            dumps(restaurant.infos.acces)
            if restaurant.infos.acces
            else None,
            restaurant.open,
            datetime.now(),
            restaurant.feedId,
        )

    async def saveRegionProgress(
        self, connection: Connection, processed: list[int], menusHashes: dict[int, str]
    ) -> None:
        """
        Enregistre, en une requête chacun, les restaurants traités par la tâche et
        l'empreinte de leurs menus.

        :param connection: La connexion à la base de données
        :type connection: Connection
        :param processed: Les RIDs des restaurants traités
        :type processed: list[int]
        :param menusHashes: L'empreinte des menus de chaque restaurant (RID -> hash)
        :type menusHashes: dict[int, str]
        """
        if processed and self.taskId:
            await connection.execute(
                """
                    INSERT INTO TACHE_LOG (RID, IDTACHE)
                    SELECT U.RID, $2::int
                    FROM unnest($1::int[]) AS U(RID)
                    ON CONFLICT DO NOTHING
                """,
                processed,
                self.taskId,
            )

        if menusHashes:
            await connection.execute(
                """
                    UPDATE RESTAURANT R
                    SET FEED_MENUS_HASH = U.MENUS_HASH
                    FROM unnest($1::int[], $2::text[]) AS U(RID, MENUS_HASH)
                    WHERE R.RID = U.RID
                """,
                list(menusHashes.keys()),
                list(menusHashes.values()),
            )

    def _menuData(self, menu: Menu) -> dict:
        """
        Représentation structurée du contenu d'un menu, utilisée pour le hachage.

        :param menu: Le menu
        :type menu: Menu
        :return: Le contenu du menu
        :rtype: dict
        """
        # Note: On n'inclut pas l'ID car on compare par ID, uniquement le contenu
        menu_data = {
            "date": str(menu.date),
            "meals": []
        }

        for meal in menu.meals:
            meal_data = {
                "name": meal.name,
                "categories": []
            }

            for category in meal.categories:
                category_data = {
                    "name": category.name,
                    "dishes": [dish.name for dish in category.dishes]
                }
                meal_data["categories"].append(category_data)

            menu_data["meals"].append(meal_data)

        return menu_data

    def compute_menu_hash(self, menu: Menu) -> str:
        """
        Calcule un hash unique pour un menu basé sur son contenu complet.

        :param menu: Le menu pour lequel calculer le hash
        :type menu: Menu
        :return: Hash SHA256 du contenu du menu
        :rtype: str
        """
        menu_json = dumps(self._menuData(menu), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(menu_json.encode('utf-8')).hexdigest()

    def computeMenusHash(self, menus: Menus) -> str:
        """
        Calcule un hash de l'ensemble des menus d'un restaurant.

        Les menus des flux et ceux de l'API sont représentés par les mêmes entités :
        un contenu identique donne donc le même hash, quelle que soit la source.

        :param menus: Les menus du restaurant
        :type menus: Menus
        :return: Hash SHA256 du contenu des menus
        :rtype: str
        """
        menus_json = dumps(
            [self._menuData(menu) for menu in menus], sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(menus_json.encode('utf-8')).hexdigest()

    async def _retry_menu_get(self, region_id: int, ru_id: int, retries: int = 3, delay: float = 1.0):
        """
        Récupère les menus d'un restaurant avec une logique de nouvelle tentative
        en cas d'échec de l'appel à ``self.client.menu.get``.

        Cette méthode encapsule l'appel à l'API des menus avec un nombre maximal
        de tentatives configurables et un délai croissant entre chaque tentative.

        :param region_id: Identifiant de la région du restaurant cible.
        :type region_id: int
        :param ru_id: Identifiant du restaurant universitaire pour lequel charger les menus.
        :type ru_id: int
        :param retries: Nombre maximal de tentatives avant d'abandonner.
        :type retries: int
        :param delay: Délai de base (en secondes) avant la prochaine tentative, multiplié par le numéro de la tentative.
        :type delay: float
        :return: Liste des menus récupérés pour le restaurant.
        :rtype: list[Menu]
        :raises Exception: Relève la dernière exception rencontrée si toutes les tentatives échouent.
        """
        last_exception = None

        for attempt in range(1, retries + 1):
            try:
                self.logger.debug(
                    f"GET /regions/{region_id}/restaurants/{ru_id}/menus (attempt {attempt}/{retries})"
                )
                menus = await self.client.menu.get(region_id, ru_id)
                self.requests += 1
                return menus
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Failed to load menus for restaurant {ru_id} in region {region_id} "
                    f"(attempt {attempt}/{retries}): {e}"
                )

                if attempt < retries:
                    await asyncio.sleep(delay * attempt)

        self.logger.error(
            f"Failed to load menus for restaurant {ru_id} in region {region_id} after {retries} attempts"
        )

        if last_exception is not None:
            raise last_exception

        raise RuntimeError(
            "Failed to load menus after retries, but no exception was captured"
        )

    async def loadMenus(self, regionId: int, rid: int, title: str) -> tuple[Menus, int]:
        """
        Charge les menus et les enregistre dans la base de données.

        :param regionId: L'ID de la région
        :type regionId: int
        :param rid: L'ID du restaurant universitaire
        :type rid: int
        :param title: Le nom du restaurant (pour les logs)
        :type title: str
        :return: Les menus chargés et le nombre de menus créés ou modifiés
        :rtype: tuple[Menus, int]
        """
        self.logger.info(f"Chargement des menus pour le restaurant {title}...")

        menus = await self._retry_menu_get(regionId, rid)

        self.logger.info(f"{len(menus)} menus chargés pour le restaurant {title} !")

        if len(menus) == 0:
            return menus, 0

        # Calculer le hash de chaque menu
        hashes = {menu.id: self.compute_menu_hash(menu) for menu in menus}

        async with self.pool.acquire() as connection:
            connection: Connection

            async with connection.transaction():
                # Récupérer le hash des menus déjà enregistrés
                rows = await connection.fetch(
                    "SELECT MID, MENU_HASH FROM MENU WHERE MID = ANY($1::int[])",
                    list(hashes.keys()),
                )
                existing = {row["mid"]: row["menu_hash"] for row in rows}

                # Si le hash n'a pas changé, on peut ignorer ce menu
                unchanged = [
                    mid for mid, menu_hash in hashes.items() if existing.get(mid) == menu_hash
                ]
                changed = {
                    menu.id: menu for menu in menus if existing.get(menu.id) != hashes[menu.id]
                }

                if unchanged:
                    await connection.execute(
                        """
                            UPDATE MENU
                            SET LAST_CHECKED = $2
                            WHERE MID = ANY($1::int[])
                        """,
                        unchanged,
                        datetime.now(),
                    )
                    self.logger.debug(f"{len(unchanged)} menus inchangés, skip")

                if changed:
                    await self.saveMenus(connection, rid, list(changed.values()), hashes)

        return menus, len(changed)

    async def saveMenus(
        self, connection: Connection, rid: int, menus: list[Menu], hashes: dict[int, str]
    ) -> None:
        """
        Enregistre des menus nouveaux ou modifiés, avec leurs repas, catégories et plats.

        Chaque table est écrite en une seule requête pour l'ensemble des menus, quel que
        soit le nombre de repas, de catégories et de plats.

        :param connection: La connexion à la base de données (dans une transaction)
        :type connection: Connection
        :param rid: L'ID du restaurant universitaire
        :type rid: int
        :param menus: Les menus à enregistrer
        :type menus: list[Menu]
        :param hashes: Le hash de chaque menu (MID -> hash)
        :type hashes: dict[int, str]
        """
        mids = [menu.id for menu in menus]

        # Supprimer les anciens enregistrements liés
        await connection.execute(
            """
                DELETE FROM COMPOSITION
                WHERE CATID IN (
                    SELECT CATID FROM CATEGORIE WHERE RPID IN (
                        SELECT RPID FROM REPAS WHERE MID = ANY($1::int[])
                    )
                )
            """,
            mids,
        )

        await connection.execute(
            """
                DELETE FROM CATEGORIE
                WHERE RPID IN (
                    SELECT RPID FROM REPAS WHERE MID = ANY($1::int[])
                )
            """,
            mids,
        )

        await connection.execute(
            "DELETE FROM REPAS WHERE MID = ANY($1::int[])",
            mids,
        )

        # Insérer ou mettre à jour les menus avec le nouveau hash
        await connection.execute(
            """
                INSERT INTO MENU (MID, RID, DATE, MENU_HASH)
                SELECT U.MID, $2::int, U.DATE, U.MENU_HASH
                FROM unnest($1::int[], $3::date[], $4::text[]) AS U(MID, DATE, MENU_HASH)
                ON CONFLICT (MID) DO UPDATE
                SET MENU_HASH = EXCLUDED.MENU_HASH
            """,
            mids,
            rid,
            [menu.date for menu in menus],
            [hashes[mid] for mid in mids],
        )

        # Insérer les repas : un par (menu, type de repas)
        repas = list(
            dict.fromkeys((menu.id, meal.name) for menu in menus for meal in menu.meals)
        )

        if not repas:
            return

        rows = await connection.fetch(
            """
                INSERT INTO REPAS (TPR, MID)
                SELECT U.TPR, U.MID
                FROM unnest($1::text[], $2::int[]) AS U(TPR, MID)
                RETURNING RPID, TPR, MID
            """,
            [tpr for _, tpr in repas],
            [mid for mid, _ in repas],
        )
        rpids = {(row["mid"], row["tpr"]): row["rpid"] for row in rows}

        # Insérer les catégories : une par (repas, nom), à la position de sa première occurrence
        categories: dict[tuple[int, str], int] = {}

        for menu in menus:
            for meal in menu.meals:
                rpid = rpids[(menu.id, meal.name)]

                for ordreCategory, category in enumerate(meal.categories):
                    categories.setdefault((rpid, category.name), ordreCategory)

        if not categories:
            return

        rows = await connection.fetch(
            """
                INSERT INTO CATEGORIE (TPCAT, ORDRE, RPID)
                SELECT U.TPCAT, U.ORDRE, U.RPID
                FROM unnest($1::text[], $2::int[], $3::int[]) AS U(TPCAT, ORDRE, RPID)
                RETURNING CATID, TPCAT, RPID
            """,
            [tpcat for _, tpcat in categories],
            list(categories.values()),
            [rpid for rpid, _ in categories],
        )
        catids = {(row["rpid"], row["tpcat"]): row["catid"] for row in rows}

        # Compositions : une par (catégorie, plat), à la position de sa première occurrence
        compositions: dict[tuple[int, str], int] = {}

        for menu in menus:
            for meal in menu.meals:
                rpid = rpids[(menu.id, meal.name)]

                for category in meal.categories:
                    catid = catids[(rpid, category.name)]

                    for ordreDish, dish in enumerate(category.dishes):
                        # Vérifie la longueur du nom du plat pour éviter les erreurs de dépassement de capacité de la base de données
                        if len(dish.name) >= 499:
                            self.logger.critical(
                                f"Le plat '{dish.name}' est trop long ({len(dish.name)} caractères). Debug: [RID: {rid}, RPID: {rpid}, CATID: {catid}]"
                            )
                            # Ignore ce plat
                            continue

                        if not dish.name.strip():
                            self.logger.critical(
                                f"Le plat a un nom vide. Debug: [RID: {rid}, RPID: {rpid}, CATID: {catid}]"
                            )
                            # Ignore ce plat
                            continue

                        compositions.setdefault((catid, dish.name), ordreDish)

        if not compositions:
            return

        # Récupérer l'ID des plats existants, puis insérer ceux qui manquent
        # Note: PLAT n'a pas de contrainte d'unicité sur LIBELLE, donc on vérifie d'abord
        libelles = list(dict.fromkeys(libelle for _, libelle in compositions))

        rows = await connection.fetch(
            """
                SELECT LIBELLE, MIN(PLATID) AS PLATID
                FROM PLAT
                WHERE LIBELLE = ANY($1::text[])
                GROUP BY LIBELLE
            """,
            libelles,
        )
        platids = {row["libelle"]: row["platid"] for row in rows}

        missing = [libelle for libelle in libelles if libelle not in platids]

        if missing:
            rows = await connection.fetch(
                """
                    INSERT INTO PLAT (LIBELLE)
                    SELECT U.LIBELLE
                    FROM unnest($1::text[]) AS U(LIBELLE)
                    RETURNING PLATID, LIBELLE
                """,
                missing,
            )
            platids.update({row["libelle"]: row["platid"] for row in rows})

        await connection.execute(
            """
                INSERT INTO COMPOSITION (CATID, ORDRE, PLATID)
                SELECT U.CATID, U.ORDRE, U.PLATID
                FROM unnest($1::int[], $2::int[], $3::int[]) AS U(CATID, ORDRE, PLATID)
                ON CONFLICT DO NOTHING
            """,
            [catid for catid, _ in compositions],
            list(compositions.values()),
            [platids[libelle] for _, libelle in compositions],
        )

    async def loadImage(self, image_url: str) -> bool:
        """
        Charge une image et l'enregistre dans la base de données.
        Cette méthode est utilisée pour éviter de charger plusieurs fois la même image et de limiter les requêtes inutiles à l'API du CROUS.

        :param image_url: L'URL de l'image
        :type image_url: str
        :return: ``True`` si l'image a été enregistrée, ``False`` si elle n'a pas pu être chargée
        :rtype: bool
        """
        try:
            self.logger.debug(f"GET {image_url}")

            image_binary = BytesIO(await self.client.image.get(image_url))

            self.logger.info(f"Image {image_url} chargée !")
        except Exception as e:
            self.logger.error(f"Impossible de charger l'image {image_url} ({e}) !")
            image_binary = None

        if image_binary:
            try:
                image = Image.open(image_binary)
            except Exception as e:
                self.logger.error(f"Impossible de charger l'image {image_url} ({e}) !")

                # Enregistre l'image sans le contenu brut si l'image n'est pas valide
                async with self.pool.acquire() as connection:
                    connection: Connection

                    await connection.execute(
                        """
                            INSERT INTO RESTAURANT_IMAGE (
                                IMAGE_URL, RAW_IMAGE, DERNIERE_MODIFICATION
                            )
                            VALUES (
                                $1, NULL, $2
                            )
                            ON CONFLICT (IMAGE_URL) DO UPDATE SET 
                                DERNIERE_MODIFICATION = $2
                        """,
                        image_url,
                        datetime.now(),
                    )

                return True

            if not image.mode == "RGB":
                image = image.convert("RGB")

            b = BytesIO()
            image.save(b, format="JPEG", compress_level=1, quality=95)
            image_bytes = b.getvalue()

            async with self.pool.acquire() as connection:
                connection: Connection

                await connection.execute(
                    """
                        INSERT INTO RESTAURANT_IMAGE (
                            IMAGE_URL, RAW_IMAGE, DERNIERE_MODIFICATION
                        )
                        VALUES (
                            $1, $2, $3
                        )
                        ON CONFLICT (IMAGE_URL) DO UPDATE SET 
                            RAW_IMAGE = $2,
                            DERNIERE_MODIFICATION = $3
                    """,
                    image_url,
                    image_bytes,
                    datetime.now(),
                )

            self.logger.info(f"Image {image_url} enregistrée !")

            return True

        return False

    async def updateRestaurantsStatus(self) -> None:
        """
        Met à jour le statut des restaurants.
        """
        self.logger.info("Mise à jour du statut des restaurants...")

        if self.restaurants:
            async with self.pool.acquire() as connection:
                connection: Connection

                await connection.execute(
                    """
                        UPDATE RESTAURANT
                        SET ACTIF = FALSE
                        WHERE RID = ANY($1::int[])
                    """,
                    self.restaurants,
                )

        self.logger.info("Statut des restaurants mis à jour !")

    async def syncFromFeeds(self) -> dict:
        """
        Synchronise les menus à partir des flux régionaux du CROUS.

        Les flux (un fichier par région, régénéré toutes les 15 minutes) contiennent
        tous les restaurants et leurs menus, mais sans ID de menu. Ils servent donc
        uniquement à détecter les restaurants dont les menus ont changé : seuls
        ceux-ci sont rechargés depuis l'API, qui fournit les IDs de menus.

        L'empreinte d'un restaurant (FEED_MENUS_HASH) n'est mise à jour que si les
        menus de l'API correspondent à ceux du flux. Si l'API n'est pas encore à jour
        (elle est synchronisée à partir des flux avec un léger décalage), le
        restaurant sera simplement rechargé lors de la prochaine synchronisation.

        :return: Les compteurs de la synchronisation
        :rtype: dict
        """
        self.logger.info("Synchronisation des menus via les flux régionaux...")

        counters = {
            "feeds": 0,
            "feeds_failed": 0,
            "restaurants": 0,
            "changed": 0,
            "updated": 0,
            "lagging": 0,
            "failed": 0,
            "ignored": 0,
            "opened": 0,
        }

        feeds = await self._retry(self.client.feed.get, "GET /feed/feeds.json")

        semaphore = asyncio.Semaphore(5)

        async def fetchFeed(feed):
            async with semaphore:
                return await self._retry(
                    lambda: self.client.feed.getByURL(feed.url), f"GET {feed.url}"
                )

        results = await asyncio.gather(
            *(fetchFeed(feed) for feed in feeds.feeds), return_exceptions=True
        )

        feedRestaurants = []
        for feed, result in zip(feeds.feeds, results):
            if isinstance(result, BaseException):
                counters["feeds_failed"] += 1
                self.logger.error(f"Impossible de charger le flux {feed.name} : {result}")
                continue

            counters["feeds"] += 1
            feedRestaurants.extend(result.rus)

        if counters["feeds"] == 0:
            raise RuntimeError("Aucun flux régional n'a pu être chargé")

        async with self.pool.acquire() as connection:
            connection: Connection

            rows = await connection.fetch(
                """
                    SELECT RID, IDREG, NOM, FEED_ID, FEED_MENUS_HASH
                    FROM RESTAURANT
                    WHERE ACTIF = TRUE AND FEED_ID IS NOT NULL
                """
            )

        known = {row["feed_id"]: row for row in rows}

        changed = []
        opened = []
        for feedRu in feedRestaurants:
            row = known.get(feedRu.id)

            if row is None:
                # Restaurant inactif ou pas encore connu : pris en compte par la tâche complète
                counters["ignored"] += 1
                continue

            counters["restaurants"] += 1
            opened.append((row["rid"], feedRu.open))

            feedHash = self.computeMenusHash(feedRu.menus)
            if feedHash != row["feed_menus_hash"]:
                changed.append((row, feedHash))

        counters["changed"] = len(changed)

        self.logger.info(
            f"{counters['feeds']} flux chargés, {counters['restaurants']} restaurants, "
            f"{counters['changed']} avec des menus modifiés"
        )

        async with self.pool.acquire() as connection:
            connection: Connection

            status = await connection.execute(
                """
                    UPDATE RESTAURANT R
                    SET OPENED = U.OPENED
                    FROM unnest($1::int[], $2::bool[]) AS U(RID, OPENED)
                    WHERE R.RID = U.RID AND R.OPENED IS DISTINCT FROM U.OPENED
                """,
                [rid for rid, _ in opened],
                [isOpen for _, isOpen in opened],
            )
            counters["opened"] = int(status.split()[-1])

        for row, feedHash in changed:
            try:
                menus, written = await self.loadMenus(row["idreg"], row["rid"], row["nom"])
            except Exception as e:
                counters["failed"] += 1
                self.logger.error(
                    f"Impossible de charger les menus du restaurant {row['nom']} ({row['rid']}) : {e}"
                )
                continue

            if written:
                counters["updated"] += 1
                self.updatedRestaurants.append((row["rid"], row["nom"]))

            if self.computeMenusHash(menus) != feedHash:
                # L'API n'est pas encore à jour : nouvel essai à la prochaine synchronisation
                counters["lagging"] += 1
                self.logger.warning(
                    f"Les menus de l'API du restaurant {row['nom']} ({row['rid']}) "
                    f"ne correspondent pas encore au flux"
                )
                continue

            async with self.pool.acquire() as connection:
                connection: Connection

                await connection.execute(
                    "UPDATE RESTAURANT SET FEED_MENUS_HASH = $1 WHERE RID = $2",
                    feedHash,
                    row["rid"],
                )

        self.logger.info(f"Synchronisation via les flux terminée : {counters}")

        return counters
