<script lang="ts">
  import { onMount } from 'svelte';
  import type { Budget } from '../budgets';
  import { iconeCategorie, messageErreur, montantLisible } from '../budgets';
  import type { ChargerPage, Depense } from '../dashboard';
  import { centimes, montantDepuisCentimes, partPourMille, repartir, toutesLesDepenses } from '../dashboard';

  type Props = {
    loadBudgets: (mois: string) => Promise<Budget[]>;
    loadExpensePage: ChargerPage;
  };
  let { loadBudgets, loadExpensePage }: Props = $props();
  const maintenant = new Date();
  let mois = $state(`${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`);
  let budgets = $state<Budget[]>([]);
  let depenses = $state<Depense[]>([]);
  let chargement = $state(true);
  let erreur = $state('');
  let generation = 0;
  let synthese = $derived(repartir(depenses));
  let total = $derived(montantDepuisCentimes(synthese.total));
  let alertes = $derived(budgets.filter(budget => budget.statut !== 'ok'));
  let plafonds = $derived(montantDepuisCentimes(budgets.reduce((somme, budget) => somme + centimes(budget.montant_limite), 0n)));
  let marge = $derived(montantDepuisCentimes(budgets.reduce((somme, budget) => somme + centimes(budget.reste), 0n)));

  const couleurs: Record<string, string> = {
    Alimentation: '#8FAF79', Factures: '#F1CA72', Loisirs: '#DF7059', Transport: '#74BDE8',
    Santé: '#B99B72', Autre: '#A78FBE',
  };

  let secteurs = $derived.by(() => {
    let position = 0;
    return synthese.categories.map(item => {
      const part = partPourMille(item.total, synthese.total) / 10;
      const depart = position;
      position += part;
      return { ...item, part, depart, couleur: couleurs[item.categorie.nom] ?? '#B99B72' };
    });
  });
  let fondCamembert = $derived(secteurs.length
    ? `conic-gradient(${secteurs.map(item => `${item.couleur} ${item.depart}% ${item.depart + item.part}%`).join(', ')})`
    : '#eee8dc');

  let courbe = $derived.by(() => {
    if (depenses.length === 0) return '';
    const jours = new Map<string, bigint>();
    for (const depense of depenses) {
      const valeur = centimes(depense.montant);
      jours.set(depense.date_depense, (jours.get(depense.date_depense) ?? 0n) + valeur);
    }
    const dates = [...jours.keys()].sort();
    let cumul = 0n;
    const points = dates.map(date => { cumul += jours.get(date) ?? 0n; return cumul; });
    const maximum = points.at(-1) ?? 0n;
    if (points.length === 1) return 'M 0 100 L 100 0';
    return points.map((value, index) => {
      const x = dates.length === 1 ? 0 : Math.round(index * 1000 / (dates.length - 1)) / 10;
      const y = maximum === 0n ? 100 : 100 - Number(value * 1000n / maximum) / 10;
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  });

  async function actualiser() {
    const courante = ++generation;
    chargement = true; erreur = ''; budgets = []; depenses = [];
    try {
      const [budgetResult, depenseResult] = await Promise.all([
        loadBudgets(mois), toutesLesDepenses(mois, loadExpensePage),
      ]);
      if (courante === generation) { budgets = budgetResult; depenses = depenseResult; }
    } catch (cause) {
      if (courante === generation) erreur = messageErreur(cause);
    } finally {
      if (courante === generation) chargement = false;
    }
  }

  function changerMois(event: Event) {
    mois = (event.currentTarget as HTMLInputElement).value;
    void actualiser();
  }
  onMount(() => { void actualiser(); });
</script>

<section class="dashboard cashmire-page" aria-label="Tableau de bord mensuel" aria-busy={chargement}>
  <div class="cashmire-shell">
  <header class="topbar cashmire-card"><div class="brand"><img class="cashmire-logo-image" src="/assets/cashmire/logo-emblem.png" alt="" /><strong>Cashmire</strong></div><div class="controls"><label for="dashboard-mois">Mois</label><input id="dashboard-mois" type="month" value={mois} onchange={changerMois} /><button class="cashmire-secondary-action" type="button" onclick={actualiser} disabled={chargement}>Actualiser</button></div></header>
  {#if erreur}<div class="notice error" role="alert">{erreur} <button type="button" onclick={actualiser}>Réessayer</button></div>{/if}
  {#if chargement}<p role="status">Chargement du tableau de bord…</p>
  {:else if !erreur}
    <section class="hero cashmire-hero">
      <img class="cashmire-hero-media" src="/assets/cashmire/hero-village.png" alt="" />
      <div class="hero-content"><p class="eyebrow">Votre mois en un regard</p><h1>Des budgets bien construits.</h1><p>Chaque dépense trouve sa place.</p></div>
      <div class="indicators"><div><span>Dépensé</span><strong>{montantLisible(total)}</strong></div><div><span>Plafonds</span><strong>{montantLisible(plafonds)}</strong></div><div><span>Marge restante</span><strong>{montantLisible(marge)}</strong></div></div>
    </section>

    {#if depenses.length === 0 && budgets.length === 0}<p class="panel empty">Aucune dépense ni budget pour ce mois. Ajoutez vos premières données depuis les pages dédiées.</p>{/if}
    <div class="charts">
      <section class="panel cashmire-card"><h2>Dépenses cumulées</h2>{#if depenses.length === 0}<p>Aucune dépense à représenter.</p>{:else}<div class="chart-wrap"><svg class="line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Courbe des dépenses cumulées du mois"><path d={courbe} fill="none" stroke="#2C4939" stroke-width="2" vector-effect="non-scaling-stroke"/></svg><strong class="chart-total">{montantLisible(total)}</strong></div><p class="chart-caption">{depenses.length} dépense{depenses.length > 1 ? 's' : ''} prise{depenses.length > 1 ? 's' : ''} en compte</p>{/if}</section>
      <section class="panel cashmire-card"><h2>Répartition des dépenses</h2>{#if depenses.length === 0}<p>Aucune catégorie dépensée.</p>{:else}<div class="pie-row"><div class="pie" style:background={fondCamembert} role="img" aria-label="Répartition des dépenses par catégorie"><span>{montantLisible(total)}</span></div><ul>{#each secteurs as secteur (secteur.categorie.id)}<li><span class="swatch" style:background={secteur.couleur}></span><span>{secteur.categorie.nom}</span><strong>{montantLisible(montantDepuisCentimes(secteur.total))}</strong><small>{Math.round(secteur.part)} %</small></li>{/each}</ul></div>{/if}</section>
    </div>
    <section class="panel cashmire-card" aria-labelledby="dashboard-budgets"><div class="section-heading"><h2 id="dashboard-budgets">Mes budgets</h2>{#if alertes.length}<span class="alert-count">{alertes.length} alerte{alertes.length > 1 ? 's' : ''}</span>{/if}</div>{#if budgets.length === 0}<p>Aucun budget pour ce mois.</p>{:else}<div class="budget-grid">{#each budgets as budget (budget.id)}<article class="budget-card"><div class="card-heading"><div class="category-heading">{#if iconeCategorie(budget.categorie.nom)}<img class="cashmire-category-icon" src={iconeCategorie(budget.categorie.nom) ?? ''} alt="" />{/if}<h3>{budget.categorie.nom}</h3></div><strong>{budget.pourcentage} %</strong></div><p><strong>{montantLisible(budget.depense)}</strong> / {montantLisible(budget.montant_limite)}</p><progress max="100" value={Math.min(budget.pourcentage, 100)} aria-label={`Consommation de ${budget.categorie.nom}`}></progress><div class="card-footer"><span class:cashmire-status-ok={budget.statut === 'ok'} class:cashmire-status-warning={budget.statut === 'attention'} class:cashmire-status-exceeded={budget.statut === 'depasse'}>{budget.statut === 'ok' ? 'Dans le budget' : budget.statut === 'attention' ? 'Attention' : 'Dépassé'}</span><span class="budget-detail">{budget.reste.startsWith('-') ? `${montantLisible(budget.reste.slice(1))} au-dessus de la limite` : `${montantLisible(budget.reste)} disponibles`}</span></div>{#if budget.statut === 'attention'}<p class="alert-text">Le seuil de {budget.seuil_alerte_pct} % est atteint.</p>{:else if budget.statut === 'depasse'}<p class="alert-text">La limite est dépassée.</p>{/if}</article>{/each}</div>{/if}</section>
    <section class="panel cashmire-card" aria-labelledby="dashboard-depenses"><h2 id="dashboard-depenses">Dernières dépenses</h2>{#if depenses.length === 0}<p>Aucune dépense pour ce mois.</p>{:else}<ul class="expenses">{#each depenses.slice(0, 5) as depense (depense.id)}<li><span class="expense-name">{#if iconeCategorie(depense.categorie.nom)}<img src={iconeCategorie(depense.categorie.nom) ?? ''} alt="" />{/if}<span><strong>{depense.libelle}</strong><small>{depense.categorie.nom} · {depense.date_depense}</small></span></span><strong>{montantLisible(depense.montant)}</strong></li>{/each}</ul>{/if}</section>
  {/if}
  </div>
</section>

<style>
  .dashboard * { box-sizing: border-box; }
  .topbar, .brand, .controls, .indicators, .pie-row, .section-heading, .card-heading, .category-heading, .card-footer { display: flex; align-items: center; gap: 16px; }
  .topbar { justify-content: space-between; padding: 12px 20px; margin-bottom: 16px; }
  .brand { gap: 8px; }
  .brand strong { font: 700 27px/1 var(--story-font); }
  .controls label { font-weight: 700; }
  .dashboard input { min-height: 44px; border: 1px solid var(--border); border-radius: 10px; padding: 8px 12px; color: var(--ink); background: #fff; font: inherit; }
  .dashboard button:disabled { opacity: .55; }
  .dashboard :focus-visible { outline: 3px solid #754a0b; outline-offset: 3px; }
  .hero { position: relative; display: flex; flex-direction: column; justify-content: space-between; padding: clamp(24px, 3vw, 40px); margin-bottom: 16px; }
  .hero-content { width: min(48%, 550px); }
  .hero h1 { font: 700 clamp(32px, 4vw, 48px)/1.15 var(--story-font); margin: 4px 0 8px; }
  .hero p { margin: 0; }
  .eyebrow { color: #765d3b; font-weight: 700; }
  .indicators { align-items: stretch; flex-wrap: wrap; gap: 8px; }
  .indicators div { display: flex; flex-direction: column; justify-content: center; min-width: 150px; padding: 10px 16px; border: 1px solid color-mix(in srgb, var(--border) 75%, white); border-radius: 12px; background: #fffcf5ed; box-shadow: 0 2px 6px #2c493917; }
  .indicators span { font-size: 13px; }
  .indicators strong { font-size: 23px; line-height: 1.2; font-variant-numeric: tabular-nums; }
  .charts { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; margin-bottom: 16px; }
  .panel { margin-bottom: 16px; }
  .charts .panel { margin: 0; }
  .panel h2, .panel h3 { font-family: var(--story-font); line-height: 1.2; }
  .panel h2 { font-size: 25px; margin: 0 0 16px; }
  .panel h2::before { content: '🌿'; margin-right: 8px; font: 18px var(--body-font); }
  .panel h3 { font-size: 20px; margin: 0; }
  .chart-wrap { position: relative; padding: 18px 10px 0; }
  .line-chart { width: 100%; height: 210px; overflow: visible; background: repeating-linear-gradient(to bottom, transparent 0, transparent 49px, #e8e1d6 50px); border-left: 1px solid var(--border); border-bottom: 1px solid var(--border); }
  .chart-total { position: absolute; right: 8px; top: 0; font-variant-numeric: tabular-nums; }
  .chart-caption { color: #55695c; font-size: 13px; }
  .pie-row { align-items: center; }
  .pie { width: 190px; height: 190px; display: grid; place-items: center; flex: none; border-radius: 50%; border: 1px solid var(--border); }
  .pie span { display: grid; place-items: center; width: 54%; height: 54%; border-radius: 50%; background: var(--ivory); font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .pie-row ul { list-style: none; padding: 0; margin: 0; flex: 1; min-width: 0; }
  .pie-row li { display: grid; grid-template-columns: 12px minmax(0, 1fr) auto auto; align-items: center; gap: 8px; font-size: 13px; padding: 5px 0; }
  .pie-row li strong { font-variant-numeric: tabular-nums; white-space: nowrap; }
  .pie-row li small { color: #526456; }
  .swatch { width: 12px; height: 12px; border-radius: 50%; }
  .section-heading { justify-content: space-between; }
  .alert-count { padding: 6px 10px; border-radius: 999px; color: #754a0b; background: #fff0cd; font-size: 13px; font-weight: 700; }
  .budget-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  .budget-card { min-width: 0; border: 1px solid #e3d0b7; border-radius: 12px; padding: 14px; background: #fffdf8; }
  .card-heading { justify-content: space-between; align-items: flex-start; gap: 4px; }
  .category-heading { min-width: 0; gap: 5px; }
  .category-heading h3 { overflow-wrap: anywhere; }
  .budget-card .cashmire-category-icon { width: 52px; height: 52px; }
  .card-heading > strong { white-space: nowrap; font-variant-numeric: tabular-nums; }
  .budget-card p { margin: 7px 0; }
  .budget-card p strong { font-variant-numeric: tabular-nums; }
  .budget-card progress { width: 100%; height: 12px; accent-color: var(--sage); }
  .budget-card:has(.cashmire-status-warning) progress { accent-color: var(--straw); }
  .budget-card:has(.cashmire-status-exceeded) progress { accent-color: var(--brick); }
  .card-footer { justify-content: space-between; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
  .budget-detail, .alert-text { font-size: 13px; }
  .alert-text { font-weight: 700; }
  .expenses { list-style: none; padding: 0; margin: 0; }
  .expenses li { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 8px 0; border-bottom: 1px solid #e3d0b7; }
  .expenses li > strong { white-space: nowrap; font-variant-numeric: tabular-nums; }
  .expense-name { display: flex; align-items: center; gap: 8px; }
  .expense-name img { width: 36px; height: 36px; object-fit: contain; }
  .expense-name span { display: grid; }
  .expenses small { color: #765d3b; }
  .notice { padding: 16px; border-radius: 12px; margin-bottom: 16px; }
  .error { background: #fce5dd; color: #922514; }
  .empty { border-style: dashed; }
  :global(.cashmire-status-ok)::before { content: '✓'; }
  :global(.cashmire-status-warning)::before { content: '⚠'; }
  :global(.cashmire-status-exceeded)::before { content: '✕'; }
  @media (max-width: 1100px) {
    .budget-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .pie-row { flex-wrap: wrap; }
  }
  @media (max-width: 767px) {
    .topbar { padding: 10px 14px; flex-wrap: wrap; }
    .brand strong { font-size: 24px; }
    .controls { width: 100%; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
    .hero { display: block; padding: 0; }
    .hero-content { width: 100%; padding: 16px 20px 6px; text-align: center; }
    .hero h1 { font-size: 28px; }
    .indicators { padding: 10px; flex-wrap: nowrap; }
    .indicators div { flex: 1; min-width: 0; padding: 8px 5px; align-items: center; }
    .indicators span { font-size: 11px; text-align: center; }
    .indicators strong { font-size: 16px; }
    .charts { grid-template-columns: 1fr; gap: 16px; }
    .pie-row { flex-wrap: nowrap; }
    .pie { width: 42vw; height: 42vw; max-width: 190px; max-height: 190px; }
    .pie span { font-size: 17px; }
    .budget-grid { grid-template-columns: 1fr; }
    .panel h2 { font-size: 22px; }
  }
  @media (max-width: 420px) {
    .pie-row { flex-wrap: wrap; justify-content: center; }
    .pie-row ul { width: 100%; }
  }
</style>
