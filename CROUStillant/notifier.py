from datetime import datetime
from os import environ

from aiohttp import ClientSession
from discord import Webhook
from discord.ui import LayoutView
from pytz import timezone

from CROUStillant.utils import formatDuration, formatError, formatStats
from CROUStillant.views import ErrorView, WorkerView

# Nombre maximum de restaurants listés dans le message de synchronisation via les flux
MAX_LISTED_RESTAURANTS = 10


class Notifier:
    """
    Envoie les messages des tâches sur le webhook Discord.
    """

    def __init__(self, session: ClientSession) -> None:
        """
        Constructeur de la classe Notifier.

        :param session: La session HTTP
        :type session: ClientSession
        """
        self.webhook = Webhook.from_url(environ["WEBHOOK_URL"], session=session)

    @property
    def footerText(self) -> str:
        year = datetime.now(timezone("Europe/Paris")).year
        return f"CROUStillant Développement © 2022 - {year} | Tous droits réservés."

    async def send(self, view: LayoutView) -> None:
        """
        Envoie un message sur le webhook Discord.

        :param view: Le message
        :type view: LayoutView
        """
        await self.webhook.send(view=view)

    async def sendWorker(self, content: str, stats: str) -> None:
        await self.send(
            WorkerView(
                content=content,
                stats=stats,
                thumbnail_url=environ["THUMBNAIL_URL"],
                banner_url=environ["IMAGE_URL"],
                footer_text=self.footerText,
            )
        )

    async def taskStarted(self, taskId: int, start: datetime, stats: dict) -> None:
        """
        Message de démarrage de la tâche complète.
        """
        await self.sendWorker(
            content=(
                f"## 🚀 • Tâche de fond démarrée !\n"
                f"Chargement des données en cours...\n\n"
                f"Tâche **`#{taskId}`** · Démarrée <t:{int(start.timestamp())}:R>"
            ),
            stats=formatStats(stats),
        )

    async def taskFinished(
        self,
        taskId: int,
        start: datetime,
        end: datetime,
        stats: dict,
        previous: dict,
        requests: int,
    ) -> None:
        """
        Message de fin de la tâche complète.
        """
        details = formatStats(stats, previous=previous)
        details += f"\n` ⏱️ ` Durée : ` {formatDuration((end - start).total_seconds())} `"
        details += f"\n` 🌐 ` Requêtes API : **` {requests:,d} `**"

        await self.sendWorker(
            content=(
                f"## ✅ • Tâche de fond terminée !\n"
                f"Données chargées avec succès.\n\n"
                f"Tâche **`#{taskId}`** · Terminée <t:{int(end.timestamp())}:R>"
            ),
            stats=details,
        )

    async def menusUpdated(
        self,
        taskId: int,
        start: datetime,
        end: datetime,
        restaurants: list[str],
        counters: dict,
        requests: int,
    ) -> None:
        """
        Message de la synchronisation via les flux, lorsque des menus ont été modifiés.
        """
        details = "\n".join(
            f"` 🍽️ ` {name}" for name in restaurants[:MAX_LISTED_RESTAURANTS]
        )
        if len(restaurants) > MAX_LISTED_RESTAURANTS:
            details += f"\n*… et {len(restaurants) - MAX_LISTED_RESTAURANTS} autres*"

        details += f"\n\n` 📡 ` Flux chargés : **` {counters['feeds']} `**"
        if counters["feeds_failed"]:
            details += f" (*` {counters['feeds_failed']} ` en échec*)"
        if counters["lagging"]:
            details += f"\n` ⏳ ` API pas encore à jour : **` {counters['lagging']} `** (nouvel essai au prochain passage)"
        if counters["failed"]:
            details += f"\n` ⚠️ ` Restaurants en échec : **` {counters['failed']} `**"
        details += f"\n` ⏱️ ` Durée : ` {formatDuration((end - start).total_seconds())} `"
        details += f"\n` 🌐 ` Requêtes : **` {requests:,d} `**"

        count = len(restaurants)

        await self.sendWorker(
            content=(
                f"## 🔄 • Menus mis à jour !\n"
                f"{count} restaurant{'s' if count > 1 else ''} mis à jour via les flux régionaux.\n\n"
                f"Tâche **`#{taskId}`** · Terminée <t:{int(end.timestamp())}:R>"
            ),
            stats=details,
        )

    async def error(
        self,
        title: str,
        error: Exception,
        start: datetime,
        requests: int,
        taskId: int | None = None,
    ) -> None:
        """
        Message d'erreur.
        """
        elapsed = (datetime.now() - start).total_seconds()
        task = f" Tâche **`#{taskId}`**" if taskId else ""

        await self.send(
            ErrorView(
                content=(
                    f"## ❌ • {title}\n"
                    f"L'API du CROUS est-elle indisponible ?{task}\n\n"
                    f"{formatError(error, elapsed, requests)}"
                ),
                thumbnail_url=environ["THUMBNAIL_URL"],
                banner_url=environ["IMAGE_URL"],
                footer_text=self.footerText,
            )
        )
