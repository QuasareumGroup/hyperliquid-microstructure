# Revue adverse — rapport FABLE

Relecteur : Claude (Fable 5), arbre `~/hlm-review-fable`, branche `review/fable`, base `25e0bac`.
Second relecteur indépendant (Grok) non consulté. Tout recalcul ci-dessous a été fait avec du
code écrit pour cette revue — commité dans `review/r1…r5*.py` — sans importer le code du dépôt.
Environnement : Python 3.11.5, numpy 2.4.6, scipy 1.17.1. Le papier compile
(`tectonic -X compile paper/liquidation-overcounting.tex --outdir paper` → PDF, warnings
typographiques seulement).

**Verdict d'ensemble.** Le cœur empirique se reproduit remarquablement bien : sur les huit
chiffres porteurs, sept sont exacts au chiffre près depuis les données versionnées, et mes
attaques principales — bootstrap des quantiles, validité de Vuong, corrélations partielles,
sélection de xmin, plancher de 5 événements — n'ont **pas** renversé de résultat. Mais la revue
trouve : **(A)** deux énoncés publiés faux (le plus gros épisode n'a pas 4 776 fills ; la section
Implications cite les facteurs de compression périmés), **(B)** une description d'unité fausse
dans le papier (l'unité réellement calculée n'est pas « (account, transaction) »), un appareil
d'incertitude sans code committé et reposant sur une hypothèse d'indépendance fausse dans le
corps de la distribution, une incertitude d'échantillonnage jamais quantifiée autour de 5,72,
et plusieurs formulations plus fortes que ce que les données montrent. Rien de tout cela ne
touche la direction ou l'ordre de grandeur des résultats de tête ; tout est corrigeable
localement avant dépôt.

---

## A. Constats qui invalident un énoncé publié

### A1. Le plus gros épisode ($194 115 094) compte 2 568 fills, pas 4 776

Le fichier versionné dit sans ambiguïté que « $194,115,094 across 4,776 fills » est une
**conflation de deux épisodes différents** : le plus gros épisode *par notionnel* (BTC,
2025-11-17 14:36 UTC) a 2 568 fills ; le maximum de *fills par épisode* (4 776) appartient à un
épisode ZEC de $32,4 M (2026-06-04 02:03 UTC).

Commande (`review/r1b_followups.py`) et sortie :

```
max notionnel : $194,115,094  fills=2,568  coin=BTC  ts=2025-11-17 14:36:45
max fills     : 4,776 fills  $32,447,999  coin=ZEC  ts=2026-06-04 02:03:48
top 5 par fills :
   4,776 fills  $     32,447,999  ZEC        2026-06-04 02:03:48
   4,344 fills  $     12,300,166  HYPE       2025-10-09 14:31:30
   2,990 fills  $    127,716,857  ETH        2025-10-10 20:52:54
   2,568 fills  $    194,115,094  BTC        2025-11-17 14:36:45
```

