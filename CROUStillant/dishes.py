from asyncpg import Connection, Pool
from croustillant_classifier import VERSION, Analysis, Classifier, category_type

from CROUStillant.logger import Logger


class DishAnalyser:
    """
    Analyse les libellés de plats bruts avec `croustillant_classifier` et enregistre
    le résultat (PLAT_ANALYSE, PLAT_COMPOSANT, PLAT_CANONIQUE).

    Un plat canonique déjà en base n'est jamais modifié ici : son type a pu être
    revu à la main, c'est lui qui fait foi. Seuls les nouveaux plats canoniques
    sont créés, avec le type proposé par le classifieur.
    """

    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.classifier = Classifier()
        # catégories déjà enregistrées dans TYPE_CATEGORIE pendant cette tâche
        self._categories: set[str] = set()

    async def registerCategory(self, connection: Connection, tpcat: str) -> None:
        """
        Enregistre le type porté par une catégorie de menu (utilisé par V_COMPOSITION_TYPEE).

        :param connection: La connexion
        :param tpcat: Le libellé de la catégorie
        """
        if not tpcat or not tpcat.strip() or tpcat in self._categories:
            return
        await connection.execute(
            "INSERT INTO TYPE_CATEGORIE (TPCAT, TYPE_PLAT) VALUES ($1, $2) ON CONFLICT (TPCAT) DO NOTHING",
            tpcat,
            category_type(tpcat),
        )
        self._categories.add(tpcat)

    async def analyse(self, connection: Connection, platid: int, libelle: str, category: str | None) -> None:
        """
        Analyse un plat et enregistre le résultat. Ne lève jamais d'exception :
        une erreur d'analyse ne doit pas bloquer l'ingestion des menus.

        :param connection: La connexion (dans la transaction de l'ingestion)
        :param platid: L'identifiant du plat
        :param libelle: Le libellé brut
        :param category: La catégorie du menu où le plat apparaît
        """
        try:
            async with connection.transaction():
                await self._save(connection, platid, self.classifier.analyse(libelle, category))
        except Exception as e:
            self.logger.error(f"Analyse du plat {platid} impossible ({e}) : {libelle!r}")

    async def analysePending(self, pool: Pool, batch: int = 1000) -> int:
        """
        Analyse les plats jamais analysés, ou analysés par une autre version du
        classifieur (rattrapage après une erreur ou une mise à jour).

        :return: Le nombre de plats analysés
        """
        total = 0
        async with pool.acquire() as connection:
            while True:
                rows = await connection.fetch(
                    """
                        SELECT p.PLATID, p.LIBELLE,
                               (SELECT ca.TPCAT FROM COMPOSITION co JOIN CATEGORIE ca ON ca.CATID = co.CATID
                                WHERE co.PLATID = p.PLATID LIMIT 1) AS TPCAT
                        FROM PLAT p
                        LEFT JOIN PLAT_ANALYSE pa ON pa.PLATID = p.PLATID
                        WHERE pa.PLATID IS NULL OR pa.VERSION <> $1
                        ORDER BY p.PLATID
                        LIMIT $2
                    """,
                    VERSION,
                    batch,
                )
                if not rows:
                    break
                for row in rows:
                    await self.analyse(connection, row["platid"], row["libelle"], row["tpcat"])
                total += len(rows)

        if total:
            self.logger.info(f"{total} plats analysés (classifieur {VERSION})")
        return total

    async def _save(self, connection: Connection, platid: int, a: Analysis) -> None:
        p = a.parsed
        nature = p.kind if p.kind in ("DISH", "INFO", "JUNK", "ALLERGENS", "PRICE") else "JUNK"

        await connection.execute("DELETE FROM PLAT_COMPOSANT WHERE PLATID = $1", platid)
        await connection.execute(
            """
                INSERT INTO PLAT_ANALYSE (PLATID, NATURE, TYPE_INFO, LIBELLE_NET, POINTS, POINTS_NOTE, PRIX,
                    ALLERGENES, ORIGINES, LABELS, VIANDES, DETAILS, VEGETARIEN, STATION, INDICE_SECTION,
                    DRAPEAUX, VERSION, TRAITE_LE)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, CURRENT_TIMESTAMP)
                ON CONFLICT (PLATID) DO UPDATE SET
                    NATURE = EXCLUDED.NATURE, TYPE_INFO = EXCLUDED.TYPE_INFO, LIBELLE_NET = EXCLUDED.LIBELLE_NET,
                    POINTS = EXCLUDED.POINTS, POINTS_NOTE = EXCLUDED.POINTS_NOTE, PRIX = EXCLUDED.PRIX,
                    ALLERGENES = EXCLUDED.ALLERGENES, ORIGINES = EXCLUDED.ORIGINES, LABELS = EXCLUDED.LABELS,
                    VIANDES = EXCLUDED.VIANDES, DETAILS = EXCLUDED.DETAILS, VEGETARIEN = EXCLUDED.VEGETARIEN,
                    STATION = EXCLUDED.STATION, INDICE_SECTION = EXCLUDED.INDICE_SECTION,
                    DRAPEAUX = EXCLUDED.DRAPEAUX, VERSION = EXCLUDED.VERSION, TRAITE_LE = EXCLUDED.TRAITE_LE
            """,
            platid, nature, p.info_kind, (p.name or None) and p.name[:500], p.points, p.points_note,
            p.prices or None, p.allergen_ids or None, p.origins or None, p.labels or None, p.meats or None,
            p.details or None, p.vegetarian, p.station, p.section_hint, p.flags or None, VERSION,
        )

        if not a.is_dish:
            return

        for ordre, c in enumerate(a.components):
            # ON CONFLICT ... DO UPDATE sans changement réel : renvoie l'IDPC existant
            # sans toucher au type déjà revu
            idpc = await connection.fetchval(
                """
                    INSERT INTO PLAT_CANONIQUE (CLE, LIBELLE, TYPE_PLAT, VEGETARIEN, CONFIANCE, SOURCE, A_REVOIR, REVUE)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (CLE) DO UPDATE SET CLE = EXCLUDED.CLE
                    RETURNING IDPC
                """,
                c.key, c.label[:500], c.type if c.type != "INFO" else "AUTRE", c.vegetarian, c.confidence,
                c.source, c.needs_review or c.source in ("head", "none"), c.review or None,
            )
            await connection.execute(
                "INSERT INTO PLAT_COMPOSANT (PLATID, ORDRE, IDPC, LIBELLE) VALUES ($1, $2, $3, $4)",
                platid, ordre, idpc, c.label[:500],
            )
