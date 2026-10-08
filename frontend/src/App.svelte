<script lang="ts">
  import { onMount } from 'svelte';
  import { budgetsApi, sessionApi } from './lib/api/budgets';
  import { chargerPageDepenses, depensesApi } from './lib/api/depenses';
  import { getHealth } from './lib/api/health';
  import type { Categorie, ErreurApi } from './lib/budgets';
  import BudgetManager from './lib/components/BudgetManager.svelte';
  import Connexion from './lib/components/Connexion.svelte';
  import DepensesManager from './lib/components/DepensesManager.svelte';
  import HealthCard from './lib/components/HealthCard.svelte';
  import Inscription from './lib/components/Inscription.svelte';
  import MonthlyDashboard from './lib/components/MonthlyDashboard.svelte';
  import Navigation from './lib/components/Navigation.svelte';
  import { aller } from './lib/navigation';
  import { trouverRoute } from './lib/routes';
  import { session } from './lib/session.svelte';

  const chemin = window.location.pathname;
  const route = trouverRoute(chemin);
  let etatSante = $state<'loading' | 'ready' | 'failed'>('loading');
  let categories = $state<Categorie[]>([]);
  let categoriesChargees = $state(false);
  let erreurChargement = $state('');
  // Pages publiques qui affichent le formulaire de connexion ou d'inscription sans interroger /moi.
  const pageAcces = route?.ecran === 'connexion' || route?.ecran === 'inscription';
  // L'écran privé n'est prêt qu'une fois la session et les catégories chargées, dans cet ordre.
  let ecran = $derived(
    erreurChargement ? 'erreur'
      : session.etat === 'pret' ? (categoriesChargees ? 'pret' : 'chargement')
        : session.etat,
  );

  async function verifierSante() {
    etatSante = 'loading';
    try {
      const resultat = await getHealth();
      etatSante = resultat.statut === 'ok' && resultat.base_de_donnees === 'disponible' ? 'ready' : 'failed';
    } catch { etatSante = 'failed'; }
  }

  async function chargerCategories() {
    categoriesChargees = false;
    try {
      categories = await budgetsApi.categories();
      categoriesChargees = true;
    } catch (cause) {
      // Un 401 est déjà traité par le store comme une session expirée.
      if ((cause as ErreurApi)?.status !== 401) erreurChargement = 'Impossible de charger la session ou les catégories. Réessayez.';
    }
  }

  async function chargerSession() {
    erreurChargement = '';
    await session.charger();
    if (session.etat === 'pret') await chargerCategories();
  }

  // Connexion depuis une page privée : les erreurs restent dans le formulaire (composant Connexion),
  // les catégories sont rechargées ensuite par `surSucces`.
  async function connecterSurPagePrivee(email: string, motDePasse: string) {
    categoriesChargees = false;
    await session.connecter(email, motDePasse);
  }

  async function deconnecter() {
    await session.deconnecter();
    if (session.etat === 'deconnecte') {
      categories = [];
      categoriesChargees = false;
    }
  }

  // Lancé dès l'initialisation pour qu'aucun écran privé ne s'affiche avec un état de session périmé.
  if (route?.privee) void chargerSession();

  onMount(() => {
    if (route?.ecran === 'technique') void verifierSante();
  });
</script>