Occurrences fausses : `paper/liquidation-overcounting.tex:427` (« The largest episode in the
sample, \$194,115,094 across 4,776 fills, appears in the fill record as pieces of at most
\$10.99M »), `experiments/FINDINGS.md:94`, `README.md:46`. Occurrences **correctes** du même
nombre (maximum de fills par épisode, sans l'attacher au $194 M) : `paper:351`,
`FINDINGS.md:64`. L'origine probable est visible dans `paper:230` : la re-collecte a vérifié
« the largest episode and its fill count » comme deux scalaires séparés (max notionnel ✓, max
fills ✓) puis le texte les a soudés en un seul épisode. Aucun script committé ne calcule cette
phrase (voir B2). La ligne « max 17.7× » de la table de compression n'est pas touchée : c'est un
rapport de deux maxima, pas une affirmation qu'ils appartiennent au même épisode — mais la
phrase de `paper:427` l'affirme, et elle est fausse.

### A2. La section Implications cite les facteurs de compression périmés (12 h) comme s'ils étaient le résultat

`paper:578-579` : « A size distribution fitted on fills is compressed by **3.4×** at the 99th
percentile and **10.9×** at the 99.9th. » Ce sont les valeurs du vieil échantillon 12 h que le
papier lui-même remplace par **4,58×** et **10,02×** (Table 4, `paper:418-419`) et dont il dit
« The cascade-selected sample **understated** this » (`paper:430-437`).

```
$ grep -n "3.4\$\\\\times\$" paper/liquidation-overcounting.tex
432:...It reported 1.6$\times$, 2.1$\times$, 3.4$\times$ and     <- usage historique, correct
578:...compressed by 3.4$\times$ at                               <- présenté comme le résultat, périmé
```

C'est le paragraphe que les praticiens citeront. Il contredit la table du même papier.

---

## B. Constats qui affaiblissent une formulation ou un dispositif

### B1. L'unité de comptage annoncée n'est pas celle qui a produit les chiffres — et une ligne du tableau cooldown est vraie par construction

Le papier (`paper:270-271`) : « We adopt **(account, transaction)** for the remainder. » Or le
collecteur de l'échantillon année (`experiments/exp017_year_tail.py:50-52`) définit :

```python
#: Episode = maximal run of fills for one (user, coin) separated by <= this.
EPISODE_GAP_MS = 5_000
```

Tous les chiffres à l'échelle de l'année — 351 540, 5,72×, la table par taille, le tableau
cooldown — sont donc calculés sur l'unité **(compte, instrument, écart ≤ 5 s)**, pas sur
(account, transaction). Aucun hash de transaction n'est même conservé à l'année.

Deux conséquences :

- **La première ligne de la Table 3 (`paper:376`, « < 5 s : 0 pairs, 0.0% ») est un
  tautologisme.** Deux épisodes consécutifs de la même clef sont séparés de > 5 s *par
  définition* de l'unité. Présenter ce 0 % comme un fait empirique (« The cooldown signature is
  present and small ») est trompeur ; seules les lignes ≥ 5 s sont informatives.
- La discussion §4.2 (« Our (account, transaction) unit would count those separately »,
  `paper:360-362`) raisonne sur une unité qui n'est pas celle du calcul.

Direction : favorable au papier. Sur 12 h, (user, tx) donne 6 412 unités contre 6 546 au
5 s-gap (`experiments/data/exp016_units.csv`, table `paper:254-266`), donc une vraie unité
(account, transaction) donnerait un facteur **plus haut** (~+2 %). Mes recomptes à l'année
(`review/r1_part1_recompute.py`, section E) :

```
(compte, instrument, heure) : 343,412 unites -> facteur 5.853
(compte, heure) toutes coins: 312,928 unites -> facteur 6.423
```

Même l'unité trans-instruments la plus agressive (une liquidation = un compte-heure,
cross-margin) monte à 6,42×. 5,72 est du côté conservateur pour toutes les unités testées ;
c'est la *description* qui est fausse, pas la robustesse.

### B2. Les intervalles de confiance de la compression n'ont aucun code committé ; leur hypothèse d'indépendance est fausse dans le corps de la distribution

Aucune fonction `bq` n'existe dans le dépôt ; `exp024_analyse.py` ne calcule que des points ;
l'historique git ne contient aucune version avec bootstrap :

```
$ grep -rn "def bq\|binomial" --include="*.py" .   (hors .venv)
(aucun résultat)
```

