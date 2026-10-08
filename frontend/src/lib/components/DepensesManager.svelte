<script lang="ts">
  import { onMount } from 'svelte';
  import type { FiltresDepenses } from '../api/depenses';
  import type { Categorie } from '../budgets';
  import { iconeCategorie, montantLisible } from '../budgets';
  import type { Depense, PageDepenses } from '../dashboard';
  import type { DepenseFormulaire } from '../depenses';
  import { dateIso, dateLisible, messageErreurDepense } from '../depenses';
  import DepenseForm from './DepenseForm.svelte';

  type Props = {
    categories: Categorie[];
    loadDepenses: (filtres: FiltresDepenses) => Promise<PageDepenses>;
    createDepense: (donnees: DepenseFormulaire) => Promise<Depense>;
    updateDepense: (id: string, donnees: Partial<DepenseFormulaire>) => Promise<Depense>;
    deleteDepense: (id: string) => Promise<void>;
  };

  const PAR_PAGE = 10;

  let { categories, loadDepenses, createDepense, updateDepense, deleteDepense }: Props = $props();
  let mois = $state(dateIso(new Date()).slice(0, 7));
  let categorieFiltre = $state('');
  let page = $state(0);
  let depenses = $state<Depense[]>([]);
  let total = $state(0);
  let chargement = $state(true);
  let attente = $state(false);
  let erreur = $state('');
  let succes = $state('');
  let edition = $state<string | null>(null);
  let confirmation = $state<string | null>(null);
  let generation = 0;
  let nombrePages = $derived(Math.max(1, Math.ceil(total / PAR_PAGE)));

  async function recharger() {
    const courante = ++generation;
    chargement = true;
    depenses = [];
    erreur = '';
    try {
      const resultat = await loadDepenses({
        mois, categorieId: categorieFiltre, limite: PAR_PAGE, decalage: page * PAR_PAGE,
      });
      if (courante !== generation) return;
      if (resultat.elements.length === 0 && page > 0 && resultat.total > 0) {
        page = Math.ceil(resultat.total / PAR_PAGE) - 1;
        void recharger();
        return;
      }
      depenses = resultat.elements;
      total = resultat.total;
    } catch (cause) {
      if (courante === generation) erreur = messageErreurDepense(cause);
    } finally {
      if (courante === generation) chargement = false;
    }
  }

    function reinitialiser() {
    page = 0;
    edition = null;
    confirmation = null;
    succes = '';
    void recharger();
  }

  function changerMois(event: Event) {
    const valeur = (event.currentTarget as HTMLInputElement).value;
    if (!valeur) return;
    mois = valeur;
    reinitialiser();
  }

  function changerCategorie(event: Event) {
    categorieFiltre = (event.currentTarget as HTMLSelectElement).value;
    reinitialiser();
  }

  function aller(nouvellePage: number) {
    page = Math.min(Math.max(0, nouvellePage), nombrePages - 1);
    edition = null;
    confirmation = null;
    void recharger();
  }

  async function creer(donnees: DepenseFormulaire) {
    erreur = '';
    succes = '';
    await createDepense(donnees);
    mois = donnees.date_depense.slice(0, 7);
    if (categorieFiltre && categorieFiltre !== donnees.categorie_id) categorieFiltre = '';
    page = 0;
    succes = 'Dépense ajoutée.';
    await recharger();
  }

  async function modifier(id: string, donnees: DepenseFormulaire) {
    erreur = '';
    succes = '';
    await updateDepense(id, donnees);
    edition = null;
    succes = 'Dépense modifiée.';
    await recharger();
  }

  async function supprimer(id: string) {
    attente = true;
    erreur = '';
    succes = '';
    try {
      await deleteDepense(id);
      confirmation = null;
      succes = 'Dépense supprimée.';
      await recharger();
    } catch (cause) {
      confirmation = null;
      erreur = messageErreurDepense(cause);
    } finally {
      attente = false;
    }
  }

  onMount(() => { void recharger(); });
</script>

