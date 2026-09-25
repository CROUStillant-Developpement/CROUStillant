from CROUStillant.tasks.feed import runFeed
from CROUStillant.tasks.full import runFull

# Tâches disponibles, par mode (argument de la ligne de commande)
TASKS = {
    "full": runFull,
    "feed": runFeed,
}

__all__ = (
    "TASKS",
    "runFeed",
    "runFull",
)
