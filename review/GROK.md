# Revue adverse — Grok (relecteur indépendant)

**Dépôt :** `~/hlm-review-grok` · branche `review/grok` · commit de base `25e0bac`  
**Date de revue :** 2026-07-27  
**Python :** `.venv/bin/python` (3.11.5)  
**Méthode :** recalculs indépendants depuis `experiments/data/` (aucun script auteur relancé pour les chiffres porteurs) ; recherche ouverte pour les affirmations de nouveauté ; lecture croisée papier / FINDINGS / README.

**Règle de lecture.** Un *constat* cite fichier, chiffre, commande et sortie. Sans preuve → *doute*. Gravité : **invalide un résultat** / **affaiblit une formulation** / **cosmétique**.

---

## Verdict en une page

Les **chiffres de comptage** (5,72×, top 1 % fills 23,1 %, notional 67,3 %, tranching 72 / 132, corrélation log-log 0,545, fusion 5,76×, quantiles de fills de compression) **tiennent** sur les CSV versionnés, au troisième chiffre près quand l’arrondi le permet.

Trois problèmes sérieux avant dépôt public sous nom réel :

1. **Fusion de deux maxima distincts** : le papier dit que le plus gros épisode fait **194 115 094 $ en 4 776 fills**. Les données disent **194 M$ en 2 568 fills** (BTC) et **4 776 fills pour 32,4 M$** (ZEC). Ce n’est pas un arrondi.
2. **Section Implications encore aux chiffres 12 h** (3,4× / 10,9×) alors que le corps du papier a basculé en année (4,58× / 10,02×).
3. **Affirmation de rareté « seul enregistrement public complet *et* attribué »** trop large telle qu’écrite dans l’abstract : plusieurs venues on-chain publient des liquidations complètes et nommées ; la formulation de l’introduction (« aucun CEX ») est plus défendable. La revue de littérature n’a pas fermé ce flanc.

Le papier **n’est pas prêt à être déposé tel quel**. Les mesures de base sont solides ; les formulations de priorité et deux erreurs factuelles le rendent fragile en public.

---

## Partie 1 — Recalcul des chiffres porteurs

**Sources utilisées uniquement :**

- `experiments/data/exp017_episodes.csv` — 351 540 lignes, colonnes `ts,coin,hip3,user,fills,notional`
- `experiments/data/exp024_fill_notionals.csv.gz` — 2 010 314 lignes, colonnes `hip3,notional`

### 1.1 Inflation du comptage — **5,72×** — tient

```text
$ .venv/bin/python -c "
import pandas as pd
ep=pd.read_csv('experiments/data/exp017_episodes.csv')
print(len(ep), int(ep.fills.sum()), ep.fills.sum()/len(ep))
"
# sortie:
# 351540 2010042 5.717818740399386
```

| | annoncé | recalcul | écart |
|---|---:|---:|---:|
| épisodes | 351 540 | 351 540 | 0 |
| fills (somme colonne) | 2 010 042 | 2 010 042 | 0 |
| facteur | 5,72 | 5,7178… → **5,72** à 2 décimales | aucun au niveau affiché |
| comptes uniques | 151 730 | 151 730 | 0 |
| instruments | 380 | 380 | 0 |
| notionnel total | 15,53 bn $ | 15,530 486 298,36 $ | cohérent |

**Gravité :** rien. Le facteur exact est 5,7178 ; l’affichage 5,72 est correct.

**Note de cohérence des deux collectes.** Le fichier fills EXP-024 a 2 010 314 lignes (+0,014 %). Majors fills : 1 672 034 (épisodes) vs 1 672 302 (fills) ; HIP-3 : 338 008 vs 338 012. Documenté dans EXP-024 / Limitations. N’invalide pas 5,72× (qui repose sur EXP-017).

### 1.2 Tranchage top 1 % — médiane **72**, moyenne **132** — tient

```text
n_top = ceil(0.01 * 351540) = 3516
top = ep.nlargest(3516, 'notional')
# median fills = 72.0
# mean fills   = 132.271331…
# max fills    = 4776
```

Table taille (§4) reproduite au centième près sur les moyennes annoncées (2,19 / 3,94 / 19,11 / 132,27).