<section class="depenses-page cashmire-page" aria-label="Gestion des dépenses">
  <div class="cashmire-shell">
    <header class="page-heading cashmire-card">
      <div class="brand"><img class="cashmire-logo-image" src="/assets/cashmire/logo-emblem.png" alt="" /><strong>Cashmire</strong></div>
      <h1>Mes dépenses</h1>
    </header>

    <div class="depenses-layout">
      <section class="cashmire-card" aria-labelledby="depense-ajout-titre">
        <h2 id="depense-ajout-titre">Ajouter une dépense</h2>
        {#if categories.length === 0}
          <p role="status">Les catégories ne sont pas disponibles. Réessayez après leur chargement.</p>
        {:else}
          <DepenseForm {categories} enregistrer={creer} />
        {/if}
      </section>

      <section aria-labelledby="depenses-liste-titre" aria-busy={chargement}>
        <div class="list-heading">
          <h2 id="depenses-liste-titre">Dépenses du mois</h2>
          <button class="cashmire-secondary-action" type="button" onclick={recharger} disabled={chargement || attente}>Actualiser</button>
        </div>

        <div class="filtres cashmire-card">
          <label>Mois <input type="month" value={mois} onchange={changerMois} required /></label>
          <label>Catégorie
            <select value={categorieFiltre} onchange={changerCategorie}>
              <option value="">Toutes</option>
              {#each categories as categorie (categorie.id)}<option value={categorie.id}>{categorie.nom}</option>{/each}
            </select>
          </label>
        </div>

        {#if erreur}<p class="notice error" role="alert">{erreur}</p>{/if}
        {#if succes}<p class="notice success" role="status">{succes}</p>{/if}

        {#if chargement}
          <p role="status">Chargement des dépenses…</p>
        {:else if !erreur}
          {#if depenses.length === 0}
            <p class="cashmire-card empty">Aucune dépense pour ces critères. Utilisez le formulaire pour ajouter la première.</p>
          {:else}
            <p class="total">{total} dépense{total > 1 ? 's' : ''}</p>
            <ul class="liste">
              {#each depenses as depense (depense.id)}
                <li class="cashmire-card depense">
                  {#if edition === depense.id}
                    <DepenseForm {categories} {depense} enregistrer={(donnees) => modifier(depense.id, donnees)} annuler={() => edition = null} />
                  {:else}
                    <div class="depense-ligne">
                      <div class="depense-infos">
                        {#if iconeCategorie(depense.categorie.nom)}<img class="cashmire-category-icon" src={iconeCategorie(depense.categorie.nom) ?? ''} alt="" />{/if}
                        <div>
                          <h3>{depense.libelle}</h3>
                          <p>{depense.categorie.nom} · {dateLisible(depense.date_depense)}</p>
                        </div>
                      </div>
                      <p class="cashmire-amount">{montantLisible(depense.montant)}</p>
                    </div>
                    {#if confirmation === depense.id}
                      <p>Supprimer « {depense.libelle} » ? Cette action est définitive.</p>
                      <div class="actions">
                        <button class="danger" type="button" onclick={() => supprimer(depense.id)} disabled={attente}>Confirmer la suppression</button>
                        <button class="cashmire-secondary-action" type="button" onclick={() => confirmation = null} disabled={attente}>Annuler</button>
                      </div>
                    {:else}
                      <div class="actions">
                        <button class="cashmire-secondary-action" type="button" aria-label={`Modifier ${depense.libelle}`} onclick={() => { edition = depense.id; confirmation = null; }}>Modifier</button>
                        <button class="cashmire-secondary-action" type="button" aria-label={`Supprimer ${depense.libelle}`} onclick={() => { confirmation = depense.id; edition = null; }}>Supprimer</button>
                      </div>
                    {/if}
                  {/if}
                </li>
              {/each}
            </ul>
            {#if nombrePages > 1}
              <nav class="pagination" aria-label="Pagination des dépenses">
                <button class="cashmire-secondary-action" type="button" onclick={() => aller(page - 1)} disabled={page === 0}>Précédent</button>
                <span>Page {page + 1} sur {nombrePages}</span>
                <button class="cashmire-secondary-action" type="button" onclick={() => aller(page + 1)} disabled={page >= nombrePages - 1}>Suivant</button>
              </nav>
            {/if}
          {/if}
        {/if}
      </section>
    </div>
  </div>
</section>

<style>
  .page-heading, .list-heading, .depense-ligne, .depense-infos, .actions, .pagination {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .page-heading { justify-content: space-between; padding: 12px 20px; margin-bottom: 24px; }
  .brand { display: flex; align-items: center; gap: 8px; }
  .brand strong { font: 700 27px/1 var(--story-font); }

  h1, h2, h3 { margin: 0; font-family: var(--story-font); line-height: 1.2; }
  h1 { font-size: clamp(26px, 4vw, 36px); }
  h2 { margin-bottom: 16px; font-size: 25px; }
  h3 { font-size: 20px; overflow-wrap: anywhere; }

  .depenses-layout {
    display: grid;
    grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }
  .list-heading { justify-content: space-between; }
  .list-heading h2 { margin: 0; }

  .filtres { display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0; padding: 12px 16px; }
  .filtres label { display: flex; align-items: center; gap: 10px; font-weight: 700; }
  .filtres input, .filtres select {
    min-height: 44px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: #fff;
    color: var(--ink);
    font: inherit;
  }

  .total { margin: 0 0 12px; color: #435449; font-size: 14px; }
  .liste { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }
  .depense-ligne { justify-content: space-between; }
  .depense-infos { min-width: 0; }
  .depense-infos p { margin: 4px 0 0; color: #435449; font-size: 14px; }
  .cashmire-amount { margin: 0; font-size: 22px; white-space: nowrap; }
  .actions { flex-wrap: wrap; margin-top: 12px; }
  .pagination { justify-content: center; margin-top: 16px; }

  button { min-height: 44px; }
  button:disabled { opacity: .55; cursor: not-allowed; }
  button.danger {
    padding: 8px 16px;
    color: #fff;
    background: #9a3028;
    border: 1px solid #9a3028;
    border-radius: 12px;
    font: 700 14px var(--body-font);
    cursor: pointer;
  }
  :focus-visible { outline: 3px solid #754a0b; outline-offset: 3px; }

  .notice { margin: 12px 0; padding: 12px; border-radius: 12px; }
  .error { color: #922514; background: #fce5dd; }
  .success { background: #e4f0de; }
  .empty { border-style: dashed; }

  @media (max-width: 767px) {
    .page-heading { flex-wrap: wrap; padding: 10px 14px; }
    .depenses-layout { grid-template-columns: 1fr; gap: 16px; }
    .filtres label { width: 100%; justify-content: space-between; }
    .depense-ligne { flex-wrap: wrap; }
  }
</style>
