<div align="center">
<img src="https://croustillant.menu/logo.png" alt="CROUStillant Logo"/>
  
# CROUStillant
CROUStillant est un projet qui a pour but de fournir les menus des restaurants universitaires en France et en Outre-Mer. 

</div>
  
# 📖 • Sommaire

- [🚀 • Présentation](#--présentation)
- [📦 • Installation](#--installation)
- [💻 • Utilisation](#--utilisation)
- [🔍 • To Do](#--to-do)
- [📃 • Crédits](#--crédits)
- [📝 • License](#--license)

# 🚀 • Présentation

Ce dépôt contient la tâche de fond sur laquelle tous les services de CROUStillant s'appuient. Elle est responsable de la récupération des données des menus des restaurants universitaires et de leur stockage dans une base de données.

# 📦 • Installation

Pour installer CROUStillant, vous aurez besoin de [Docker](https://www.docker.com/) et de [Docker Compose](https://docs.docker.com/compose/).

Pour cloner le dépôt, exécutez la commande suivante :
```bash
git clone https://github.com/CROUStillant-Developpement/CROUStillant
```

Il vous faudra ensuite créer un fichier `.env` à la racine du projet, contenant les variables d'environnement suivantes :
```env
# Environment
ENVIRONMENT=

# Postgres
POSTGRES_DATABASE=CROUStillant
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Postgres API
PGRST_USER=
PGRST_PASSWORD=
PGRST_DB_SCHEMA=api

# Discord
WEBHOOK_URL=
THUMBNAIL_URL=
IMAGE_URL=
EMBED_COLOR=6A9F56
```

Pour lancer CROUStillant, exécutez la commande suivante :
```bash
docker-compose up
```

# 💻 • Utilisation

CROUStillant est un service de fond, il n'y a donc pas d'interface utilisateur. Pour accéder aux données stockées, vous pouvez utiliser l'API PostgREST qui est accessible à l'adresse `http://localhost:3000`.

# 🔍 • To Do

- [ ] Ajouter la vérification des données insérées dans la base de données. Il faut notamment vérifier que les plats insérés ne contiennent pas d'erreurs (ex: "Chou fkeur" au lieu de "Chou fleur")  
- [ ] Ajouter des tests.

# 📃 • Crédits

- [Paul Bayfield](https://github.com/PaulBayfield) - Fondateur du projet et développeur principal
- [Lucas Debeve](https://github.com/lucasDebeve) - Pro de la conception des bases de données, à l'origine de la base de données de CROUStillant

# 📝 • License

CROUStillant sous licence [Apache 2.0](LICENSE).

```
Copyright 2024 - 2025 CROUStillant Développement

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