Les IC publiés (Table 4 du papier ; EXP-024 §6) sortent donc d'un code jamais versionné, alors
que `paper:55-56` (abstract) affirme « All data, code and pre-registrations are public » et que
la déviation de verdict d'EXP-024 §6 montre déjà que l'analyse publiée a débordé le script
committé. Autres nombres publiés sans code committé, que j'ai tous re-dérivés : la table de
tranchage/parts/corrélation de FINDINGS §2 (reproduite, sauf A1 — c'est le mode de défaillance
attendu d'une analyse hors dépôt), le tableau cooldown §4.2 (reproduit), les Spearman du
drapeau d'EXP-021 §7 (reproduits — sur les 191 heures usable, sous-ensemble non déclaré), les
partielles groupées et le Fisher d'EXP-023 §8 (reproduits exactement), et « (user, tx) = 6 412 »
(non recalculable : aucun hash publié ; borne de cohérence : somme de la colonne `txs` = 6 582 ≥ 6 412 ✓).

J'ai ensuite identifié et testé la méthode des IC (`review/r2_bootstrap.py`) :

```
(i) Beta/binomiale, cotes independants, 20,000 tirages
p99.0      4.58  [  4.41,   4.76]   IC publie [4.41, 4.76]
p99.9     10.02  [  9.21,  11.12]   IC publie [9.24, 11.21]
(ratios majors/HIP-3, r5 §1 : p90 [1.24, 1.36], p99 [0.74, 0.90] = publiés)
```

Les IC publiés sont donc bien un bootstrap binomial de la statistique d'ordre, **côtés épisode
et fill tirés indépendamment**. Or les fills *composent* les épisodes — les deux quantiles ne
sont pas indépendants. Sur l'échantillon 12 h, où l'appartenance épisode→fills est versionnée
(`exp016_fills.csv`), le bootstrap par grappes d'épisodes (correct) contre l'indépendant :

```
     q   grappes (correct)       independant  rapport largeur
p50.0   [  1.37,   1.72]   [  1.44,   1.70]       1.39
p90.0   [  1.71,   2.48]   [  1.76,   2.39]       1.22
p99.0   [  2.66,   4.47]   [  2.80,   4.67]       0.97
p99.9   [  5.75,  16.76]   [  6.64,  18.91]       0.90
```

Dans le corps (p50, p90), l'indépendance **sous-estime** la largeur de 20–40 % — les fills
arrivent en grappes intra-épisode, ce que le tirage iid ignore ; en queue elle est à peu près
juste, voire légèrement large. Aucune conclusion ne bascule : les IC de la Table 4 excluent les
valeurs 12 h par des marges bien supérieures à 40 %. Mais les IC p50/p90 publiés sont trop
étroits, la méthode n'est décrite qu'en une parenthèse d'EXP-024, et l'hypothèse d'indépendance
n'est déclarée nulle part.

### B3. « 5.72 » est publié sans aucune incertitude ; la variabilité réelle est au troisième chiffre près

Deux sources d'incertitude, aucune quantifiée dans le papier :

- **Échantillonnage des jours.** Bootstrap par grappes de jours (`review/r2_bootstrap.py`,
  section iv) : IC 95 % **[5,45 – 6,00]**, écart-type 0,14 — trois fois l'écart-type iid-épisodes
  (0,047), parce que les cascades concentrent les fills (2025-10-10 porte à lui seul 5,4 % des
  fills ; les 5 plus gros jours, 14,0 % ; facteur journalier : médiane 5,18, p90 8,20).
- **Stratification horaire.** Quatre strates sur 24 sont observées, et le facteur varie
  systématiquement entre elles (`review/r5_complements.py`, §5) :

```
 h UTC    tous  majors   HIP-3
     2   5.693   5.691   5.705
     8   6.027   6.089   5.726
    14   5.356   5.383   5.258
    20   6.120   6.239   5.399
```

  Le spread (5,36–6,12 ; 5,38–6,24 au sein des majors seuls, donc pas un effet de composition
  HIP-3) est du même ordre que l'IC jours. 14 UTC porte 38,1 % des fills de l'échantillon : les
  heures se ressemblent peu. Les 20 heures non observées peuvent tirer le facteur dans un sens
  comme dans l'autre — la *direction* du biais de stratification est indéterminable de
  l'intérieur, mais son *ampleur plausible* (±0,3–0,4) est du même ordre que le spread observé.

Conséquence de formulation : « **unbiased** archive year » (`FINDINGS.md:63`, EXP-024 §1) et le
5,72 à trois chiffres significatifs sans IC (`paper:283-285`, abstract) promettent une précision
que l'échantillon ne soutient pas. La limitation du papier (« a cascade falling entirely outside
those hours is invisible », `paper:597-598`) décrit le cas extrême mais pas cette exposition
ordinaire. L'énoncé robuste est : facteur ≈ 5,7, IC jours [5,45–6,00], hétérogénéité horaire du
même ordre.

### B4. Les quantiles épisodes de la table de compression ne sont pas reproductibles depuis les données publiées ; « reproduces every quantile … exactly » est trop fort

Le côté *fills* de la Table 4 se reproduit exactement depuis
`exp024_fill_notionals.csv.gz` ($558 / $12 046 / $119 919 / $582 486 / $10 990 000 ✓,
`review/r1_part1_recompute.py` §C). Le côté *épisodes* vient du fichier de la **seconde passe
(351 648 épisodes), non committé** ; le fichier committé (première passe) donne d'autres
dollars :

```
     q   episode$ (1ere passe)   publie (Table 4)
p90                39,307          39,288
p99               549,060         548,922
p99.9           5,835,800       5,834,505
```