### 1.3 Part des fills, top 1 % — **23,1 %** — tient

```text
100 * top.fills.sum() / 2010042 = 23.137128… %  → 23,1 %
```

### 1.4 Part du notionnel, top 1 % — **67,3 %** — tient

```text
100 * top.notional.sum() / ep.notional.sum() = 67.291505… %  → 67,3 %
top 5 %  → 85,593 % (annoncé 85,6 %)
top 10 % → 92,570 % (annoncé 92,6 %)
```

### 1.5 corr(ln notionnel, ln fills) — **+0,545** — tient (mais libellé trompeur)

```text
Pearson(log notional, log fills) = 0.545438…
Spearman(notional, fills)        = 0.467925…
```

Le papier écrit : *« The rank correlation between log notional and log fills per episode is +0.545 »*.

- Le **nombre** 0,545 est le **Pearson des logs**, pas une corrélation de rang.
- Une corrélation de rang (Spearman) vaut **0,468**.

**Constat — affaiblit une formulation.** Le chiffre est vrai pour Pearson(log, log) ; l’étiquette « rank correlation » est fausse. Remplacer par « Pearson correlation of log notional and log fills » (ou publier 0,468 si l’on veut vraiment du rang).

### 1.6 Plus gros épisode — **194 115 094 $ en 4 776 fills** — **FAUX**

```text
max notional:
  coin=BTC  fills=2568  notional=194115093.5355

max fills:
  coin=ZEC  fills=4776  notional=32447999.0564
```

Aucun épisode ne combine 194 M$ et 4 776 fills. Ce sont **deux maxima distincts** collés en une phrase dans :

- abstract / § compression / FINDINGS / README racine  
  (« Largest episode **$194,115,094**, spread across **4,776 fills** »)

**Constat — invalide ce sous-résultat (formulation).**  
Correction minimale : *« plus gros notionnel 194 115 094 $ (2 568 fills, BTC) ; plus grand nombre de fills 4 776 (32,4 M$, ZEC) »*.

Max fill unique 10 990 000 $ : **reproduit** (`fl.notional.max()`).

### 1.7 Compression p99 / p99.9 — facteurs **tiennent** ; quantiles épisode **pas bit-exacts** depuis les données commitées

**Fills (fichier commité suffisant) :**

| quantile | paper fill $ | recalcul | |
|---|---:|---:|---|
| p50 | 558 | 558,17 | OK arrondi |
| p90 | 12 046 | 12 045,52 | OK |
| p99 | 119 919 | 119 918,96 | OK |
| p99.9 | 582 486 | 582 486,49 | OK |

**Épisodes (compression table du papier = recollecte 351 648 eps, fichier non commité) :**

| quantile | paper épisode $ | depuis `exp017` (351 540) | Δ |
|---|---:|---:|---:|
| p50 | 1 117 | 1 116,91 | −0,09 |
| p90 | 39 288 | 39 307,42 | **+19** |
| p99 | 548 922 | 549 059,57 | **+138** |
| p99.9 | 5 834 505 | 5 835 800,40 | **+1 295** |

Facteurs avec `exp017` + fills EXP-024 :

| q | facteur recalcul | paper | |
|---|---:|---:|---|
| p50 | 2,001 | 2,00 | OK |
| p90 | 3,263 | 3,26 | OK |
| p99 | 4,579 | 4,58 | OK |
| p99.9 | 10,019 | 10,02 | OK |

Bootstrap binomial 20 000 tirages (graine 42), facteur p99 : CI **[4,41 – 4,76]** ; p99.9 : **[9,23 – 11,17]** — aligné sur [4,41 – 4,76] et [9,24 – 11,21] du papier (légère variation de graine / clip d’indice).

**Constat — affaiblit la promesse de reproductibilité.**

`paper/README.md` affirme : *« What is committed reproduces every quantile in the paper exactly »*.  
**Faux pour les quantiles *épisode* de la table de compression** : ils exigent le fichier épisodes recollecté (351 648), **non versionné**. Seuls les quantiles *fill* et les facteurs arrondis à 2 décimales sont reproductibles à l’identique. Le joinable 119 Mo n’est pas nécessaire pour les quantiles fill seuls ; il le serait pour réconcilier épisode↔fills ligne à ligne.

