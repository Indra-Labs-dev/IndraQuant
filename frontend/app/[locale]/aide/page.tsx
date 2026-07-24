"use client";

import { useEffect, useState } from "react";

import { AppNav } from "@/components/layout/AppNav";
import { useRouter } from "@/lib/i18n/navigation";
import { useAuthHydrated, useAuthStore } from "@/lib/stores/auth";

const TOC = [
  { id: "bienvenue", label: "Bienvenue" },
  { id: "architecture", label: "Comment IndraQuant décide" },
  { id: "dashboard", label: "Le tableau de bord" },
  { id: "meta-decision", label: "Meta Decision Engine & régime" },
  { id: "correlations", label: "Corrélations" },
  { id: "backtesting", label: "Backtesting & validation" },
  { id: "paper-trading", label: "Paper trading & portefeuille" },
  { id: "entrainement", label: "Entraînement & dérive" },
  { id: "news", label: "Actualités & sentiment" },
  { id: "alertes", label: "Alertes" },
  { id: "assistant", label: "Assistant IA" },
  { id: "glossaire", label: "Glossaire des indicateurs" },
  { id: "avertissements", label: "Bon à savoir" },
] as const;

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="space-y-4 text-sm leading-relaxed text-[var(--muted)]">
        {children}
      </div>
    </section>
  );
}

function Callout({
  tone,
  title,
  children,
}: {
  tone: "info" | "warning" | "success";
  title: string;
  children: React.ReactNode;
}) {
  const styles = {
    info: "border-[var(--accent-cyan)]/30 bg-[var(--accent-cyan)]/5",
    warning: "border-[var(--accent-orange)]/30 bg-[var(--accent-orange)]/5",
    success: "border-[var(--up)]/30 bg-[var(--up)]/5",
  } as const;
  return (
    <div className={`rounded-xl border p-4 ${styles[tone]}`}>
      <p className="mb-1 text-sm font-medium text-[var(--foreground)]">{title}</p>
      <div className="text-sm text-[var(--muted)]">{children}</div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <p className="mb-2 text-sm font-medium text-[var(--foreground)]">{title}</p>
      <div className="text-sm text-[var(--muted)]">{children}</div>
    </div>
  );
}

/** Flux global : marché → données → moteurs spécialisés → fusion → interface. */
function ArchitectureDiagram() {
  const box = (x: number, y: number, w: number, h: number, label: string[], color: string) => (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={10}
        fill="rgba(255,255,255,0.03)"
        stroke={color}
        strokeWidth={1.5}
      />
      {label.map((line, i) => (
        <text
          key={i}
          x={x + w / 2}
          y={y + h / 2 - (label.length - 1) * 7 + i * 14}
          textAnchor="middle"
          fontSize="11"
          fill="var(--foreground)"
        >
          {line}
        </text>
      ))}
    </g>
  );
  const arrow = (x1: number, y1: number, x2: number, y2: number) => (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--muted)" strokeWidth={1.5} />
      <polygon
        points={`${x2},${y2} ${x2 - 6},${y2 - 4} ${x2 - 6},${y2 + 4}`}
        fill="var(--muted)"
      />
    </g>
  );

  return (
    <svg viewBox="0 0 900 220" className="w-full" role="img" aria-label="Flux de décision d'IndraQuant">
      {box(10, 90, 130, 60, ["Marchés", "(Binance, Yahoo)"], "var(--accent-cyan)")}
      {arrow(140, 120, 175, 120)}
      {box(180, 90, 140, 60, ["Market Data Engine", "+ Feature Store"], "var(--accent-cyan)")}
      {arrow(320, 120, 355, 120)}
      {box(360, 20, 160, 50, ["Analyse technique", "+ indicateurs avancés"], "var(--accent-violet)")}
      {box(360, 85, 160, 50, ["Modèle ML", "(XGBoost + régression)"], "var(--accent-violet)")}
      {box(360, 150, 160, 50, ["Smart Money, régime,", "actualités, corrélations"], "var(--accent-violet)")}
      {arrow(520, 45, 555, 100)}
      {arrow(520, 110, 555, 110)}
      {arrow(520, 175, 555, 120)}
      {box(560, 85, 160, 60, ["Meta Decision Engine", "(fusion pondérée)"], "var(--accent-orange)")}
      {arrow(720, 115, 755, 115)}
      {box(760, 60, 130, 130, ["Tableau de bord,", "alertes, paper", "trading, portefeuille"], "var(--up)")}
    </svg>
  );
}