Les **facteurs** à la précision affichée sont insensibles (3,26 / 4,58 / 10,02 dans les deux
cas), donc le résultat tient — mais : (a) `EXP-024:9-10` (« reproduces every quantile below
exactly ») est faux pour la colonne épisodes, qu'aucun fichier publié ne reproduit ; (b) la
régénération S3 documentée ne rendrait pas ces valeurs non plus (l'archive a déjà dérivé de
0,03 % entre les deux passes) ; (c) combiné à B2 (code des IC absent), l'« All data, code …
are public » de l'abstract est deux fois trop fort. La ligne majors p99.9 (10,88 publié contre
10,89 recalculé première passe) a la même cause.

### B5. « The rank correlation between log notional and log fills per episode is +0.545 » — ce n'est pas une corrélation de rangs

`paper:349`. Une corrélation de rangs est invariante par log ; la valeur +0,545 est le
**Pearson des logs**. Recalcul (`review/r1_part1_recompute.py` §B) :

```
Pearson(ln ntl, ln fills) = +0.5454   (annonce +0.545)
Spearman(ntl, fills)      = +0.3829
```

Un lecteur qui vérifie la « rank correlation » trouvera 0,38 et conclura à une erreur.
`FINDINGS.md:68` (« corr(ln notional, ln fills) ») est, lui, correct.

### B6. « $1,902 for isolated episodes » repose sur une définition non déclarée et non naturelle

`paper:391-392`, `FINDINGS.md:77`. La définition naturelle — épisodes hors de toute chaîne
≤ 90 s — donne une médiane de **$1 083**. La valeur publiée correspond à « hors chaîne **et**
ayant au moins un autre épisode de la même clef (compte, instrument) dans l'année », un
sous-ensemble de comptes re-liquidés (n = 141 417) que rien dans le texte n'annonce
(`review/r1b_followups.py`) :

```
(a) tous les episodes hors chaine                  : mediane $1,083  n=346,661
(b) hors chaine, avec au moins un voisin même clef : mediane $1,902  n=141,417   <- la valeur publiée
```

Le contraste avec $72 326 (que je reproduis à l'identique) est *plus fort* sous la définition
naturelle (×67 au lieu de ×38) — l'argument survit, mais le chiffre publié n'est pas celui que
la phrase décrit.

### B7. « lognormal and Weibull each dominate Pareto at all 14 estimable thresholds » — à un seuil sur 14, la comparaison n'est pas significative ; et une plage de R de la Table 5 est fausse

`paper:461-463`. À k = 277 (xmin $6,9 M), leur propre grille (`exp022_grid.csv`, ligne 3) et mon
refit indépendant (`review/r3_tail.py` §4) donnent :

```
    277   6,908,537     -1.78  0.0743     -1.82  0.0684
```

R pointe vers les alternatives mais p ≈ 0,07 : « dominate » sur-affirme à ce seuil (l'ordre des
vraisemblances tient à 14/14, la significativité à 13/14). Dans le même registre, la Table 5
(`paper:484-486`) donne pour $1,85 M–$8,85 M « R = −1.00 to −1.86 » : à $8,85 M (k = 200), le R
lognormale-contre-Weibull est **+0,36** (p = 0,72) — dans la plage annoncée du tableau, hors de
l'intervalle de R annoncé. Le verdict « indistinguishable » est inchangé ; la plage citée est
factuellement fausse à son extrémité.

### B8. §6.3 « A band where nothing fits » : la conclusion tient, le diagnostic imprimé est à moitié faux

`paper:499-501` : « both alternatives converge on a parameter bound—lognormal with μ → −∞ … ».
Contredit par **leur propre grille** à 2 des 4 seuils exclus : `exp022_grid.csv` donne
ln_mu = **1.956** (k = 26 113) et **−17.11** (k = 18 871) — intérieurs, pas sur la borne μ = −30 ;
seule la Weibull est épinglée par la borne λ ≥ 10⁻⁹ **du script** (`exp022_xmin.py:99`). Même
constat d'EXP-022 §7 (« lognormal at μ = −30 »). Avec des bornes plus larges (μ ∈ [−60, 40],
ln λ ∈ [−45, 45]), les deux familles convergent à l'intérieur ou près de mes bornes… et le GoF
absolu rejette quand même (`review/r5_complements.py` §2) :

```
k=26,113 xmin=$49,362 lognormale mu=1.96 sigma=3.57  KS=0.0412 GoF p=0.000
k=26,113 xmin=$49,362 weibull beta=0.0759 lam=3.9e-14 KS=0.0409 GoF p=0.000
k=18,871 xmin=$76,644 lognormale mu=-17.13 sigma=5.75 KS=0.0462 GoF p=0.000
k=18,871 xmin=$76,644 weibull beta=0.0595 lam=2.9e-20 KS=0.0527 GoF p=0.000
```