### 1.8 Segments majors / HIP-3 (comptage)

| | épisodes | fills | inflation | part notionnel |
|---|---:|---:|---:|---:|
| majors | 289 283 | 1 672 034 | 5,780 | 90,75 % |
| HIP-3 | 62 257 | 338 008 | 5,429 | 9,25 % |

Aligné FINDINGS / papier (5,78× / 5,43× ; 90,7 % / 9,3 %).

---

## Partie 2 — Affirmations de nouveauté / littérature

### Affirmation A — « seul enregistrement public complet *et* attribué »

**Texte abstract :** *« the only public liquidation record that is simultaneously complete and attributed to the liquidated account ».*

**Texte intro (§1) :** *« To our knowledge no **centralised** venue publishes both. »* — formulation plus étroite.

#### Contre-exemples testés (public ? complet ? adresse liquidée ?)

| venue | public | complet (pas de rate-limit type CEX) | compte liquidé | notes |
|---|---|---|---|---|
| **dYdX v4** | **oui** (Indexer + nœud) | **oui** (fills on-chain : trades, liquidations, ADL) | **oui** (adresse Cosmos / subaccount) | Docs Indexer listent explicitement liquidations comme fills on-chain : https://docs.dydx.exchange/concepts-architecture/indexer — API fills : https://docs.dydx.xyz/indexer-client/http |
| **GMX v1** | **oui** (logs Arbitrum) | **oui** (événement `LiquidatePosition`) | **oui** | Unité = événement protocole (pas multi-fill carnet) — Bitquery / docs Vault |
| **GMX v2** | **oui** (subgraph / événements) | **oui** (on-chain) | **oui** | Même logique événementielle |
| **Drift** | **oui** (Solana) | **oui** (ix liquidation on-chain) | **oui** | Bots de liquidation publics ; état comptes lisible |
| **Synthetix Perps** | partiel / évolutif | on-chain settlement | selon version | Design hybride ; pas creusé au même grain |
| **Lighter** | **oui** (proofs / data availability annoncés) | revendique liquidations vérifiables | à confirmer grain | https://docs.lighter.xyz/ — « verifiable order matching and liquidations » |
| **Jupiter Perps, Ostium, edgeX, Extended, Avantis, Aevo, Paradex, Vertex** | souvent public on-chain ou API | variable | souvent attribué si on-chain | Pas de falsification **fermante** unique trouvée pour chacun en une session ; dYdX + GMX suffisent déjà pour l’abstract |
| **Bybit `allLiquidation`** | **oui** | **oui** depuis ~fév. 2025 (tous les ordres, 500 ms) | **non** (anonyme) | Complet mais **non attribué** — le papier le note correctement |
| **Binance / OKX** | oui | **non** (maxima / 1 Hz) | non | |

**Constat — affaiblit fortement (voire invalide) la formulation de l’abstract.**

Un seul « oui aux trois » suffit. **dYdX v4** et **GMX** publient des liquidations **publiques, complètes, avec adresse**. Ce ne sont pas des CEX rate-limités.

Ce qui peut encore être défendable (et le papier le montre empiriquement) :

- seul (ou rare) **carnet d’ordres** on-chain où la liquidation est un **flux de fills** multi-niveaux, avec attribution, permettant de *mesurer* le surcomptage fill→épisode ;
- aucun **CEX** n’offre complet + attribué.

**Recommandation de formulation (sans réécrire ici) :** restreindre l’abstract à l’intro (« no centralised venue ») *ou* à « fill-level order-book record that is complete and attributed », et citer dYdX / GMX comme voisins méthodologiques (comme le lending).

#### Preuve que le problème multi-fill est déjà « produit » en industrie

Pinax / The Graph (API liquidations Hyperliquid) :

> *« Returns one row per liquidation event, **aggregated across the multiple fills that walk the book** during a liquidation. »*  
> https://app.pinax.network/docs/perp-exchanges/getV1HyperliquidMarketsLiquidations/