/** Les 7 moteurs spécialisés qui convergent vers la décision fusionnée. */
function MetaDecisionDiagram() {
  const engines = [
    "Tendance",
    "Retour à la moyenne",
    "Volatilité",
    "Liquidité (SMC)",
    "Modèle ML",
    "Actualités",
    "Macroéconomie",
  ];
  const cx = 300;
  const cy = 150;
  const radius = 130;
  return (
    <svg viewBox="0 0 600 320" className="w-full" role="img" aria-label="Fusion des moteurs du Meta Decision Engine">
      {engines.map((name, i) => {
        const angle = (i / engines.length) * 2 * Math.PI - Math.PI / 2;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);
        return (
          <g key={name}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--muted)" strokeWidth={1} opacity={0.5} />
            <rect
              x={x - 55}
              y={y - 16}
              width={110}
              height={32}
              rx={8}
              fill="rgba(255,255,255,0.03)"
              stroke="var(--accent-violet)"
              strokeWidth={1.2}
            />
            <text x={x} y={y + 4} textAnchor="middle" fontSize="10.5" fill="var(--foreground)">
              {name}
            </text>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r={62} fill="rgba(245,158,11,0.08)" stroke="var(--accent-orange)" strokeWidth={2} />
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="12" fontWeight={600} fill="var(--foreground)">
        Décision
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" fontSize="12" fontWeight={600} fill="var(--foreground)">
        fusionnée
      </text>
      <text x={cx} y={cy + 24} textAnchor="middle" fontSize="9" fill="var(--muted)">
        pondérée par le régime
      </text>
    </svg>
  );
}

/** Boucle d'auto-apprentissage du Prediction Engine. */
function LearningLoopDiagram() {
  const steps = [
    { x: 150, y: 40, label: ["Prédiction", "émise"] },
    { x: 400, y: 40, label: ["Bougie réelle", "se ferme"] },
    { x: 400, y: 190, label: ["Comparaison", "prédit vs réel"] },
    { x: 150, y: 190, label: ["Confiance", "recalibrée"] },
  ];
  return (
    <svg viewBox="0 0 550 240" className="w-full" role="img" aria-label="Boucle d'auto-apprentissage">
      {steps.map((s, i) => {
        const next = steps[(i + 1) % steps.length];
        return (
          <line
            key={i}
            x1={s.x}
            y1={s.y}
            x2={next.x}
            y2={next.y}
            stroke="var(--muted)"
            strokeWidth={1.5}
            markerEnd="url(#arrow)"
          />
        );
      })}
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--muted)" />
        </marker>
      </defs>
      {steps.map((s, i) => (
        <g key={i}>
          <rect
            x={s.x - 65}
            y={s.y - 22}
            width={130}
            height={44}
            rx={10}
            fill="rgba(255,255,255,0.03)"
            stroke="var(--accent-cyan)"
            strokeWidth={1.4}
          />
          {s.label.map((line, j) => (
            <text
              key={j}
              x={s.x}
              y={s.y - 22 + 22 + (j - (s.label.length - 1) / 2) * 14}
              textAnchor="middle"
              fontSize="11"
              fill="var(--foreground)"
            >
              {line}
            </text>
          ))}
        </g>
      ))}
    </svg>
  );
}

export default function AidePage() {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthHydrated();
  const [activeTab, setActiveTab] = useState<string>(TOC[0].id);

  useEffect(() => {
    if (hydrated && !token) router.push("/login");
  }, [hydrated, token, router]);

  if (!hydrated || !token) return null;

  return (
    <div className="min-h-screen">
      <AppNav />
      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-8 lg:grid-cols-[220px_1fr]">
        <aside className="hidden lg:block">
          <nav className="sticky top-8 space-y-1 text-sm">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Sommaire
            </p>
            {TOC.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                onClick={() => setActiveTab(item.id)}
                className={`block rounded-md px-2 py-1.5 transition-colors ${
                  activeTab === item.id
                    ? "bg-white/10 text-[var(--foreground)]"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="space-y-12">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">
              <span className="brand-gradient-text">Guide complet</span> d&apos;IndraQuant
            </h1>
            <p className="text-sm text-[var(--muted)]">
              Ce qu&apos;IndraQuant fait, comment le lire, et comment s&apos;en servir sans
              se faire piéger par ses propres biais.
            </p>
          </div>

          {/* Mobile TOC */}
          <div className="flex flex-wrap gap-2 lg:hidden">
            {TOC.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--muted)]"
              >
                {item.label}
              </a>
            ))}
          </div>

          <Section id="bienvenue" title="Bienvenue">
            <p>
              IndraQuant est une plateforme personnelle d&apos;aide à la décision pour les
              marchés financiers (crypto et actions). Elle ne prédit rien avec certitude :
              chaque sortie est une <strong className="text-[var(--foreground)]">estimation
              probabiliste</strong>, accompagnée d&apos;une explication concrète de ce qui l&apos;a
              produite.
            </p>
            <Callout tone="info" title="Trois principes non négociables">
              <ul className="list-inside list-disc space-y-1">
                <li>
                  <strong className="text-[var(--foreground)]">Probabiliste</strong> — jamais
                  &laquo; ça va monter &raquo;, toujours &laquo; X % de chances, sur cette
                  base&nbsp;&raquo;.
                </li>
                <li>
                  <strong className="text-[var(--foreground)]">Explicable</strong> — chaque
                  moteur, chaque indicateur qui a pesé dans une décision est affiché, jamais
                  caché dans une boîte noire.
                </li>
                <li>
                  <strong className="text-[var(--foreground)]">Auto-critique</strong> — le
                  système compare ses prédictions passées à ce qui s&apos;est réellement
                  passé, et ajuste sa confiance en conséquence.
                </li>
              </ul>
            </Callout>
            <p>
              IndraQuant n&apos;est pas un conseiller financier et ne exécute aucun ordre réel
              — le Paper Trading simule des transactions sans argent réel, précisément pour
              apprendre et tester sans risque.
            </p>
          </Section>

          <Section id="architecture" title="Comment IndraQuant décide">
            <p>
              Les données de marché traversent plusieurs étages avant d&apos;arriver à une
              décision. Chaque étage est indépendant et son résultat est visible — rien n&apos;est
              résumé en un seul chiffre sans détail.
            </p>
            <Card title="Vue d'ensemble">
              <ArchitectureDiagram />
            </Card>
            <ol className="list-inside list-decimal space-y-2">
              <li>
                <strong className="text-[var(--foreground)]">Ingestion</strong> — les bougies
                (open/high/low/close/volume) sont récupérées depuis Binance (crypto) ou Yahoo
                Finance (actions) et stockées.
              </li>
              <li>
                <strong className="text-[var(--foreground)]">Feature Store</strong> — les
                indicateurs techniques (moyennes, RSI, MACD, volatilité...) sont calculés une
                seule fois par bougie et partagés entre les moteurs, pour éviter les
                recalculs et garder les résultats cohérents.
              </li>
              <li>
                <strong className="text-[var(--foreground)]">Moteurs spécialisés</strong> —
                modèle ML (XGBoost + régression logistique), structures Smart Money, régime de
                marché, sentiment des actualités, corrélations entre actifs.
              </li>
              <li>
                <strong className="text-[var(--foreground)]">Fusion</strong> — le Meta
                Decision Engine combine tous ces avis en une seule décision, en expliquant le
                poids de chacun.
              </li>
            </ol>
          </Section>

          <Section id="dashboard" title="Le tableau de bord">
            <p>
              La page d&apos;accueil affiche le graphique en chandeliers de l&apos;instrument
              sélectionné, en temps quasi réel (WebSocket), avec les moyennes mobiles 20/50
              superposées.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Card title="Prédiction IA">
                Cliquez sur « Analyser » pour entraîner le modèle sur l&apos;historique récent
                et obtenir une probabilité de hausse/baisse, une estimation de prix (avec
                intervalle, jamais une valeur unique) et les facteurs SHAP qui ont le plus
                pesé.
              </Card>
              <Card title="Meta Decision Engine">
                Détail moteur par moteur (tendance, retour à la moyenne, volatilité,
                liquidité, ML, actualités, macro) avec un badge de régime de marché à côté du
                titre — voir la section suivante.
              </Card>
              <Card title="Figures détectées">
                Figures chartistes classiques (avalement, marteau, double sommet...) avec un
                niveau de confiance et une explication en français.
              </Card>
              <Card title="Structures de marché (SMC)">
                Cassures de structure, prises de liquidité, Fair Value Gaps et Order Blocks —
                le vocabulaire du <em>Smart Money Concepts</em>, expliqué à chaque
                détection.
              </Card>
            </div>
          </Section>

          <Section id="meta-decision" title="Meta Decision Engine & régime de marché">
            <p>
              Plutôt qu&apos;un seul modèle, IndraQuant interroge sept avis indépendants et les
              combine — sans masquer leur désaccord éventuel.
            </p>
            <Card title="Les sept moteurs">
              <MetaDecisionDiagram />
            </Card>
            <p>
              La confiance affichée n&apos;est <strong className="text-[var(--foreground)]">pas
              une moyenne</strong> : elle est réduite quand les moteurs se contredisent. Un
              score élevé mais peu fiable (moteurs divergents) affiche donc une confiance
              basse — c&apos;est volontaire.
            </p>
            <Callout tone="info" title="Le régime de marché ajuste les poids">
              Le <strong className="text-[var(--foreground)]">Market Regime Detector</strong>{" "}
              classe le marché en tendance haussière/baissière, range, ou panique (via le
              ratio d&apos;efficacité de Kaufman et un z-score de volatilité). En régime de
              tendance, le moteur « Tendance » pèse plus lourd ; en range, c&apos;est « Retour à
              la moyenne » ; en panique, le modèle ML est délibérément dévalué (les données
              historiques ne décrivent plus la situation actuelle) et la confiance finale est
              encore réduite.
            </Callout>
          </Section>

          <Section id="correlations" title="Corrélations entre actifs">
            <p>
              Sur la page <strong className="text-[var(--foreground)]">Corrélations</strong>,
              sélectionnez au moins deux instruments pour voir à quel point leurs rendements
              évoluent ensemble.
            </p>
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-[var(--muted)]">
                <tr>
                  <th className="py-1 pr-4">Mesure</th>
                  <th className="py-1">Ce qu&apos;elle capture</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <tr>
                  <td className="py-2 pr-4 font-medium text-[var(--foreground)]">Pearson</td>
                  <td className="py-2">Relation linéaire entre les rendements.</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-medium text-[var(--foreground)]">Spearman</td>
                  <td className="py-2">
                    Relation monotone, plus robuste aux valeurs extrêmes.
                  </td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-medium text-[var(--foreground)]">Glissante</td>
                  <td className="py-2">Corrélation calculée sur la fenêtre récente uniquement.</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-medium text-[var(--foreground)]">
                    Dynamique (EWMA)
                  </td>
                  <td className="py-2">
                    S&apos;adapte en continu, plus de poids aux données récentes.
                  </td>
                </tr>
              </tbody>
            </table>
            <p>
              Une corrélation forte et stable entre deux actifs signifie que les détenir
              tous les deux n&apos;apporte pas vraiment de diversification.
            </p>
          </Section>

          <Section id="backtesting" title="Backtesting & validation scientifique">
            <p>
              La page <strong className="text-[var(--foreground)]">Backtesting</strong>{" "}
              rejoue une stratégie (croisement de moyennes, RSI, MACD, Bollinger) sur
              l&apos;historique. Le bouton{" "}
              <strong className="text-[var(--foreground)]">Walk-forward</strong> optimise les
              paramètres sur une fenêtre puis les teste sur la fenêtre suivante, jamais vue —
              un garde-fou de base contre le surapprentissage.
            </p>
            <Callout tone="warning" title="Un bon backtest peut quand même être un mirage">
              Le bouton <strong className="text-[var(--foreground)]">Validation</strong>{" "}
              pousse plus loin : un intervalle de confiance bootstrap sur le rendement, un test
              de permutation Monte Carlo (le timing de la stratégie bat-il un positionnement
              aléatoire sur le même marché ?), et un Reality Check de White qui vérifie si le
              résultat résiste à la correction pour tests multiples — essayer 5 variantes
              d&apos;une stratégie et garder la meilleure gonfle artificiellement la
              performance apparente si on ne s&apos;en corrige pas.
            </Callout>
            <p>
              L&apos;optimisation des hyperparamètres (Grid Search, Random Search, recherche
              bayésienne via Optuna ou Hyperopt) explore automatiquement l&apos;espace des
              paramètres d&apos;une stratégie ou du modèle ML, et est disponible via l&apos;API
              d&apos;optimisation.
            </p>
          </Section>

          <Section id="paper-trading" title="Paper trading & portefeuille">
            <p>
              Le <strong className="text-[var(--foreground)]">Paper Trading</strong> exécute
              une stratégie en conditions quasi réelles, sans argent réel : chaque session
              suit son propre capital, ses frais (0,1 % par ordre) et son historique de
              trades avec la raison de chaque décision.
            </p>
            <p>
              La page <strong className="text-[var(--foreground)]">Portefeuille</strong>{" "}
              agrège toutes les sessions et ajoute un contrôle de risque :
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Card title="Contrôle d'exposition">
                Alerte si une position dépasse une part maximale du portefeuille, ou si
                l&apos;exposition totale dépasse 100 % (effet de levier implicite).
              </Card>
              <Card title="Budget de risque">
                Compare le poids actuel de chaque position à un poids cible calculé par
                parité de risque (inversement proportionnel à sa volatilité) — une position
                très volatile mais peu pondérée en capital peut quand même dominer le risque
                réel du portefeuille.
              </Card>
            </div>
            <p>
              Sur chaque session, un profil de risque avancé est disponible : VaR, Expected
              Shortfall (perte moyenne au-delà de la VaR), critère de Kelly (fraction de
              capital à risquer par position), risque de ruine simulé par Monte Carlo, et
              dimensionnement de position à risque fixe.
            </p>
          </Section>

          <Section id="entrainement" title="Entraînement continu, auto-apprentissage & dérive">
            <p>
              La page <strong className="text-[var(--foreground)]">Entraînement IA</strong>{" "}
              permet d&apos;activer un entraînement continu sur les actifs de votre choix : le
              modèle se ré-entraîne régulièrement et chaque prédiction est enregistrée, puis
              vérifiée dès que la bougie visée se ferme.
            </p>
            <Card title="La boucle d'auto-apprentissage">
              <LearningLoopDiagram />
            </Card>
            <p>
              La confiance affichée n&apos;est jamais seulement celle du modèle : elle est
              mélangée avec le taux de réussite réellement observé sur des prédictions
              passées de confiance comparable. Plus l&apos;historique vérifié est grand, plus
              la confiance affichée s&apos;éloigne de l&apos;estimation brute pour refléter ce
              qui s&apos;est vraiment produit.
            </p>
            <Callout tone="info" title="Détection de dérive">
              Un bouton « Vérifier la dérive » compare la première et la seconde moitié de
              l&apos;historique récent sur trois plans :{" "}
              <strong className="text-[var(--foreground)]">dérive de données</strong> (les
              features ont-elles changé de distribution — indice PSI),{" "}
              <strong className="text-[var(--foreground)]">dérive de label</strong> (le
              marché monte-t-il/descend-il plus souvent qu&apos;avant), et{" "}
              <strong className="text-[var(--foreground)]">dérive de concept</strong> (la
              précision réellement vérifiée du modèle se dégrade-t-elle). Une dérive
              significative est un signal pour surveiller le modèle de plus près.
            </Callout>
          </Section>

          <Section id="news" title="Actualités & sentiment">
            <p>
              La page <strong className="text-[var(--foreground)]">Actualités</strong> agrège
              des flux RSS financiers gratuits et propose une analyse de sentiment par un
              modèle de langage local (Ollama) — jamais envoyée à un service tiers. Le
              calendrier économique liste les événements macro à venir (FOMC, CPI, NFP).
            </p>
          </Section>

          <Section id="alertes" title="Alertes">
            <p>
              Définissez un seuil de prix ou de RSI sur un instrument ; une tâche de fond
              vérifie les alertes actives toutes les 30 secondes. Une alerte est à usage
              unique : une fois déclenchée, elle se désactive avec un message explicatif.
            </p>
          </Section>

          <Section id="assistant" title="Assistant IA">
            <p>
              L&apos;assistant conversationnel (modèle local Ollama) reçoit à chaque message un
              instantané des instruments suivis. Il ne donne jamais de certitude sur les
              prix futurs ni de conseil d&apos;investissement, et ne conserve pas
              d&apos;historique côté serveur.
            </p>
          </Section>

          <Section id="glossaire" title="Glossaire des indicateurs techniques">
            <p>
              Disponibles via l&apos;endpoint <code className="text-[var(--foreground)]">/indicators</code> et
              utilisés en interne par les moteurs de décision.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-[var(--muted)]">
                  <tr>
                    <th className="py-1 pr-4">Indicateur</th>
                    <th className="py-1">Ce qu&apos;il mesure</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    ["SMA / EMA", "Moyenne mobile simple / exponentielle du prix."],
                    ["RSI", "Force relative — survente / surachat (0-100)."],
                    ["MACD", "Écart entre deux moyennes exponentielles, avec ligne de signal."],
                    ["Bollinger", "Bandes à ± n écarts-types autour d'une moyenne mobile."],
                    ["VWAP", "Prix moyen pondéré par le volume sur une fenêtre glissante."],
                    ["ATR", "Amplitude moyenne réelle — mesure de volatilité en unités de prix."],
                    ["ADX", "Force de la tendance (peu importe la direction)."],
                    ["Donchian", "Canal formé par le plus haut / plus bas sur la période."],
                    ["Keltner", "Canal autour d'une EMA, largeur basée sur l'ATR."],
                    ["OBV", "Volume cumulé, ajouté ou retranché selon le sens du prix."],
                    ["MFI", "RSI pondéré par le volume."],
                    ["CCI", "Écart du prix typique à sa moyenne, normalisé."],
                    ["Williams %R", "Position du prix dans son range récent (survente/surachat)."],
                    ["Chaikin Money Flow", "Pression acheteuse/vendeuse pondérée par le volume."],
                    ["Ulcer Index", "Profondeur et durée des creux de prix (pas juste l'amplitude)."],
                    ["Momentum", "Variation de prix sur une période donnée."],
                    ["Order Flow Proxy", "Pression acheteuse/vendeuse estimée depuis la position de clôture dans la bougie."],
                    ["Volatility Clustering", "Auto-corrélation de la volatilité — les grands mouvements suivent-ils de grands mouvements ?"],
                    ["Volume Profile", "Répartition du volume par niveau de prix, avec le point de contrôle (prix le plus échangé)."],
                  ].map(([name, desc]) => (
                    <tr key={name}>
                      <td className="py-2 pr-4 font-medium text-[var(--foreground)]">{name}</td>
                      <td className="py-2">{desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section id="avertissements" title="Bon à savoir">
            <Callout tone="warning" title="Ce qu'IndraQuant n'est pas">
              <ul className="list-inside list-disc space-y-1">
                <li>Pas un conseiller financier agréé — aucune sortie n&apos;est un conseil d&apos;investissement.</li>
                <li>Pas une garantie — toutes les statistiques (précision, VaR, corrélations...) décrivent le passé.</li>
                <li>
                  Pas un système d&apos;exécution réel — le Paper Trading simule des ordres
                  sans jamais toucher à de l&apos;argent réel.
                </li>
              </ul>
            </Callout>
            <Callout tone="success" title="Ce qu'il faut retenir">
              Chaque chiffre affiché est accompagné de son explication et, quand c&apos;est
              pertinent, de son historique de fiabilité réel. En cas de doute sur un résultat,
              cherchez d&apos;abord l&apos;explication associée avant de le prendre pour argent
              comptant.
            </Callout>
          </Section>
        </div>
      </main>
    </div>
  );
}