Donc : « rien n'ajuste dans la bande » est **vrai**, mais la preuve imprimée (« les deux sur une
borne, donc non identifiés ») est bancale — la borne est celle de l'optimiseur, et la lognormale
n'y était même pas. Le GoF direct est l'argument solide, et il manque au papier. Détail
adjacent : la règle d'exclusion a coûté au papier deux seuils où la lognormale battait Pareto
proprement (R = −7,53 et −2,68 dans leur CSV) — l'exclusion joue *contre* leur claim P2, pas
pour.

### B9. « Each experiment is pre-registered … committed before the run, and the commit ordering is checkable » — faux pour 4 des 9 expériences dont dépend le papier

`paper:621-623`. L'historique (`git log --oneline --all`) montre des paires
pré-enregistrement → résultats pour EXP-017 (`826509f` → `3fbbfa5`) et EXP-021→024
(`e9cf731`→`d32accf`, `c6a3d6d`→`bd30039`, `ef289b8`→`b89b19e`, `18f6e1f`→`eb3ab99`→`37e1865`),
mais **EXP-016, EXP-018, EXP-019 et EXP-020 arrivent en un seul commit contenant déjà les
résultats** (`41f30f1`, `ed59208`, `0ccf5e8`, `defcae4`). Le README (`README.md:68-71`,
« Several were committed while the campaign was still collecting ») est honnête ; la phrase du
papier, universelle, est vérifiable et fausse. Or le papier s'appuie sur EXP-016 (Table 1),
EXP-019/020 (rejet de Pareto, candidats).

### B10. « the goodness-of-fit bootstrap … makes the reported p conservative toward rejection » — la direction est au mieux ambiguë, au pire inversée

`paper:601-602`, `EXP-022:235-237`. Le d_obs est un KS **minimisé** par la sélection de seuil ;
les d_syn ne le sont pas (xmin fixé dans les synthétiques). Un d_obs optimisé comparé à des
d_syn non optimisés donne p = P(d_syn ≥ d_obs) **surestimé** — c'est-à-dire biaisé *contre* le
rejet. Comme ils rejettent quand même (p = 0,010 ; mon re-run indépendant : p = 0,013,
`review/r3_tail.py` §3), le rejet est a fortiori — conclusion inchangée, mais la phrase, telle
qu'écrite, décrit la direction inverse de la simplification, et un rapporteur s'y arrêtera.

### B11. Déclaration d'intérêts : complète sur les faits, mais la dernière phrase est un plaidoyer

`paper:636-643`. Ce qui est bien : la déclaration est en tête des Declarations, nomme le
produit (perplog), le trading sur la venue, l'indépendance des données (archive publique
requester-pays), et anticipe l'objection. Ce qui l'affaiblit : « The finding itself is
unflattering to the venue's ecosystem…—which is the opposite of what a commercial interest
would motivate » est un argument, pas une divulgation — et il est contestable : le papier
établit simultanément que l'archive de Hyperliquid est « the only public liquidation record
that is simultaneously complete and attributed » (abstract), c'est-à-dire le substrat canonique
du sujet — exactement l'écosystème dont vit un produit d'orderflow Hyperliquid. Les deux
lectures sont défendables ; une déclaration n'a pas à trancher pour le lecteur. Pour le reste,
je n'ai pas trouvé de penchant non déclaré : la section CEX s'appuie sur la documentation des
venues, la caractérise correctement (j'ai vérifié la cohérence interne des affirmations avec
EXP-016 ; pas de re-vérification en ligne des docs), et le papier désavantage aussi Hyperliquid
(c'est son titre). Suggestion de rapport, pas de réécriture : supprimer la phrase d'avocat.

---

## C. Cosmétique

- **C1.** « reproduces every count statistic … to three decimal places » (`paper:229`,
  `FINDINGS.md:57-58`) : le facteur d'inflation est 5,71782 (1re passe) contre 5,71684 (2e) —
  5,718 ≠ 5,717 à trois décimales (`review/r5_complements.py` §6). Vrai à deux décimales.
- **C2.** « The second pass returned … **0.03% more** » (`paper:230`) : épisodes +0,031 %,
  fills +0,014 %. Le « 0.03 % » global double l'écart des fills ; `paper:593-594` (Limitations)
  donne les bons comptes bruts.
- **C3.** EXP-022 §3 annonce une grille de « 20 log-spaced grid points », le CSV en contient 18,
  le défaut du script est 14 (`EXP-022:73`, `exp022_grid.csv`, `exp022_xmin.py:314`).
- **C4.** Trois épisodes de l'échantillon année sont horodatés 19:59:59 UTC (fichiers d'heure
  20) : `2026-06-26 19:59:59 xyz:DRAM ×2, xyz:MU` — débordement de bloc en bord d'heure,
  inoffensif, mais « four fixed hours » n'est pas *exactement* vrai du fichier
  (`review/r1b_followups.py` §3).