Dwellir (docs stream fills HL) : une liquidation produit plusieurs fills (user + contrepartie).  
https://www.dwellir.com/docs/hyperliquid/stream_fills

→ L’agrégation fill→épisode est une pratique de data vendor, pas une invention pure. Le **facteur 5,72× année** et la dépendance à la taille restent, à ma connaissance, non publiés comme mesure.

### Affirmation B — « aucun travail ne compte depuis un enregistrement fill-level ni n’énonce son unité »

**Cherché :**

| source | requête / cible | résultat |
|---|---|---|
| web général | `"liquidation" fills Hyperliquid overcount`, unit of count, tranching | docs vendors (Pinax, Dwellir) sur multi-fill ; **pas** de papier quantifiant 5×+ |
| arXiv / SSRN (via web) | Cheng, Qin, Moallemi, Chitra ADL, Lim 2026, Zhivkov | volumes / $ / cascades ; pas d’unité fill vs épisode mesurée |
| Paradigm, Delphi, Blockworks, Galaxy, Dragonfly, Kaiko, Amberdata | liquidation data bias / unit | Amberdata documente des feeds ; pas de facteur de surcomptage fill |
| Coinglass / Coinalyze / Laevitas | heatmaps | estimés OI+levier (le papier a raison de les séparer) |
| X / K33 | underrepresentation | biais **sous**-comptage CEX (Affirmation C) |
| GitHub | hyperliquid liquidation episode counting | pas de réplication du facteur trouvé |

**Verdict B :**

- **Académique / mesure publiée du facteur :** rien de comparable trouvé → la mesure 5,72× peut être nouvelle.
- **« aucun n’énonce son unité » :** **trop fort**. Les vendors HL agrègent déjà explicitement les fills ; Bybit distingue allLiquidation ; Tardis documente les limites OKX/Binance.
- **Doute** (pas constat d’invalidation totale) : absence de résultat académique ≠ preuve d’absence ; la Limitations du papier le dit déjà honnêtement.

Si le papier **sous-estime** sa nouveauté : la juxtaposition **sous-comptage CEX + surcomptage fill on-chain** et le fait que les deux **ne s’annulent pas** est un cadrage utile et peu présent dans la presse K33 (qui ne traite que le sous-comptage). À garder ; à ne pas sur-promettre sur « seul au monde ».

### Affirmation C — Binance / OKX / K33 encore vrais en 2026

**Binance `forceOrder` :** toujours rate-limité en 2026.

- Changelog derivatives : description mise à jour de *« latest »* vers *« largest »* one liquidation order within 1000 ms — cohérent avec le papier (*largest*).  
  https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/change-log  
- Streams documentés (fapi) : snapshot par symbole, 1000 ms.  
  Pages catalogue encore crawlées le 2026-07-25 avec cette limite.

**Nuance cosmétique :** certaines pages Binance disent encore « latest » et d’autres « largest ». Le papier a la version corrigée du changelog. **Toujours vrai qu’on n’a pas tous les ordres.**

**OKX :** Tardis (mise à jour 2026) : *« Liquidation orders with at most one update per second per contract »*.  
https://docs.tardis.dev/historical-data-details/okex-futures  
La doc OKX v5 live est dense ; la limite 1/s reste l’état de l’art des agrégateurs. **Pas de preuve de levée de la limite en 2026.**

**K33 / Vetle Lunde :** citation exacte retrouvée :

> *« Liquidation data from exchanges are bogus and a vast underrepresentation of actual liquidation volumes in the market »*  
> https://x.com/VetleLunde/status/1829164203438997567  
> reprise Cointelegraph etc.

**Chiffres d’ampleur (sous-estimation) :**

- Bybit CEO (fév. 2025) : Coinglass ~333 M$ Bybit vs **2,1 Md$** internes Bybit sur 24 h ; estimation marché **8–10 Md$** vs ~2,2 Md$ agrégés — facteur ~3–5× sous-comptage côté CEX.  
  https://www.coindesk.com/markets/2025/02/21/bybit-makes-liquidation-data-more-transparent-aiming-to-lure-institutional-investors  
  https://www.theblock.co/post/338482/bybit-ceo-estimates-crypto-traders-were-liquidated-for-8-10-billion-in-last-day-alone

