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
            for region in regions:
                await connection.execute(
                    """
                        INSERT INTO region (IDREG, LIBELLE) 
                        VALUES ($1, $2) 
                        ON CONFLICT DO NOTHING
                    """,
                    region.id,
                    region.name,
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

            for region in regions:
                self.logger.info(
                    f"Chargement des restaurants pour la région {region.name}..."
                )

                restaurants = await self._retry_ru_get(region.id)

                self.logger.info(
                    f"{len(restaurants)} restaurants chargés pour la région {region.name} !"
                )

                for restaurant in restaurants:
                    restaurant: RU

                    # Vérifie si le restaurant était actif lors de la dernière mise à jour. Limite le nombre de requêtes inutiles.
                    if restaurant.id not in self.restaurants:
                        self.logger.debug(
                            f"Le restaurant {restaurant.title} n'est pas actif !"
                        )
                        continue

                    tpRestaurantID = await connection.fetchval(
                        "SELECT IDTPR FROM TYPE_RESTAURANT WHERE LIBELLE = $1",
                        restaurant.type,
                    )

                    if not tpRestaurantID:
                        await connection.execute(
                            """
                                INSERT INTO type_restaurant (LIBELLE) 
                                VALUES ($1) 
                                ON CONFLICT DO NOTHING
                            """,
                            restaurant.type,
                        )

                        tpRestaurantID = await connection.fetchval(
                            "SELECT IDTPR FROM TYPE_RESTAURANT WHERE LIBELLE = $1",
                            restaurant.type,
                        )

                    async with connection.transaction():
                        if restaurant.feedId is not None:
                            # Si l'API a renuméroté le restaurant, libère l'ID du flux de l'ancien RID
                            await connection.execute(
                                "UPDATE RESTAURANT SET FEED_ID = NULL WHERE FEED_ID = $1 AND RID <> $2",
                                restaurant.feedId,
                                restaurant.id,
                            )

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
                            region.id,
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

                    if restaurant.image_url:
                        lastUpdate = await connection.fetchval(
                            "SELECT DERNIERE_MODIFICATION FROM RESTAURANT_IMAGE WHERE IMAGE_URL = $1",
                            restaurant.image_url,
                        )

                        if not lastUpdate or ((datetime.now() - lastUpdate).days >= 7):
                            await self.loadImage(restaurant.image_url)

                    if restaurant.id in self.restaurants:
                        self.restaurants.remove(restaurant.id)

                    if self.taskId:
                        await connection.execute(
                            """
                                INSERT INTO TACHE_LOG (RID, IDTACHE)
                                VALUES ($1, $2)
                            """,
                            restaurant.id,
                            self.taskId,
                        )

                    # if restaurant.open:
                    #     await self.loadMenus(region, restaurant)
                    # else:
                    #     self.logger.debug(f"Le restaurant {restaurant.title} est fermé ! Aucun menu ne sera chargé.")

                    # Le restaurant peut être fermé aujourd'hui mais les menus peuvent être disponibles pour les jours suivants
                    menus, _ = await self.loadMenus(region.id, restaurant.id, restaurant.title)

                    # Enregistre l'empreinte des menus : la synchronisation via les flux
                    # ne rechargera ce restaurant que si ses menus changent dans le flux
                    await connection.execute(
                        "UPDATE RESTAURANT SET FEED_MENUS_HASH = $1 WHERE RID = $2",
                        self.computeMenusHash(menus),
                        restaurant.id,
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

        written = 0

        async with self.pool.acquire() as connection:
            connection: Connection

            async with connection.transaction():
                for menu in menus:
                    # Calculer le hash du menu
                    menu_hash = self.compute_menu_hash(menu)

                    # Vérifier si le menu existe déjà et si son hash a changé
                    existing_hash = await connection.fetchval(
                        "SELECT MENU_HASH FROM MENU WHERE MID = $1",
                        menu.id,
                    )

                    # Si le hash n'a pas changé, on peut ignorer ce menu
                    if existing_hash == menu_hash:
                        await connection.execute(
                            """
                            UPDATE MENU
                            SET LAST_CHECKED = $2
                            WHERE MID = $1
                            """,
                            menu.id,
                            datetime.now(),
                        )
                        self.logger.debug(f"Menu {menu.id} inchangé, skip")
                        continue

                    written += 1

                    # Si le menu a changé ou n'existe pas, supprimer les anciens enregistrements liés
                    await connection.execute(
                        """
                            DELETE FROM COMPOSITION 
                            WHERE CATID IN (
                                SELECT CATID FROM CATEGORIE WHERE RPID IN (
                                    SELECT RPID FROM REPAS WHERE MID = $1
                                )
                            )
                        """,
                        menu.id,
                    )

                    await connection.execute(
                        """
                            DELETE FROM CATEGORIE 
                            WHERE RPID IN (
                                SELECT RPID FROM REPAS WHERE MID = $1
                            )
                        """,
                        menu.id,
                    )

                    await connection.execute(
                        "DELETE FROM REPAS WHERE MID = $1",
                        menu.id,
                    )

                    # Insérer ou mettre à jour le menu avec le nouveau hash
                    await connection.execute(
                        """
                            INSERT INTO MENU (MID, RID, DATE, MENU_HASH)
                            VALUES ($1, $2, $3, $4) 
                            ON CONFLICT (MID) DO UPDATE 
                            SET MENU_HASH = EXCLUDED.MENU_HASH
                        """,
                        menu.id,
                        rid,
                        menu.date,
                        menu_hash,
                    )

                    # Insérer les repas, catégories et compositions
                    for meal in menu.meals:
                        await connection.execute(
                            """
                                INSERT INTO REPAS (TPR, MID)
                                VALUES ($1, $2) 
                                ON CONFLICT DO NOTHING
                            """,
                            meal.name,
                            menu.id,
                        )

                        rpid = await connection.fetchval(
                            "SELECT RPID FROM REPAS WHERE TPR = $1 AND MID = $2",
                            meal.name,
                            menu.id,
                        )

                        for ordreCategory, category in enumerate(meal.categories):
                            await connection.execute(
                                """
                                    INSERT INTO CATEGORIE (TPCAT, ORDRE, RPID)
                                    VALUES ($1, $2, $3) 
                                    ON CONFLICT DO NOTHING
                                """,
                                category.name,
                                ordreCategory,
                                rpid,
                            )

                            catid = await connection.fetchval(
                                "SELECT CATID FROM CATEGORIE WHERE TPCAT = $1 AND RPID = $2",
                                category.name,
                                rpid,
                            )

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

                                # Essayer d'insérer le plat, ou récupérer l'ID s'il existe déjà
                                # Note: PLAT n'a pas de contrainte d'unicité sur LIBELLE, donc on vérifie d'abord
                                platid = await connection.fetchval(
                                    "SELECT PLATID FROM PLAT WHERE LIBELLE = $1 LIMIT 1",
                                    dish.name,
                                )

                                if platid is None:
                                    # Utiliser RETURNING pour obtenir l'ID atomiquement
                                    platid = await connection.fetchval(
                                        """
                                            INSERT INTO PLAT (LIBELLE)
                                            VALUES ($1)
                                            RETURNING PLATID
                                        """,
                                        dish.name,
                                    )

                                await connection.execute(
                                    """
                                        INSERT INTO COMPOSITION (CATID, ORDRE, PLATID)
                                        VALUES ($1, $2, $3) 
                                        ON CONFLICT DO NOTHING
                                    """,
                                    catid,
                                    ordreDish,
                                    platid,
                                )

        return menus, written

    async def loadImage(self, image_url: str) -> None:
        """
        Charge une image et l'enregistre dans la base de données.
        Cette méthode est utilisée pour éviter de charger plusieurs fois la même image et de limiter les requêtes inutiles à l'API du CROUS.

        :param image_url: L'URL de l'image
        :type image_url: str
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

                return

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

    async def updateRestaurantsStatus(self) -> None:
        """
        Met à jour le statut des restaurants.
        """
        self.logger.info("Mise à jour du statut des restaurants...")

        for restaurant in self.restaurants:
            async with self.pool.acquire() as connection:
                connection: Connection

                await connection.execute(
                    """
                        UPDATE RESTAURANT
                        SET ACTIF = FALSE
                        WHERE RID = $1
                    """,
                    restaurant,
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
