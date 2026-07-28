# Rapport d'implémentation — IndraQuant

*Généré le 2026-07-22, section infrastructure mise à jour le 2026-07-28 (migration Windows → Kali natif). Reflète l'état du code à ces dates — voir `docs/00-index.md` et `docs/07-decisions-architecture.md` pour la documentation vivante qui continuera d'évoluer.*

Plateforme personnelle d'aide à la décision pour les marchés financiers (crypto + actions), en français, avec des sorties IA toujours **probabilistes et explicables** — jamais de prédiction binaire ou de boîte noire. Toutes les phases de la feuille de route (`docs/06-feuille-de-route.md`) sont implémentées, plus un cycle d'extensions post-lancement.

---

## 1. Stack technique

| Couche | Choix | Note |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic | Port **8100**, conteneurisé (Docker Compose) |
| Base de données | PostgreSQL (stack Homelab partagé, `indralabs-network`) | Remplace MariaDB/XAMPP (ADR-033) |
| Cache | Redis (stack Homelab partagé, DB index 2) | Remplace Microsoft Garnet (ADR-034) |
| Frontend | Next.js 16 (Turbopack), TypeScript, Tailwind, Zustand, Framer Motion, lightweight-charts v5 | 100 % français (next-intl), reste natif (`npm run dev`) |
| Données de marché | `ccxt` (crypto, Binance) + `yfinance` (actions) | Architecture multi-actifs dès le départ (ADR-004) |
| IA | XGBoost + régression logistique + SHAP, Ollama local (qwen3.5:9b) | Deep Learning volontairement différé (ADR-017) |
| Environnement | Kali Linux natif, Docker Compose pour le backend | Rejoint `indralabs-network` (ADR-035) |

---

## 2. Pages frontend (10)

| Page | Route | Contenu |
|---|---|---|
| Connexion | `/login` | Authentification JWT, utilisateur unique |
| **Tableau de bord** | `/` | Graphique en chandeliers (ou ligne) temps réel par instrument/unité de temps, indicateurs MM 20/50, RSI 14, badge « marché fermé » (horaires NYSE réels), figures de chandeliers détectées, structures Smart Money (cassure de structure, prise de liquidité, Fair Value Gap, Order Block), panneau **Prédiction IA** (probabilité de direction, estimation de prix avec intervalle, attribution SHAP, auto-apprentissage affiché) |
| Backtesting | `/backtesting` | Formulaire de stratégie généré depuis le catalogue backend (4 stratégies), lancement de backtest, validation walk-forward, historique des backtests précédents |
| Paper trading | `/paper-trading` | Démarrage/arrêt de sessions d'exécution simulée en quasi temps réel, suivi equity/PnL/rendement/position/frais, métriques de risque (VaR 95 %, drawdown, volatilité), historique des ordres |
| **Portefeuille** | `/portfolio` | Vue agrégée réelle sur toutes les sessions de paper trading : capital total, PnL, rendement, répartition par instrument, liste des sessions |
| **Entraînement IA** | `/training` | Suivi réel du Prediction Engine : bilan par unité de temps, courbe de calibration, tendance de précision glissante, tableau paginé des prédictions récentes, sélection multi-actifs prioritaires, bouton démarrer/arrêter l'entraînement continu |
| Actualités | `/news` | Agrégation RSS (CoinDesk, Cointelegraph, Yahoo), analyse de sentiment par IA locale, calendrier économique (45 jours) |
| Alertes | `/alerts` | Création d'alertes prix/RSI, vérification automatique toutes les 30 s |
| Assistant IA | `/assistant` | Chat conversationnel avec contexte de marché (Ollama local) |
| Réglages | `/settings` | Langue, thème |

Éléments transverses : logo/thème dégradé bleu-violet-orange, fond animé « + », transitions de page (Framer Motion), pastille d'onglet actif, graphique avec mise à jour en direct par incréments (pas de rechargement complet).

---

## 3. Modules backend (20)