**C tient.** Le papier pourrait même **renforcer** C avec le chiffre Bybit 2,1 vs 0,33 Md$ (il mentionne « several times » sans ce ratio).

---

## Partie 3 — Unité, échantillonnage, COI, cohérence

### 3.1 Unité de comptage et fusion 30 s / 90 s — **5,76× tient**

Recalcul indépendant sur `exp017_episodes.csv` (groupes `user×coin`, fusion si gap &lt; 90 s) :

```text
pairs consécutifs same (user,coin): 98983
<5 s:     0      (0.0 %)
5–35 s:   1757   (1.775 %)
35–90 s:  922    (0.931 %)
90 s–10 m: 2545  (2.571 %)
>10 m:    93759  (94.722 %)

chaînes ≥2 eps: 2200
épisodes dans chaînes: 4879 (1.388 %)
n après fusion 90 s: 348861
facteur: 2010042/348861 = 5.761727… → 5,76×
médiane notional départ de chaîne: 72326.48 $
```

Aligné tableau §4.2 (0 % / 1,8 % / 0,9 % / 2,6 % / 94,7 % ; 2 200 chaînes ; 4 879 eps ; 1,4 %).

Sensibilité :

| gap | facteur fusionné |
|---:|---:|
| 30 s | 5,745 |
| 35 s | 5,747 |
| 60 s | 5,754 |
| 90 s | **5,762** |
| 120 s | 5,767 |

**L’unité ne porte pas le titre** dans cette bande.

**Constat — affaiblit une formulation :** médiane des épisodes *isolés* annoncée **1 902 $** ; recalcul sous la même définition de chaîne à 90 s :

```text
médiane isolés = 1083.12 $
(médiane départs de chaîne multi = 72326.48 $ — OK)
```

Je n’ai **pas** reproduit 1 902 $ (proches : ~1 913 $ = médiane du *next* d’une paire à gap ≥ 35 s — définition différente). **Doute sur 1 902 $** tant que la définition exacte n’est pas dans le code publié. Le ratio « facteur 38 » du papier repose sur ce second nombre.

**L’unité est-elle la bonne ?**  
Argument sérieux pour une autre unité : *une liquidation économique = une position forcée jusqu’à clôture ou backstop*, en fusionnant le cooldown 30 s. Le papier teste et montre +0,04 sur le facteur.  
Argument pour coller au **hash de transaction** : c’est l’unité native du ledger ; le papier l’adopte.  
Argument contre : pour le risque de compte, le notionnel total liquidé prime — invariant au découpage (Cheng et al. déjà en volumes). Le papier le dit ; le titre reste un facteur de *comptage d’événements*, pas de notionnel.

### 3.2 Échantillonnage stratifié (02, 08, 14, 20 UTC)

**Ce que disent les données :**

```text
heures présentes: 2, 8, 14, 19, 20
slots date×heure: 1431 (attendu 365×4 = 1460 si 4 h/jour pleines)
jours avec ≠4 heures « nominales »: 28
3 fills à 19:59:59.899 UTC (frontière avant 20:00) — artefact de bord
```

Les ~29 slots manquants peuvent être des **heures sans aucune liquidation** (absentes du CSV épisodes) — **doute**, pas preuve de trous d’archive. À clarifier d’une phrase.

**Le facteur dépend de l’activité (donc potentiellement des cascades) :**

| quintile d’activité (fills/heure) | inflation moyenne du slot |
|---|---:|
| q1 (calme) | **3,84** |
| q5 (actif) | **6,71** |
| global | 5,72 |
| moyenne non pondérée des slots | 5,91 |

```text
drop top 1 % heures les plus actives → inflation 5,49
drop top 5 % → 5,25
drop top 10 % → 5,08
corr(fills_heure, inflation) ≈ +0,07
jours top 10 % activité: inf moyenne 6,50 ; bottom 10 %: 5,09
part notionnel h14: 39 % (inf 5,36) ; h20: 28 % (inf 6,12)
```