- **C5.** Les Spearman d'EXP-021 §7 (+0,034 / −0,015) sont calculés sur les **191 heures
  usable**, pas sur les 193 classées ; sur 193 : +0,003 / −0,040. Même conclusion (« non
  corrélé »), sous-ensemble non déclaré (`review/r5_complements.py` §3).
- **C6.** `README.md:59` illustre la section queue avec le Hill plot d'EXP-018 — le graphe d'une
  quantité que FINDINGS déclare retirée (« real as a property of the estimator and empty as an
  estimate ») — sans légende ni renvoi à la rétractation.
- **C7.** Le Spearman étendu d'EXP-021 : j'obtiens −0,096 contre −0,099 annoncé (traitement des
  ex æquo : leur `spearman` maison ne corrige pas les ties, scipy si). Sans conséquence.

---

## D. Ce qui a été attaqué et a tenu

### D1. Les huit chiffres porteurs (recalcul indépendant, `review/r1_part1_recompute.py`)

| affirmation | annoncé | recalculé | verdict |
|---|---|---|---|
| inflation | 5,72× (2 010 042 / 351 540) | 5,7178× (2 010 042 / 351 540) | ✓ exact |
| tranchage top 1 % | médiane 72, moyenne 132 | 72 ; 132,30 (rang) / 132,27 (bord $) | ✓ |
| part des fills, top 1 % | 23,1 % | 23,14 % | ✓ |
| part du notionnel, top 1 % | 67,3 % (85,6 / 92,6) | 67,29 % (85,59 / 92,57) | ✓ |
| compression p99 | 4,58× [4,41–4,76] | 4,58× ; IC Beta [4,41–4,76] | ✓ (réserves B2/B4) |
| compression p99.9 | 10,02× [9,24–11,21] | 10,02× ; Beta [9,21–11,12], naïf [9,22–11,06] | ✓ idem |
| corr(ln ntl, ln fills) | +0,545 | +0,5454 (Pearson des logs) | ✓ (étiquette : B5) |
| plus gros épisode | $194 115 094 en 4 776 fills | $194 115 094 en **2 568** fills | **✗ → A1** |

Également exacts : segments 5,78 / 5,43 et leurs comptes, 380 instruments, 151 730 comptes,
$15,53 Md, parts HIP-3 17,7 % / 9,25 %, buckets Table 2 (2/2,19 ; 2/3,94 ; 8/19,11 aux bords
$1 117 / $39 307 / $549 060), plus gros fill $10 990 000 (4 fills > $10 M, 2 valeurs distinctes
— l'observation « nombre rond » d'EXP-024 §6 est confirmée), et l'échantillon 12 h (3,75× ;
corr +0,509 ; compression 1,56/2,06/3,36/10,93 ; top 1 % fills 30,8 %). Les fichiers de figure
concordent avec les données committées (CCDF : écart max 2,8e-05 / 3,0e-06 ; les 20 bins de
`fills_by_size.dat` reproduits, n min = 33 ≥ 30 comme en légende).

### D2. Le bootstrap binomial à p99.9 (la question posée) — il tient

La représentation binomiale/Beta de la statistique d'ordre est *exactement* la loi du quantile
bootstrap ; ce n'est pas une approximation asymptotique. Vérifié contre un bootstrap naïf
complet (3 000 ré-échantillons de 2,01 M / 351 k valeurs, `review/r2_bootstrap.py` §ii) :

```
p99.9   naïf [9.22, 11.06]   Beta [9.21, 11.12]   publié [9.24, 11.21]
```

Concordance aux fluctuations Monte-Carlo près, malgré la discrétisation réelle en queue (le
quantile épisode p99.9 ne prend que ~140 valeurs distinctes sur 20 000 tirages). Là où ça casse
n'est pas la binomiale : c'est l'indépendance des deux côtés (B2) et l'absence du code (B2).

