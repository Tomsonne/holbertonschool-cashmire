<script lang="ts">
  import { onMount } from 'svelte';
  import type { Budget, Categorie, ErreurApi } from '../budgets';
  import { messageErreur, montantLisible } from '../budgets';

  type Props = {
    categories: Categorie[];
    loadBudgets: (mois: string) => Promise<Budget[]>;
    createBudget: (data: { categorie_id: string; montant_limite: string; mois: string; seuil_alerte_pct: number }) => Promise<Budget>;
    updateBudget: (id: string, data: { montant_limite: string; seuil_alerte_pct: number }) => Promise<Budget>;
    deleteBudget: (id: string) => Promise<void>;
  };

  let { categories, loadBudgets, createBudget, updateBudget, deleteBudget }: Props = $props();
  const aujourdHui = new Date();
  let mois = $state(`${aujourdHui.getFullYear()}-${String(aujourdHui.getMonth() + 1).padStart(2, '0')}`);
  let budgets = $state<Budget[]>([]);
  let chargement = $state(true);
  let attente = $state(false);
  let erreur = $state('');
  let succes = $state('');
  let champs = $state<Record<string, string>>({});
  let categorieId = $state('');
  let limite = $state('');
  let seuil = $state(80);
  let edition = $state<string | null>(null);
  let confirmation = $state<string | null>(null);
  let generation = 0;
  let disponibles = $derived(categories.filter(categorie => !budgets.some(budget => budget.categorie.id === categorie.id)));

  async function recharger() {
    const courante = ++generation;
    chargement = true;
    budgets = [];
    erreur = '';
    try {
      const resultat = await loadBudgets(mois);
      if (courante === generation) budgets = resultat;
    } catch (cause) {
      if (courante === generation) erreur = messageErreur(cause);
    } finally {
      if (courante === generation) chargement = false;
    }
  }

  function changerMois(event: Event) {
    mois = (event.currentTarget as HTMLInputElement).value;
    edition = null;
    confirmation = null;
    succes = '';
    void recharger();
  }

  function afficherErreur(cause: unknown) {
    erreur = messageErreur(cause);
    champs = (cause as ErreurApi)?.champs ?? {};
  }

  async function creer(event: SubmitEvent) {
    event.preventDefault();
    if (!categorieId) { champs = { categorie_id: 'Choisissez une catégorie.' }; return; }
    attente = true; erreur = ''; succes = ''; champs = {};
    try {
      await createBudget({ categorie_id: categorieId, montant_limite: limite.replace(',', '.'), mois, seuil_alerte_pct: seuil });
      categorieId = ''; limite = ''; seuil = 80;
      succes = 'Budget créé.';
      await recharger();
    } catch (cause) { afficherErreur(cause); }
    finally { attente = false; }
  }

  function commencerEdition(budget: Budget) {
    edition = budget.id;
    confirmation = null;
    limite = budget.montant_limite;
    seuil = budget.seuil_alerte_pct;
    erreur = ''; champs = {};
  }

  async function modifier(event: SubmitEvent, id: string) {
    event.preventDefault();
    attente = true; erreur = ''; succes = ''; champs = {};
    try {
      await updateBudget(id, { montant_limite: limite.replace(',', '.'), seuil_alerte_pct: seuil });
      edition = null; limite = ''; seuil = 80;
      succes = 'Budget modifié.';
      await recharger();
    } catch (cause) { afficherErreur(cause); }
    finally { attente = false; }
  }

  async function supprimer(id: string) {
    attente = true; erreur = ''; succes = '';
    try {
      await deleteBudget(id);
      confirmation = null;
      succes = 'Budget supprimé. Les dépenses sont conservées.';
      await recharger();
    } catch (cause) { afficherErreur(cause); }
    finally { attente = false; }
  }

  onMount(() => { void recharger(); });
</script>