Architecture Clean/DDD stricte : chaque module a ses couches `domain` (logique pure) → `application` (cas d'usage, DTO) → `infrastructure` (implémentations concrètes) → `interface` (routeurs FastAPI). Aucun module n'importe le `domain` d'un autre module — seulement son `application/dto.py`.

| Module | Rôle | Endpoints / capacités clés |
|---|---|---|
| `auth` | Authentification JWT stateless | `POST /auth/login`, `GET /auth/me` |
| `settings` | Préférences utilisateur | `GET/PUT /settings` |
| `market_data` | Instruments, ingestion OHLCV, streaming, horaires de marché | `GET /instruments`, `GET /instruments/{id}/ohlcv`, `WS /ws/market-data`, `GET /instruments/{id}/market-status`, rafraîchissement proactif en tâche de fond (5 min) |
| `feature_engineering` | Primitives numériques partagées (moyenne/écart-type glissants, EMA) | Utilisé par `technical_analysis` et `machine_learning` |
| `technical_analysis` | Indicateurs techniques | `GET /instruments/{id}/indicators` (SMA, EMA, RSI, MACD, Bollinger) |
| `pattern_recognition` | Figures de chandeliers | `GET /instruments/{id}/patterns` (avalement, marteau, double sommet) |
| `smart_money` | Structures de marché « Smart Money Concepts » | `GET /instruments/{id}/smc` (cassure de structure, prise de liquidité, **Fair Value Gap**, **Order Block**) |
| `backtesting` | Simulation de stratégies sur historique | `POST /backtests`, `GET /backtests`, `POST /backtests/walk-forward` — **4 stratégies** : croisement de moyennes mobiles, retour à la moyenne RSI, **croisement MACD**, **cassure de Bollinger** |
| `strategy_builder` | Catalogue de stratégies pilotant le formulaire frontend | `GET /strategies` (paramètres, bornes, descriptions — le frontend ne code aucune stratégie en dur) |
| `paper_trading` | Exécution simulée en continu sur flux réel | `POST/GET /paper-trading/sessions`, `POST /paper-trading/sessions/{id}/stop` |
| `portfolio_analytics` | Analytique par session + vue agrégée | `GET /portfolio/summary` (capital total, PnL, répartition par instrument) |
| `risk_management` | Métriques de risque | VaR historique 95 %, drawdown max, volatilité annualisée |
| `machine_learning` | Modèles ML partagés | Ensemble XGBoost + régression logistique, SHAP (`TreeExplainer`), régresseur de prix XGBoost, fonctions de calibration pures |
| `prediction_engine` | Cœur IA : prédiction de direction + prix, auto-apprentissage | `GET /instruments/{id}/prediction`, `GET /predictions/dashboard`, `POST /training/start`/`stop`, `GET /training/sessions` |
| `economic_calendar` | Calendrier économique | `GET /calendar/events` (FOMC, CPI, NFP) |
| `news_intelligence` | Agrégation d'actualités | `GET /news` (flux RSS) |
| `sentiment_analysis` | Analyse de sentiment IA locale | `GET /news/sentiment` (Ollama, classification par titre) |
| `ai_assistant` | Assistant conversationnel | `POST /assistant/chat` (contexte marché, garde-fous) |
| `alert_center` | Alertes prix/RSI | `POST/GET/DELETE /alerts` |
| *(Plugin System)* | Extensions tierces découvertes automatiquement | `backend/plugins/<nom>/plugin.py`, montées sous `/api/v1/plugins/<nom>` |

---

## 4. Intelligence artificielle — détail

### Prédiction de direction
Ensemble XGBoost (classifieur) + régression logistique, entraînement à la volée sur l'historique récent, attribution SHAP (facteurs les plus influents affichés en clair), précision test comparée à une référence naïve (honnêteté du modèle affichée, jamais cachée).

### Estimation de prix
Régresseur XGBoost prédisant le rendement logarithmique de la prochaine bougie. L'intervalle bas/haut n'est **jamais** une hypothèse théorique : il est construit à partir des **quantiles empiriques des résidus réels** du modèle sur les données de test.

### Auto-apprentissage (deux volets)
- **Direction** : chaque prédiction est persistée, automatiquement vérifiée une fois la bougie cible close, et la confiance affichée est recalibrée par rapport au taux de réussite réellement observé dans des tranches de confiance de 5 %.
- **Prix** : même principe appliqué à l'intervalle de prix — il s'élargit ou se resserre selon que la couverture réelle observée est en dessous ou au-dessus de la confiance annoncée.

Les deux mécanismes ont été vérifiés de bout en bout avec de vraies données (prédiction réelle → résolution automatique après clôture de bougie → recalibration visible à l'appel suivant).

### Entraînement continu
Sélection multi-actifs explicite et mémorisée (pas de sémantique « tout ou rien »), bouton démarrer/arrêter par instrument/unité de temps, sessions ré-exécutant périodiquement le Prediction Engine en tâche de fond.

### Explicabilité (principe non négociable)
Chaque sortie IA du projet — direction, prix, sentiment, Smart Money Concepts — est accompagnée d'une explication en français et d'une mesure de confiance ou d'un intervalle. Le Deep Learning (LSTM/Transformers) est délibérément différé (ADR-017) tant qu'aucun besoin ne justifie sa complexité supplémentaire.

---

## 5. Infrastructure & tâches de fond

- **25 instruments actifs** : 13 cryptomonnaies (Binance, via `ccxt`) + 12 actions (Yahoo Finance).
- **Stack entièrement async** (SQLAlchemy `asyncpg` + `redis.asyncio`, ADR-036) : les 5 tâches de fond ci-dessous et toutes les routes FastAPI partagent la même boucle événementielle (`uvloop`), sans thread séparé ni connexion bloquante.
- **5 tâches de fond** (`asyncio.create_task`, démarrées/arrêtées dans le cycle de vie FastAPI) :
  1. `AlertRunner` — vérifie les alertes toutes les 30 s.
  2. `PaperTradingRunner` — fait avancer les sessions de paper trading sur flux réel.
  3. `PredictionResolverRunner` — résout les prédictions dont la bougie cible est close.
  4. `TrainingRunner` — ré-exécute le Prediction Engine pour les sessions d'entraînement continu actives.
  5. `MarketDataRefreshRunner` — rafraîchit proactivement les données 1h/1d toutes les 5 min pour les 25 instruments (respecte les horaires NYSE pour les actions).
- **1 migration Alembic** (`001_initial_schema`, PostgreSQL natif) — squash des 7 anciennes révisions MariaDB (ADR-033), aucune donnée de production à préserver (ADR-001/002).

---

## 6. Journal des décisions d'architecture (ADR)

37 décisions documentées dans `docs/07-decisions-architecture.md`. Résumé chronologique :

| Plage | Thème |
|---|---|
| ADR-001 à 009 | Fondations : utilisateur unique, déploiement local, données multi-actifs, français dès le départ, JWT, structure par module, `/api/v1` |
| ADR-010 à 014 | *(Historique, remplacées le 2026-07-28 — voir ADR-033/034/036)* Réalité d'environnement Windows Phase 0-1 : MariaDB/XAMPP, Garnet, bootstrap, ingestion lecture-au-travers |
| ADR-015 à 019 | Phases 2-6 : timeframes secondes, WebSocket, Prediction Engine initial, sources Phase 5, assistant/alertes/plugins |
| ADR-020 à 023 | Auto-apprentissage direction, animations, calendrier de marché NYSE, page Entraînement IA |
| ADR-024 à 027 | Entraînement continu multi-actifs, estimation de prix, reproductibilité, parallélisation |
| ADR-028 à 032 | **Sweep « implémente tout » (2026-07-22)** : Portfolio Analytics, auto-apprentissage du prix, rafraîchissement proactif, extension SMC (FVG/Order Block), extension Strategy Builder (MACD/Bollinger) |
| ADR-033 à 037 | **Migration Windows → Kali natif (2026-07-28)** : PostgreSQL Homelab remplace MariaDB, Redis Homelab remplace Garnet, backend conteneurisé sur `indralabs-network`, stack async SQLAlchemy/Redis, nettoyage Windows/PowerShell — détail ci-dessous |

### Détail des nouvelles décisions (2026-07-28)

- **ADR-033 — PostgreSQL natif du Homelab remplace MariaDB/XAMPP.** Base dédiée `indraquant` sur le Postgres partagé (`~/Homelab`), driver `psycopg` (sync, migrations) + `asyncpg` (async, application). Les 7 migrations MariaDB ont été squashées en une seule migration Postgres-native (`001_initial_schema`) générée par autogénération contre les modèles SQLAlchemy existants plutôt que portées à la main — aucune donnée de production à préserver (ADR-001/002). Un upsert codé en dur avec la syntaxe MySQL (`ON DUPLICATE KEY UPDATE`, dans `market_data` et `settings`) a aussi été trouvé et corrigé vers `ON CONFLICT` natif Postgres à cette occasion — il n'était détecté par aucune migration ni aucun test (doublons de test en mémoire).
- **ADR-034 — Redis réel du Homelab remplace Microsoft Garnet.** Instance partagée, index logique **2** dédié à IndraQuant (l'index 1 est réservé par le projet A.R.S.E.N.I.C — voir `~/Homelab/README.md`).
- **ADR-035 — Backend conteneurisé sur `indralabs-network`.** `docker-compose.yml` à la racine du projet (patron repris d'A.R.S.E.N.I.C) : le backend rejoint le réseau Docker externe du Homelab, résout Postgres/Redis par nom de service, publie le port 8100 sur `127.0.0.1` uniquement. Le frontend reste natif (`npm run dev`). Ollama, non conteneurisé (accès GPU), est atteint via `host.docker.internal` — nécessite qu'Ollama écoute sur `0.0.0.0` et non uniquement `127.0.0.1` (configuration système, hors du dépôt).
- **ADR-036 — Stack backend entièrement asynchrone.** SQLAlchemy passe de `create_engine`/`Session` à `create_async_engine`/`AsyncSession` (`asyncpg`), `redis.Redis` à `redis.asyncio.Redis`. Conversion réalisée en un seul changement atomique (composition_root, 8 repositories, ~24 cas d'usage, ~55 routes, 5 tâches de fond) et non module par module comme envisagé initialement : `GetOhlcvUseCase` (module `market_data`) est appelé directement par la quasi-totalité des autres modules, rendant toute conversion partielle instable. Les 5 tâches de fond utilisent désormais `asyncio.create_task` directement (suppression de `run_coroutine_threadsafe`/`attach_loop`, devenus inutiles puisque tous les appelants tournent déjà sur la boucle événementielle).
- **ADR-037 — Port 8100 conservé, mais pour une raison différente.** Le port 8000 reste indisponible sous Kali — non plus à cause d'un service Windows, mais parce que l'agent Portainer Edge du Homelab (`PORTAINER_EDGE_PORT=8000`) l'occupe déjà.

---

## 7. Ce qui n'est pas fait (volontairement)

- **Deep Learning (LSTM/Transformers)** : différé tant qu'aucun besoin ne justifie une architecture séquentielle plus complexe que l'ensemble XGBoost actuel (ADR-017).
- Pas de multi-tenant, pas de mode hébergé — le projet reste local-first, mono-utilisateur (ADR-001, ADR-002).

---

## 8. Vérification

Chaque fonctionnalité listée ci-dessus a été vérifiée avec de vraies données (appels API réels via curl avec authentification, et interaction réelle dans le navigateur), pas seulement par des tests unitaires. Suite de tests backend : **266 tests unitaires**, tous passants.

La migration Windows → Kali (§1, ADR-033 à 037) a été vérifiée de bout en bout contre l'infrastructure réelle : conteneur Docker démarré, migration Postgres appliquée, connexion Redis (index 2) confirmée, puis appels API réels (connexion, liste d'instruments, ingestion OHLCV crypto **et actions**, création/liste de backtests, création/arrêt de session de paper trading) via le stack async — health check `{"status":"ok","database":"ok","cache":"ok"}`.

### Performances (Kali natif)

- **uvloop** activé sur le déploiement Docker (`--loop uvloop`) — boucle asyncio plus rapide, sans changement de comportement.
- **Un seul worker uvicorn**, délibérément : les 5 tâches de fond et le cache d'instruments en mémoire (`SqlAlchemyInstrumentRepository`) sont process-local — plusieurs workers dupliqueraient les tâches de fond et fragmenteraient ce cache.
- **Cache Redis des indicateurs techniques** : évalué, **non ajouté** — `ComputeIndicatorsUseCase` n'est appelé par aucune tâche de fond (seulement à la demande depuis le tableau de bord), et le calcul reste bon marché (< 5000 bougies, opérations vectorielles simples). Le cache existant (lecture-au-travers OHLCV, feature store, prédictions) couvre déjà les chemins réellement coûteux.
- **TimescaleDB** : évalué, **non activé** — `ohlcv_candles` totalise 11 538 lignes (2,4 Mo) au moment de l'évaluation ; projeté sur plusieurs années à 25 instruments, le volume resterait largement dans les capacités d'un Postgres nu avec l'index unique déjà en place. Voie d'activation documentée pour référence future si le volume réel le justifiait un jour : `CREATE EXTENSION timescaledb` sur le Postgres du Homelab, puis `create_hypertable('ohlcv_candles', 'open_time')` — sans complexifier le projet tant que le besoin n'est pas prouvé (ADR-001/002).