**Constat — affaiblit l’affirmation implicite « la stratification ne biaise pas le facteur ».**

- À l’intérieur de l’échantillon, plus d’activité → plus d’inflation (cohérent avec tranching size-dependent).
- On **ne peut pas** signer le sens du biais vs recensement 24/7 sans les 20 autres heures : si les cascades tombent hors {02,08,14,20}, on sous-estime ; si la structure intra-journalière des 4 heures surpondère le calme ou le stress, le facteur bouge de l’ordre de **0,5–0,7** dans les stress tests ci-dessus.
- Le paper note honnêtement « cascade hors créneaux invisible » en Limitations, mais **n’a pas testé** la dépendance activité→facteur que les données contiennent déjà.
- Paradoxe utile (déjà dans FINDINGS) : l’échantillon 12 h *sélectionné pour cascades* donnait **3,8× &lt; 5,72×** — donc la sélection cascade n’agit pas comme le simple « plus d’activité ⇒ plus d’inflation » intra-année. Mécanisme encore ouvert.

### 3.3 Conflit d’intérêts

Déclaration lue (`Declarations`) :

- opère **perplog**, trade sur HL ;
- intérêt matériel **déclaré** ;
- données = archive S3 publique, pas le produit ;
- argument « le résultat est flatteur inverse pour la venue » (surcomptage 5×).

**Suffisante ?** Forme correcte et plus honnête que beaucoup de preprints crypto.

**Penche-t-il ailleurs sans le dire ?**

- README racine et intro vendent HL comme *« fully public, tick-resolved, and — for liquidations — named »* et *« the only… »* — c’est exactement le positionnement commercial d’un outil d’orderflow HL.
- La contribution empirique (5,72×, compression) n’a **pas** besoin de l’unicité absolue pour tenir.
- **Affaiblit une formulation** : l’unicité abstraite sert l’intérêt déclaré plus que le résultat de mesure ; la déclaration COI ne compense pas une claim A trop large.

Pas de constat d’usage caché de données perplog dans les CSV (identifiants dérivés, archive S3).

### 3.4 Cohérence paper / FINDINGS / README

| item | gravité | détail |
|---|---|---|
| **194 M$ × 4 776 fills** | **invalide formulation** | partout (paper, FINDINGS, README) |
| **Implications risk models : 3,4× / 10,9×** | **affaiblit** (chiffres périmés) | `liquidation-overcounting.tex` L578–579 ; le § compression dit 4,58 / 10,02 |
| **« rank correlation » = 0,545** | affaiblit | Pearson des logs |
| **médiane isolés 1 902 $** | doute / affaiblit | non reproduit (1 083 $) |
| **paper/README « every quantile exactly »** | affaiblit | quantiles épisode compression non bit-exacts sans fichier non commité |
| **Abstract 10.0× vs table 10.02×** | cosmétique | arrondi acceptable |
| **« 1 460 hours »** vs 1 431 slots non vides | cosmétique / clarifier | heures vides possibles |
| FINDINGS vs paper sur 5,72 / 23,1 / 67,3 / 4,58 | OK | alignés |
| EXP-016 encore « α ≈ 1.15 » dans le corps historique | OK si FINDINGS gouverne | papier a retiré ; bon |

---

## Tableau de synthèse des constats