### D3. Vuong sous double mauvaise spécification (la question posée) — l'usage est légitime

La prémisse de l'attaque est inversée : le test de Vuong (1989) est précisément construit pour
des modèles **mal spécifiés** (théorie QMLE ; H0 : égalité des distances de Kullback-Leibler à
la vraie loi). Comparer deux familles toutes deux rejetées par KS est son cas d'usage : il
répond « laquelle est la plus proche », jamais « laquelle est vraie » — et le papier exploite
les deux niveaux correctement (classement par Vuong, rejet absolu par KS bootstrap). Points de
validité vérifiés : les paires comparées sont strictement non emboîtées ✓ ; la seule paire
emboîtée (Pareto ⊂ pareto_cutoff) utilise un LR, pas Vuong ✓ (`exp020_alternatives.py:183-188`)
— avec un caveat de frontière (λ = 0 au bord ⇒ le χ²(1) double le p ; sans conséquence ici, les
LR vont de 14,9 à 1 115) ; la zone dangereuse de Vuong (ω² → 0, densités qui se confondent) est
exactement la bande dégénérée, qu'ils excluent ✓ ; pas de correction de dimension entre Pareto
(1 param.) et les alternatives (2) — l'ajustement type BIC (~4,3 log-unités à k = 5 000) ne
renverse aucun R décisif. Une seule formulation à surveiller : « an exponential is rejected
decisively (Vuong…) » (`paper:454-456`) fait dire au test relatif une chose absolue. J'ai comblé
le trou : GoF absolu de l'exponentielle au xmin sélectionné, KS = 0,296, **p = 0,000** (1 000
bootstraps paramétriques, `review/r3_tail.py` §3) — l'énoncé absolu est vrai, il n'est juste pas
étayé par le bon test dans le texte.

### D4. Sélection de xmin et parade de la grille (la question posée) — la parade suffit, et j'ai essayé de la casser

Reproduction indépendante intégrale (`review/r3_tail.py`) : sélection CSN identique
($560 627, k = 3 104, KS = 0,0234, α = 0,960), IC bootstrap du xmin [194 k, 958 k] contre
[194 k, 987 k] annoncé (bruit MC), log-vraisemblances d'EXP-020 à la décimale près
(−74 307,3 / −74 308,6 / −74 339,1 / −76 965,1), R de Vuong de la grille à ±0,01, R = +11,96
du papier retrouvé. Puis deux tentatives de démolition du « renversement » (le cœur de « the
tail cannot be named ») :

- **Vérité lognormale simulée** (LN ajustée aux majors, n = 289 283, 3 réplicats, 6 seuils) :
  le motif observé — Weibull gagnant à p < 0,01 sur une bande de seuils profonds — **n'apparaît
  jamais** (R ∈ [−1,9, +3,1], aucun R < 0 significatif à 1 %).
- **Vérité Weibull simulée** (β = 0,23 ajusté, idem) : le motif « lognormale gagne R = +13 à +16
  dans le corps » **n'apparaît jamais** (|R| ≤ 2,3).

Le renversement des vraies données (−3,67 à −2,74 sur $199 k–$1,33 M ; +13,4/+15,9 sous $28 k)
n'est donc pas un artefact de troncature d'une famille unique : il reflète bien deux régimes
locaux différents. La conclusion négative du papier sort **renforcée** de la revue. Réserves
restantes : B7 (un seuil sur 14 non significatif), B8 (le diagnostic de la bande), et le fait —
reconnu par EXP-022 §2 — que les seuils de la grille sont des statistiques d'ordre des mêmes
données (18 tests corrélés ; acceptable pour une claim qualitative de stabilité).

### D5. Le plancher de 5 événements (la question posée) — il n'a jamais pu décider

Le plancher ne peut changer une classification que si 0,25 × (compte attendu de l'autre venue
dans la fenêtre de silence) < 5, soit un attendu < 20 événements. Sur les données committées des
quatre actifs (`review/r5_complements.py` §4) :

```
BTC : silences>=60s hl/bin/okx = 2/0/0 ; heures ou le plancher PEUT decider : 0
ETH : 2/0/0 ; 0        SOL : 8/0/0 ; 0        HYPE : 2/0/0 ; 0
```

