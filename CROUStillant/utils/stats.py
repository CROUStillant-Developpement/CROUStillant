STAT_KEYS = (
    "regions",
    "restaurants",
    "types_restaurants",
    "menus",
    "repas",
    "categories",
    "plats",
    "compositions",
    "actifs",
)

STAT_EMOJIS = {
    "regions": "🌍",
    "restaurants": "🍽️",
    "types_restaurants": "🏷️",
    "menus": "📋",
    "repas": "🍴",
    "categories": "📂",
    "plats": "🍛",
    "compositions": "🥗",
    "actifs": "✅",
}

STAT_LABELS = {
    "regions": "Régions",
    "restaurants": "Restaurants",
    "types_restaurants": "Types de restauration",
    "menus": "Menus",
    "repas": "Repas",
    "categories": "Catégories",
    "plats": "Plats",
    "compositions": "Compositions",
    "actifs": "Restaurants actifs",
}


def formatStats(stats: dict, previous: dict | None = None) -> str:
    """
    Formate le bloc de statistiques affiché dans le message Discord.
    Affiche l'évolution par rapport aux statistiques précédentes si fournies.

    :param stats: Les statistiques actuelles
    :type stats: dict
    :param previous: Les statistiques précédentes, pour afficher l'évolution
    :type previous: dict | None
    :return: Le bloc de statistiques formaté
    :rtype: str
    """
    lines = []

    for key in STAT_KEYS:
        value = stats[key]
        line = f"` {STAT_EMOJIS[key]} ` **` {value:,d} `** {STAT_LABELS[key].lower()}"

        if previous is not None:
            delta = value - previous[key]
            if delta > 0:
                line += f" (*` +{delta:,d} `*)"

        lines.append(line)

    return "\n".join(lines)


def formatDuration(seconds: float) -> str:
    """
    Formate une durée en secondes sous une forme lisible (ex : `2 min 15 sec`).

    :param seconds: La durée en secondes
    :type seconds: float
    :return: La durée formatée
    :rtype: str
    """
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    parts.append(f"{secs} sec")

    return " ".join(parts)


def formatError(error: Exception, elapsed: float, requests: int) -> str:
    """
    Formate le détail d'une erreur sous forme de citation, à intégrer dans le
    contenu d'un message (dans le même esprit que les messages d'erreur du bot).

    :param error: L'exception rencontrée
    :type error: Exception
    :param elapsed: Le temps écoulé avant l'échec, en secondes
    :type elapsed: float
    :param requests: Le nombre de requêtes effectuées avant l'échec
    :type requests: int
    :return: Le bloc de citation formaté
    :rtype: str
    """
    message = str(error).strip() or "Aucun détail fourni."

    return (
        f"> **{type(error).__name__}** : {message[:300]}\n"
        f"> ` ⏱️ ` Temps écoulé avant l'échec : ` {formatDuration(elapsed)} `\n"
        f"> ` 🌐 ` Requêtes effectuées : **` {requests:,d} `**"
    )