| # | constat | gravité | preuve |
|---|---|---|---|
| C1 | Max notionnel et max fills sont **deux** épisodes ; « 194 M$ en 4 776 fills » est faux | **invalide formulation** | `exp017` nlargest notional vs fills |
| C2 | Implications encore en compression **12 h** (3,4× / 10,9×) | **affaiblit** | tex L578–579 vs table L418–419 |
| C3 | Abstract « only public… complete and attributed » contredit dYdX / GMX | **affaiblit fortement claim A** | docs dYdX Indexer ; GMX LiquidatePosition |
| C4 | « Rank correlation » 0,545 est un Pearson log-log ; Spearman = 0,468 | **affaiblit** | recalcul |
| C5 | Quantiles épisode compression non reproductibles bit-à-bit depuis data commitées | **affaiblit repro** | Δ p90 +19 $, p99 +138 $ |
| C6 | paper/README « every quantile exactly » est faux | **affaiblit** | idem |
| C7 | Inflation corrélée à l’activité horaire (q1 3,8 vs q5 6,7) ; stratification non testée sur ce levier | **affaiblit** claim robustesse échantillon | groupby date×hour |
| C8 | Médiane isolés 1 902 $ non reproduite (1 083 $) | **doute → affaiblit** si non corrigé | merge 90 s |
| C9 | 5,72×, 23,1 %, 67,3 %, 72/132, 5,76×, fills quantiles, CI ordre de grandeur | **tiennent** | Partie 1 |
| C10 | Binance/OKX rate-limit encore documentés 2026 ; K33 citation exacte ; Bybit 2,1 vs 0,33 Md$ | **C tient** ; C enrichissable | liens Partie 2 |
| C11 | Vendors HL agrègent déjà multi-fill | **affaiblit** « personne n’énonce l’unité » | Pinax docs |
| C12 | COI déclaré OK ; claim d’unicité aligne intérêt commercial | **affaiblit** formulation A | Declarations + abstract |

---

## Ce qui a été tenté et a tenu

1. Recalcul naïf `sum(fills)/n` → **5,7178 = 5,72**.
2. Top 1 % par rang notionnel → **72 / 132,27 / 23,14 % fills / 67,29 % notionnel**.
3. Pearson logs → **0,5454**.
4. Fusion chaînes 90 s → **5,7617**, 2 200 chaînes, 4 879 eps, départ **72 326 $**.
5. Quantiles fill EXP-024 → match paper ; facteurs 4,58 / 10,02 stables.
6. Bootstrap binomial p99/p99.9 → IC dans le même intervalle publié.
7. Six définitions d’unité (EXP-016, 12 h) non rejouées ici (échantillon 12 h seulement) ; la robustesse année repose sur le test 90 s, rejoué avec succès.
8. Affirmation C (docs CEX 2026) : pas de démenti trouvé.
9. Pas de papier académique trouvé avec un facteur de surcomptage fill-level comparable.

## Ce qui casse ou fend

1. **194 M$ ≠ 4 776 fills** (C1) — correction factuelle obligatoire.
2. **Implications périmées** (C2).
3. **Claim A abstract** (C3) — reformuler avant SSRN/arXiv.
4. Libellé corrélation (C4), repro quantiles épisode (C5–C6), biais d’échantillonnage non testé (C7), 1 902 $ (C8).

---

## Recommandation de soumission

**Ne pas déposer** tant que C1, C2 et la reformulation de A ne sont pas traités.  
Après correction de ces trois points, le cœur empirique (Partie 1 hors C1) est assez solide pour un preprint de mesure, avec la Limitations déjà présente sur la recherche bibliographique.

Je n’ai **pas** « validé » le papier. J’ai cassé ce qui cassait et listé ce qui a résisté.

---

## Annexe — commandes de reproduction (extraits)

```bash
cd ~/hlm-review-grok
.venv/bin/python <<'PY'
import numpy as np, pandas as pd
ep = pd.read_csv('experiments/data/exp017_episodes.csv')
fl = pd.read_csv('experiments/data/exp024_fill_notionals.csv.gz')
print('n, fills, factor', len(ep), int(ep.fills.sum()), ep.fills.sum()/len(ep))
top = ep.nlargest(3516, 'notional')
print('top1 fills share', top.fills.sum()/ep.fills.sum())
print('top1 ntl share', top.notional.sum()/ep.notional.sum())
print('top1 med/mean fills', top.fills.median(), top.fills.mean())
print('pearson logs', np.corrcoef(np.log(ep.notional), np.log(ep.fills))[0,1])
print('max ntl', ep.loc[ep.notional.idxmax(), ['coin','fills','notional']].to_dict())
print('max fills', ep.loc[ep.fills.idxmax(), ['coin','fills','notional']].to_dict())
for q in [50,90,99,99.9]:
    a,b = np.percentile(ep.notional,q), np.percentile(fl.notional,q)
    print(f'p{q}', a, b, a/b)
PY
```

Branche : `review/grok` uniquement. Aucun push. Aucune collecte S3.
