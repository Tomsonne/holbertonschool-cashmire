<script lang="ts">
  import { onMount } from 'svelte';
  import type { Budget } from '../budgets';
  import { messageErreur, montantLisible } from '../budgets';
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

<section class="dashboard" aria-label="Tableau de bord mensuel" aria-busy={chargement}>
  <header class="topbar"><strong class="brand">Cashmire</strong><div class="controls"><label for="dashboard-mois">Mois</label><input id="dashboard-mois" type="month" value={mois} onchange={changerMois} /><button type="button" onclick={actualiser} disabled={chargement}>Actualiser</button></div></header>
  {#if erreur}<div class="notice error" role="alert">{erreur} <button type="button" onclick={actualiser}>Réessayer</button></div>{/if}
  {#if chargement}<p role="status">Chargement du tableau de bord…</p>
  {:else if !erreur}
    <section class="hero">
      <div><p class="eyebrow">Votre mois en un regard</p><h1>Des budgets bien construits.</h1><p>Chaque dépense trouve sa place.</p><div class="indicators"><div><strong>{montantLisible(total)}</strong><span>Dépenses du mois</span></div><div><strong>{budgets.length}</strong><span>Budgets</span></div><div><strong>{alertes.length}</strong><span>Alertes</span></div></div></div>
      <svg class="houses" viewBox="0 0 360 170" role="img" aria-label="Trois petits cochons devant leurs maisons de paille, de bois et de briques">
        <rect x="0" y="128" width="360" height="42" rx="18" fill="#8FAF79" opacity=".45"/>
        <g><path d="M15 80 L60 30 L105 80Z" fill="#F1CA72" stroke="#876B3E" stroke-width="3"/><rect x="25" y="80" width="70" height="58" rx="4" fill="#F7DC9B" stroke="#876B3E" stroke-width="3"/><path d="M38 95l40 30M78 95l-40 30" stroke="#C79A49" stroke-width="3"/><circle cx="60" cy="116" r="13" fill="#F4A9A1"/><path d="M47 105l-5-10 10 3M73 105l5-10-10 3" fill="#F4A9A1"/><ellipse cx="60" cy="120" rx="6" ry="4" fill="#DF807E"/><circle cx="55" cy="113" r="1.5"/><circle cx="65" cy="113" r="1.5"/><path d="M44 101h32" stroke="#B28B3B" stroke-width="6"/></g>
        <g><path d="M126 80 L180 23 L234 80Z" fill="#B99B72" stroke="#76583C" stroke-width="3"/><rect x="138" y="80" width="84" height="58" rx="4" fill="#D1AD7C" stroke="#76583C" stroke-width="3"/><path d="M153 80v58M180 80v58M207 80v58" stroke="#9E764E" stroke-width="4"/><circle cx="180" cy="116" r="13" fill="#F4A9A1"/><path d="M167 105l-5-10 10 3M193 105l5-10-10 3" fill="#F4A9A1"/><ellipse cx="180" cy="120" rx="6" ry="4" fill="#DF807E"/><circle cx="175" cy="113" r="1.5"/><circle cx="185" cy="113" r="1.5"/><path d="M169 128h22" stroke="#74BDE8" stroke-width="7"/></g>
        <g><path d="M250 80 L300 25 L350 80Z" fill="#DF7059" stroke="#874335" stroke-width="3"/><rect x="260" y="80" width="80" height="58" rx="4" fill="#E9957B" stroke="#874335" stroke-width="3"/><path d="M260 100h80M260 120h80M280 80v20M320 80v20M300 100v20" stroke="#B75F4C" stroke-width="3"/><circle cx="300" cy="116" r="13" fill="#F4A9A1"/><path d="M287 105l-5-10 10 3M313 105l5-10-10 3" fill="#F4A9A1"/><ellipse cx="300" cy="120" rx="6" ry="4" fill="#DF807E"/><circle cx="295" cy="113" r="1.5"/><circle cx="305" cy="113" r="1.5"/><path d="M288 128h24" stroke="#C8634D" stroke-width="7"/></g>
      </svg>
    </section>

    {#if depenses.length === 0 && budgets.length === 0}<p class="panel empty">Aucune dépense ni budget pour ce mois. Ajoutez vos premières données depuis les pages dédiées.</p>{/if}
    <div class="charts">
      <section class="panel"><h2>Dépenses cumulées</h2>{#if depenses.length === 0}<p>Aucune dépense à représenter.</p>{:else}<svg class="line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Courbe des dépenses cumulées du mois"><path d={courbe} fill="none" stroke="#2C4939" stroke-width="2" vector-effect="non-scaling-stroke"/></svg><p>{depenses.length} dépense{depenses.length > 1 ? 's' : ''} prise{depenses.length > 1 ? 's' : ''} en compte</p>{/if}</section>
      <section class="panel"><h2>Répartition par catégorie</h2>{#if depenses.length === 0}<p>Aucune catégorie dépensée.</p>{:else}<div class="pie-row"><div class="pie" style:background={fondCamembert} role="img" aria-label="Répartition des dépenses par catégorie"></div><ul>{#each secteurs as secteur (secteur.categorie.id)}<li><span class="swatch" style:background={secteur.couleur}></span><span>{secteur.categorie.nom}</span><strong>{montantLisible(montantDepuisCentimes(secteur.total))}</strong></li>{/each}</ul></div>{/if}</section>
    </div>
    <section class="panel" aria-labelledby="dashboard-budgets"><h2 id="dashboard-budgets">Budgets et alertes</h2>{#if budgets.length === 0}<p>Aucun budget pour ce mois.</p>{:else}<div class="budget-grid">{#each budgets as budget (budget.id)}<article class="budget-card"><div class="card-heading"><h3>{budget.categorie.nom}</h3><span class:ok={budget.statut === 'ok'} class:attention={budget.statut === 'attention'} class:depasse={budget.statut === 'depasse'} class="badge">{budget.statut === 'ok' ? 'Dans le budget' : budget.statut === 'attention' ? 'Attention' : 'Dépassé'}</span></div><p><strong>{montantLisible(budget.depense)}</strong> sur {montantLisible(budget.montant_limite)}</p><progress max="100" value={Math.min(budget.pourcentage, 100)} aria-label={`Consommation de ${budget.categorie.nom}`}></progress><p class="budget-detail">{budget.pourcentage} % · {budget.reste.startsWith('-') ? `${montantLisible(budget.reste.slice(1))} au-dessus de la limite` : `${montantLisible(budget.reste)} disponibles`}</p>{#if budget.statut === 'attention'}<p class="alert-text">Le seuil de {budget.seuil_alerte_pct} % est atteint.</p>{:else if budget.statut === 'depasse'}<p class="alert-text">La limite est dépassée.</p>{/if}</article>{/each}</div>{/if}</section>
    <section class="panel" aria-labelledby="dashboard-depenses"><h2 id="dashboard-depenses">Dernières dépenses</h2>{#if depenses.length === 0}<p>Aucune dépense pour ce mois.</p>{:else}<ul class="expenses">{#each depenses.slice(0, 5) as depense (depense.id)}<li><span><strong>{depense.libelle}</strong><small>{depense.categorie.nom} · {depense.date_depense}</small></span><strong>{montantLisible(depense.montant)}</strong></li>{/each}</ul>{/if}</section>
  {/if}
</section>

<style>
  .dashboard{background:var(--cream);color:var(--ink);min-height:100vh;padding:24px;max-width:1400px;margin:auto;font:16px/1.5 system-ui,sans-serif}.dashboard *{box-sizing:border-box}.topbar,.controls,.indicators,.card-heading,.pie-row{display:flex;align-items:center;gap:16px}.topbar{justify-content:space-between;margin-bottom:24px}.brand,h1,h2,h3{font-family:Georgia,serif}.brand{font-size:24px}.controls label{font-weight:700}.dashboard input{min-height:44px;border:1px solid var(--border);border-radius:10px;padding:8px;color:var(--ink);background:#fff;font:inherit}.dashboard button{min-height:44px;border:0;border-radius:10px;padding:8px 16px;background:var(--ink);color:#fff;font:700 14px system-ui;cursor:pointer}.dashboard button:disabled{opacity:.55}.dashboard :focus-visible{outline:3px solid #186a9b;outline-offset:3px}.hero,.panel{background:var(--ivory);border:1px solid var(--border);border-radius:16px;box-shadow:0 4px 16px #2c493910}.hero{display:grid;grid-template-columns:1fr 360px;align-items:end;gap:16px;padding:24px;margin-bottom:24px;background:linear-gradient(120deg,#FFF6DF,var(--ivory))}.hero h1{font-size:clamp(28px,4vw,36px);margin:4px 0}.hero p{margin:0}.eyebrow{font-weight:700;color:#765D3B}.indicators{margin-top:24px;flex-wrap:wrap}.indicators div{display:grid;padding-right:16px;border-right:1px solid var(--border)}.indicators strong{font-size:22px;font-variant-numeric:tabular-nums}.indicators span{font-size:13px}.houses{width:100%;height:auto}.charts{display:grid;grid-template-columns:3fr 2fr;gap:24px;margin-bottom:24px}.panel{padding:24px;margin-bottom:24px}.charts .panel{margin:0}.panel h2{font-size:24px;margin:0 0 16px}.line-chart{width:100%;height:210px;background:repeating-linear-gradient(to bottom,#fff 0,#fff 49px,#eadfce 50px);border-left:1px solid var(--border);border-bottom:1px solid var(--border)}.pie{width:170px;height:170px;flex:none;border-radius:50%;border:1px solid var(--border)}.pie-row ul{list-style:none;padding:0;flex:1}.pie-row li{display:flex;align-items:center;gap:8px;font-size:14px;padding:5px 0}.pie-row li strong{margin-left:auto;font-variant-numeric:tabular-nums}.swatch{width:12px;height:12px;border-radius:4px;flex:none}.budget-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.budget-card{border:1px solid #E3D0B7;border-radius:12px;padding:16px;background:#fff}.card-heading{justify-content:space-between;align-items:start}.budget-card h3{margin:0}.budget-card strong{font-variant-numeric:tabular-nums}.badge{padding:3px 8px;border-radius:100px;font-size:12px;font-weight:700;white-space:nowrap}.badge.ok{background:#DFEED7}.badge.attention{background:#FBE6A8}.badge.depasse{background:#F9D8CE}.budget-card progress{width:100%;accent-color:var(--sage)}.budget-detail,.alert-text{font-size:14px}.alert-text{font-weight:700}.expenses{list-style:none;padding:0;margin:0}.expenses li{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid #E3D0B7}.expenses li span{display:grid}.expenses small{color:#765D3B}.notice{padding:16px;border-radius:12px;margin-bottom:16px}.error{background:#FCE5DD;color:#922514}.empty{border-style:dashed}@media(max-width:800px){.dashboard{padding:16px}.hero{grid-template-columns:1fr}.houses{max-width:360px}.charts{grid-template-columns:1fr;gap:16px}.panel{padding:16px;margin-bottom:16px}.topbar{align-items:start}.controls{flex-wrap:wrap}.pie-row{flex-wrap:wrap}.expenses li{align-items:start}}
</style>