{#if route?.privee}
  <Navigation utilisateur={session.utilisateur} {chemin} {deconnecter} />
  {#if ecran === 'pret'}
    {#if session.message}<p class="session-message" role="alert">{session.message}</p>{/if}
    {#if route.ecran === 'budgets'}<BudgetManager {categories} loadBudgets={budgetsApi.lister} createBudget={budgetsApi.creer} updateBudget={budgetsApi.modifier} deleteBudget={budgetsApi.supprimer} />
    {:else if route.ecran === 'depenses'}<DepensesManager {categories} loadDepenses={depensesApi.lister} createDepense={depensesApi.creer} updateDepense={depensesApi.modifier} deleteDepense={depensesApi.supprimer} />
    {:else if route.ecran === 'synthese'}<MonthlyDashboard loadBudgets={budgetsApi.lister} loadExpensePage={chargerPageDepenses} />{/if}
  {:else}
    {@render pageAccesCompte()}
  {/if}
{:else if pageAcces}
  <Navigation utilisateur={session.utilisateur} {chemin} {deconnecter} />
  {@render pageAccesCompte()}
{:else if route?.ecran === 'technique'}
  <main>
    <div class="shell">
      <header><div class="brand-mark" aria-hidden="true">C</div><span>CASHMIRE</span><span class="tag">APERÇU TECHNIQUE</span></header>
      <section class="intro"><p class="eyebrow">VOTRE ARGENT, PLUS LISIBLE</p><h1>Bienvenue sur <em>Cashmire.</em></h1><p class="lead">Une base simple pour suivre vos dépenses et garder vos projets financiers en vue.</p></section>
      <HealthCard state={etatSante} retry={verifierSante} />
      <footer><span>Une application pédagogique construite avec soin.</span><span>État du système <i></i></span></footer>
    </div>
  </main>
{:else}
  <main class="access-page cashmire-page"><div class="cashmire-shell cashmire-card"><h1>Page introuvable</h1><a href="/budgets">Ouvrir mes budgets</a></div></main>
{/if}

{#snippet pageAccesCompte()}
  <main class="access-page cashmire-page">
    <div class="cashmire-shell">
      <div class="access-layout">
        <section class="access-illustration cashmire-hero"><img class="cashmire-hero-media" src="/assets/cashmire/hero-village.png" alt="" /><div><h1>Des budgets bien construits.</h1><p>Chaque dépense trouve sa place.</p></div></section>
        <section class="access-card cashmire-card" aria-label={route?.ecran === 'inscription' ? 'Création de compte' : 'Accès aux budgets'}>
          {#if route?.ecran === 'inscription'}
            <Inscription inscrire={sessionApi.inscrire} />
          {:else if route?.ecran === 'connexion'}
            <Connexion titre="Connexion" connecter={session.connecter} surSucces={() => aller('/budgets')} />
          {:else if ecran === 'chargement'}
            <p role="status">Chargement de votre session…</p>
          {:else if ecran === 'erreur'}
            <h2>Service indisponible</h2><p role="alert">{erreurChargement || session.message}</p><button class="cashmire-primary-action" type="button" onclick={chargerSession}>Réessayer</button>
          {:else}
            <Connexion titre="Accéder à mes budgets" connecter={connecterSurPagePrivee} surSucces={chargerCategories} avertissement={session.message} />
          {/if}
        </section>
      </div>
    </div>
  </main>
{/snippet}

<style>
  .access-page { display: block; }
  .access-page :global(*) { box-sizing: border-box; }
  .access-layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr); gap: 16px; }
  .access-illustration { display: flex; align-items: flex-start; padding: 28px; }
  .access-illustration > div { width: 50%; }
  .access-illustration h1 { font: 700 clamp(30px, 4vw, 46px)/1.15 var(--story-font); margin: 0 0 8px; }
  .access-illustration p { margin: 0; }
  /* Les formulaires sont rendus par Connexion et Inscription : leurs éléments sont stylés en :global. */
  .access-card :global(h2) { font: 700 27px var(--story-font); margin: 0 0 8px; }
  .access-card :global(p) { margin: 0 0 16px; }
  .access-card :global(label) { display: block; font-weight: 700; margin: 12px 0 4px; }
  .access-card :global(input) { width: 100%; min-height: 44px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 10px; font: inherit; }
  .access-card :global(input[aria-invalid='true']) { border-color: #922514; }
  .access-card :global(.aide), .access-card :global(.champ-erreur) { margin: 4px 0 0; font-size: 14px; }
  .access-card :global(button), .access-card :global(a.cashmire-primary-action) { display: inline-block; margin-top: 18px; }
  .access-page :global(:focus-visible) { outline: 3px solid #754a0b; outline-offset: 3px; }
  .access-card :global(.login-error), .access-card :global(.champ-erreur), .session-message { color: #922514; }
  .session-message { padding: 8px 24px; background: #fce5dd; }
  @media (max-width: 767px) {
    .access-layout { grid-template-columns: 1fr; }
    .access-illustration { display: block; padding: 0; }
    .access-illustration > div { width: 100%; padding: 20px; }
    .access-illustration h1 { font-size: 28px; }
  }
</style>