Les seuls silences ≥ 60 s du jeu sont les vraies pannes HL (dont les deux de 07:00 UTC), toutes
avec des comptes attendus ≥ 20 chez Binance/OKX. Avec plancher 0 ou plancher 5, chaque
classification du jeu publié est identique : la déviation post-enregistrement est déclarée
(`EXP-021:142-147`), motivée en principe, et **immatérielle en fait** — elle n'a pas pu être
ajustée pour obtenir un résultat, puisqu'elle n'en a produit aucun. (Sa valeur « 5 » reste
arbitraire et n'est testable que sur une fenêtre plus pauvre en événements.)

### D6. Corrélations partielles sur rangs (la question posée) — l'hypothèse non vérifiée est vérifiée, et elle ne porte rien

`review/r4_leadlag.py` : la méthode « résidus de régression linéaire sur rangs » coïncide avec
la formule classique de la partielle de Spearman **à la 4e décimale** sur les quatre actifs et
en groupé ; une variante par résidus **cubiques** donne −0,0900/−0,0992 contre −0,0895/−0,1003 ;
le tau de Kendall partiel concorde (−0,088/−0,088) ; le test direct de courbure (terme
quadratique rang-rang) est non significatif dans 11 cas sur 12 — l'exception (HYPE,
rang(nret)~rang(range), p = 0,041) est la relation de contrôle, au taux attendu par hasard.
Les chiffres groupés se reproduisent exactement : marginale −0,213 ; partielles −0,0895
(p = 0,0138) / −0,1003 (p = 0,0057) ; non-BTC −0,1194 (p = 0,0045) ; Fisher p = 0,0625. La
limite déclarée d'EXP-023 §9 (« assumes the rank relation is roughly linear. Not checked »)
peut être fermée telle quelle.

### D7. Fusion des chaînes et cooldown — tout se reproduit au chiffre près

`review/r1_part1_recompute.py` §D : 98 983 paires ✓ ; bins 0 / 1 757 / 922 / 2 545 / 93 759 ✓ ;
2 200 chaînes couvrant 4 879 épisodes (1,39 %) ✓ ; fusion → 348 861 unités → **5,7617×** ✓ ;
médiane des débuts de chaîne $72 326 ✓ ; 4,86 % d'épisodes > $100 k ✓. Le calcul annoncé
« 5,72 → 5,76 » est exact (réserves B1 sur l'unité et B6 sur « isolated »).

### D8. EXP-021 (heures récupérées) — les chiffres de tête se reproduisent

193 heures, 49 flaggées, 47 complètes (95,9 %), 191 usable, médianes 35,5/34,8 et 9 442/9 760,
Mann-Whitney z = +0,47 p = 0,637, récupérées 47/47 Binance mène, médiane 575 ms, étendu 191 h
575 ms, span 4,2–187,8 — tous conformes (`review/r4_leadlag.py` §C ; réserves C5/C7,
sans effet).

---

## E. Réponse à la question de reproductibilité posée par la mission

« Vérifie que ce qui est publié suffit réellement à reproduire ces quantiles, ou dis que non. »
Réponse : **les quantiles fills, oui, exactement ; les quantiles épisodes de la Table 4, non**
(ils exigent le fichier 2e passe non committé ; la 1re passe committée donne d'autres dollars,
mêmes facteurs à 2 décimales — B4) ; **les IC, non** (aucun code ; méthode identifiée et
reproduite ici — B2) ; le reste des chiffres du papier se reproduit depuis les fichiers
committés (D1, D7, D8).

## F. À corriger avant dépôt (constats, pas de patchs — l'auteur décide)

1. A1 — remplacer « across 4,776 fills » par le vrai compte (2 568) aux trois emplacements, ou
   citer l'épisode ZEC pour le max de fills.
2. A2 — mettre la section Implications au niveau de la Table 4 (4,58× / 10,02×).
3. B1 — décrire l'unité réellement utilisée à l'année ((compte, instrument, écart 5 s)) et
   retirer la ligne « < 5 s » du Tableau 3 ou la marquer « par construction ».
4. B2/B4 — committer le code des IC ; déclarer l'indépendance des deux côtés (ou passer aux
   grappes) ; restreindre « reproduces every quantile exactly » aux fills ; ajuster « All data,
   code … are public ».
5. B3 — publier une incertitude sur 5,72 (IC jours [5,45–6,00]) et adoucir « unbiased ».
6. B5, B6, B7, B8, B9, B10, B11, C1–C3 — corrections d'une ligne chacune, listées ci-dessus.
