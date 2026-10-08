<script lang="ts">
  import { onMount } from 'svelte';
  import { budgetsApi } from './lib/api/budgets';
  import { chargerPageDepenses } from './lib/api/depenses';
  import { getHealth } from './lib/api/health';
  import type { Categorie, ErreurApi } from './lib/budgets';
  import BudgetManager from './lib/components/BudgetManager.svelte';
  import HealthCard from './lib/components/HealthCard.svelte';
  import MonthlyDashboard from './lib/components/MonthlyDashboard.svelte';
  import Navigation from './lib/components/Navigation.svelte';
  import { trouverRoute } from './lib/routes';
  import { session } from './lib/session.svelte';

  const chemin = window.location.pathname;
  const route = trouverRoute(chemin);
  let etatSante = $state<'loading' | 'ready' | 'failed'>('loading');
  let categories = $state<Categorie[]>([]);
  let categoriesChargees = $state(false);
  let erreurChargement = $state('');
  let courriel = $state('');
  let motDePasse = $state('');
  let connexionEnCours = $state(false);
  let messageConnexion = $state('');
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
    messageConnexion = '';
    await session.charger();
    if (session.etat === 'pret') await chargerCategories();
  }

  async function connecter(event: SubmitEvent) {
    event.preventDefault();
    connexionEnCours = true;
    messageConnexion = '';
    categoriesChargees = false;
    try {
      await session.connecter(courriel, motDePasse);
      motDePasse = '';
    } catch (cause) {
      const message = (cause as Error)?.message || 'Connexion impossible. Réessayez.';
      if ((cause as ErreurApi)?.status === 401) messageConnexion = message;
      else erreurChargement = message;
      return;
    } finally { connexionEnCours = false; }
    await chargerCategories();
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
    {:else if route.ecran === 'synthese'}<MonthlyDashboard loadBudgets={budgetsApi.lister} loadExpensePage={chargerPageDepenses} />{/if}
  {:else}
    <main class="access-page cashmire-page">
      <div class="cashmire-shell">
        <div class="access-layout">
          <section class="access-illustration cashmire-hero"><img class="cashmire-hero-media" src="/assets/cashmire/hero-village.png" alt="" /><div><h1>Des budgets bien construits.</h1><p>Chaque dépense trouve sa place.</p></div></section>
          <section class="access-card cashmire-card" aria-label="Accès aux budgets">
            {#if ecran === 'chargement'}
              <p role="status">Chargement de votre session…</p>
            {:else if ecran === 'erreur'}
              <h2>Service indisponible</h2><p role="alert">{erreurChargement || session.message}</p><button class="cashmire-primary-action" type="button" onclick={chargerSession}>Réessayer</button>
            {:else}
              <h2>Accéder à mes budgets</h2>
              <p>Connectez-vous pour retrouver vos budgets personnels.</p>
              <form onsubmit={connecter}>
                <label for="email">Adresse e-mail</label><input id="email" type="email" autocomplete="username" bind:value={courriel} required />
                <label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" bind:value={motDePasse} required />
                {#if messageConnexion || session.message}<p class="login-error" role="alert">{messageConnexion || session.message}</p>{/if}
                <button class="cashmire-primary-action" type="submit" disabled={connexionEnCours}>{connexionEnCours ? 'Connexion…' : 'Se connecter'}</button>
              </form>
            {/if}
          </section>
        </div>
      </div>
    </main>
  {/if}
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

<style>
  .access-page { display: block; }
  .access-page * { box-sizing: border-box; }
  .access-layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr); gap: 16px; }
  .access-illustration { display: flex; align-items: flex-start; padding: 28px; }
  .access-illustration > div { width: 50%; }
  .access-illustration h1 { font: 700 clamp(30px, 4vw, 46px)/1.15 var(--story-font); margin: 0 0 8px; }
  .access-illustration p { margin: 0; }
  .access-card h2 { font: 700 27px var(--story-font); margin: 0 0 8px; }
  .access-card p { margin: 0 0 16px; }
  .access-card label { display: block; font-weight: 700; margin: 12px 0 4px; }
  .access-card input { width: 100%; min-height: 44px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 10px; font: inherit; }
  .access-card button { margin-top: 18px; }
  .access-page :focus-visible { outline: 3px solid #754a0b; outline-offset: 3px; }
  .login-error, .session-message { color: #922514; }
  .session-message { padding: 8px 24px; background: #fce5dd; }
  @media (max-width: 767px) {
    .access-layout { grid-template-columns: 1fr; }
    .access-illustration { display: block; padding: 0; }
    .access-illustration > div { width: 100%; padding: 20px; }
    .access-illustration h1 { font-size: 28px; }
  }
</style>