<section class="budget-page" aria-label="Gestion des budgets">
  <div class="page-heading">
    <div><p class="eyebrow">La maison des budgets</p><h1>Mes budgets</h1><p>Une limite pour chaque catégorie, mois après mois.</p></div>
    <label>Mois <input type="month" value={mois} onchange={changerMois} required /></label>
  </div>

  <div class="budget-layout">
    <section class="card" aria-labelledby="budget-form-title">
      <h2 id="budget-form-title">Construire un budget</h2>
      {#if categories.length === 0}
        <p role="status">Les catégories ne sont pas disponibles. Réessayez après leur chargement.</p>
      {:else}
        <form onsubmit={creer}>
          <label for="categorie">Catégorie</label>
          <select id="categorie" bind:value={categorieId} required disabled={attente || disponibles.length === 0} aria-invalid={Boolean(champs.categorie_id)}>
            <option value="">Choisir une catégorie</option>
            {#each disponibles as categorie (categorie.id)}<option value={categorie.id}>{categorie.nom}</option>{/each}
          </select>
          {#if champs.categorie_id}<p class="field-error">{champs.categorie_id}</p>{/if}
          {#if disponibles.length === 0}<p>Toutes les catégories ont déjà un budget ce mois.</p>{/if}
          <label for="limite">Limite mensuelle (€)</label>
          <input id="limite" type="text" inputmode="decimal" pattern={'[0-9]{1,10}([.,][0-9]{1,2})?'} bind:value={limite} placeholder="300,00" required disabled={attente} aria-invalid={Boolean(champs.montant_limite)} />
          {#if champs.montant_limite}<p class="field-error">{champs.montant_limite}</p>{/if}
          <label for="seuil">Seuil d’alerte (%)</label>
          <input id="seuil" type="number" min="1" max="100" bind:value={seuil} required disabled={attente} aria-invalid={Boolean(champs.seuil_alerte_pct)} />
          {#if champs.seuil_alerte_pct}<p class="field-error">{champs.seuil_alerte_pct}</p>{/if}
          <button type="submit" disabled={attente || disponibles.length === 0}>Créer le budget</button>
        </form>
      {/if}
    </section>

    <section class="budget-list" aria-labelledby="budget-list-title" aria-busy={chargement}>
      <div class="list-heading"><h2 id="budget-list-title">Budgets du mois</h2><button class="secondary" type="button" onclick={recharger} disabled={chargement || attente}>Actualiser</button></div>
      {#if erreur}<p class="notice error" role="alert">{erreur}</p>{/if}
      {#if succes}<p class="notice success" role="status">{succes}</p>{/if}
      {#if chargement}<p role="status">Chargement des budgets…</p>
      {:else if budgets.length === 0}<p class="card empty">Aucun budget pour ce mois. Choisissez une catégorie pour commencer.</p>
      {:else}
        {#each budgets as budget (budget.id)}
          <article class="card budget-item">
            <div class="item-heading"><h3>{budget.categorie.nom}</h3><span class:ok={budget.statut === 'ok'} class:attention={budget.statut === 'attention'} class:depasse={budget.statut === 'depasse'} class="badge">{budget.statut === 'ok' ? 'Dans le budget' : budget.statut === 'attention' ? 'Attention' : 'Dépassé'}</span></div>
            <p class="amount">{montantLisible(budget.depense)} <small>sur {montantLisible(budget.montant_limite)}</small></p>
            <progress max="100" value={Math.min(budget.pourcentage, 100)} aria-label={`Consommation de ${budget.categorie.nom}`}></progress>
            <p class="details">{budget.pourcentage} % consommés · {budget.reste.startsWith('-') ? `${montantLisible(budget.reste.slice(1))} dépassés` : `${montantLisible(budget.reste)} restants`} · alerte à {budget.seuil_alerte_pct} %</p>
            {#if edition === budget.id}
              <form onsubmit={(event) => modifier(event, budget.id)}>
                <label for={`limite-${budget.id}`}>Nouvelle limite (€)</label><input id={`limite-${budget.id}`} type="text" inputmode="decimal" pattern={'[0-9]{1,10}([.,][0-9]{1,2})?'} bind:value={limite} required aria-invalid={Boolean(champs.montant_limite)} />
                {#if champs.montant_limite}<p class="field-error">{champs.montant_limite}</p>{/if}
                <label for={`seuil-${budget.id}`}>Nouveau seuil (%)</label><input id={`seuil-${budget.id}`} type="number" min="1" max="100" bind:value={seuil} required aria-invalid={Boolean(champs.seuil_alerte_pct)} />
                {#if champs.seuil_alerte_pct}<p class="field-error">{champs.seuil_alerte_pct}</p>{/if}
                <div class="actions"><button type="submit" disabled={attente}>Enregistrer</button><button class="secondary" type="button" onclick={() => edition = null}>Annuler</button></div>
              </form>
            {:else if confirmation === budget.id}
              <p>Supprimer ce budget ? Les dépenses resteront enregistrées.</p>
              <div class="actions"><button class="danger" type="button" onclick={() => supprimer(budget.id)} disabled={attente}>Confirmer la suppression</button><button class="secondary" type="button" onclick={() => confirmation = null}>Annuler</button></div>
            {:else}
              <div class="actions"><button class="secondary" type="button" onclick={() => commencerEdition(budget)}>Modifier</button><button class="secondary" type="button" onclick={() => confirmation = budget.id}>Supprimer</button></div>
            {/if}
          </article>
        {/each}
      {/if}
    </section>
  </div>
</section>

<style>
  .budget-page{color:var(--ink);background:var(--cream);padding:24px;font:16px/1.5 system-ui,sans-serif;min-height:100vh}
  .budget-page *{box-sizing:border-box}.page-heading,.list-heading,.item-heading,.actions{display:flex;justify-content:space-between;align-items:center;gap:16px}.page-heading{max-width:1200px;margin:auto auto 24px}.page-heading p{margin:0}.eyebrow{color:#765D3B;font-weight:700}.budget-page h1,.budget-page h2,.budget-page h3{font-family:Georgia,serif}.budget-page h1{font-size:clamp(28px,4vw,36px);margin:4px 0}.budget-page h2{font-size:24px;margin:0 0 16px}.budget-page h3{font-size:20px;margin:0}.budget-layout{max-width:1200px;margin:auto;display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:24px;align-items:start}.card{background:var(--ivory);border:1px solid var(--border);border-radius:16px;padding:24px;box-shadow:0 4px 16px #2c493910}.budget-list{display:grid;gap:16px}.budget-item p{margin:12px 0}.amount{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}.amount small{font-size:14px;font-weight:400}.badge{border-radius:100px;padding:4px 10px;font-size:13px;font-weight:700}.badge.ok{background:#DFEED7}.badge.attention{background:#FBE6A8}.badge.depasse{background:#F9D8CE}.details{font-size:14px}.budget-page label{display:block;font-weight:700;margin:12px 0 4px}.budget-page input,.budget-page select{width:100%;min-height:44px;padding:8px 12px;border:1px solid var(--border);border-radius:10px;background:#fff;color:var(--ink);font:inherit}.page-heading input{width:auto}.budget-page button{min-height:44px;border:0;border-radius:10px;padding:8px 16px;background:var(--ink);color:#fff;font:700 14px system-ui;cursor:pointer}.budget-page button.secondary{border:1px solid var(--border);background:var(--ivory);color:var(--ink)}.budget-page button.danger{background:#A52E1D}.budget-page button:disabled{opacity:.55;cursor:not-allowed}.budget-page :focus-visible{outline:3px solid #186a9b;outline-offset:3px}.budget-page form>button{margin-top:20px}.actions{justify-content:flex-start;flex-wrap:wrap}.budget-page progress{width:100%;height:12px;accent-color:var(--sage)}.notice{border-radius:12px;padding:12px}.error,.field-error{color:#922514}.error{background:#FCE5DD}.success{background:#E4F0DE}.empty{border-style:dashed}@media(max-width:720px){.budget-page{padding:16px}.page-heading{display:block}.page-heading input{width:100%}.budget-layout{grid-template-columns:1fr;gap:16px}.card{padding:16px}.list-heading{align-items:flex-start}.amount{font-size:22px}}
</style>
