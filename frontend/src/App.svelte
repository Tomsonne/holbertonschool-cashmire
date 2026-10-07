<script lang="ts">
  import { onMount } from 'svelte';
  import { budgetsApi, sessionApi, type Utilisateur } from './lib/api/budgets';
  import { chargerPageDepenses } from './lib/api/depenses';
  import { getHealth } from './lib/api/health';
  import type { Categorie, ErreurApi } from './lib/budgets';
  import BudgetManager from './lib/components/BudgetManager.svelte';
  import HealthCard from './lib/components/HealthCard.svelte';
  import MonthlyDashboard from './lib/components/MonthlyDashboard.svelte';

  const chemin = window.location.pathname;
  const pageBudgets = chemin === '/' || chemin === '/budgets';
  const pageSynthese = chemin === '/synthese' || chemin === '/dashboard';
  const pagePrivee = pageBudgets || pageSynthese;
  const pageTechnique = chemin === '/etat-technique';
  let etatSante = $state<'loading' | 'ready' | 'failed'>('loading');
  let etatSession = $state<'chargement' | 'deconnecte' | 'pret' | 'erreur'>('chargement');
  let utilisateur = $state<Utilisateur | null>(null);
  let categories = $state<Categorie[]>([]);
  let courriel = $state('');
  let motDePasse = $state('');
  let connexionEnCours = $state(false);
  let message = $state('');

  async function verifierSante() {
    etatSante = 'loading';
    try {
      const resultat = await getHealth();
      etatSante = resultat.statut === 'ok' && resultat.base_de_donnees === 'disponible' ? 'ready' : 'failed';
    } catch { etatSante = 'failed'; }
  }

  async function chargerSession() {
    etatSession = 'chargement';
    message = '';
    try {
      utilisateur = await sessionApi.moi();
      categories = await budgetsApi.categories();
      etatSession = 'pret';
    } catch (cause) {
      utilisateur = null;
      etatSession = (cause as ErreurApi)?.status === 401 ? 'deconnecte' : 'erreur';
      if (etatSession === 'erreur') message = 'Impossible de charger la session ou les catégories. Réessayez.';
    }
  }

  async function connecter(event: SubmitEvent) {
    event.preventDefault();
    connexionEnCours = true;
    message = '';
    try {
      utilisateur = await sessionApi.connecter(courriel, motDePasse);
      motDePasse = '';
      categories = await budgetsApi.categories();
      etatSession = 'pret';
    } catch (cause) {
      message = (cause as Error)?.message || 'Connexion impossible. Réessayez.';
      etatSession = (cause as ErreurApi)?.status === 401 ? 'deconnecte' : 'erreur';
    } finally { connexionEnCours = false; }
  }

  async function deconnecter() {
    try { await sessionApi.deconnecter(); }
    catch (cause) { message = (cause as Error)?.message || 'Déconnexion impossible.'; return; }
    utilisateur = null;
    categories = [];
    etatSession = 'deconnecte';
  }

  onMount(() => {
    if (pagePrivee) void chargerSession();
    if (pageTechnique) void verifierSante();
  });
</script>

{#if pagePrivee}
  {#if etatSession === 'pret'}
    <div class="session-bar"><nav aria-label="Pages disponibles"><a href="/synthese" aria-current={pageSynthese ? 'page' : undefined}>Synthèse</a><a href="/budgets" aria-current={pageBudgets ? 'page' : undefined}>Budgets</a></nav><span>Bonjour, {utilisateur?.nom_affichage}</span><button type="button" onclick={deconnecter}>Se déconnecter</button></div>
    {#if message}<p class="session-message" role="alert">{message}</p>{/if}
    {#if pageBudgets}<BudgetManager {categories} loadBudgets={budgetsApi.lister} createBudget={budgetsApi.creer} updateBudget={budgetsApi.modifier} deleteBudget={budgetsApi.supprimer} />
    {:else}<MonthlyDashboard loadBudgets={budgetsApi.lister} loadExpensePage={chargerPageDepenses} />{/if}
  {:else}
    <main class="access-page cashmire-page">
      <div class="cashmire-shell">
        <header class="access-header cashmire-card"><img class="cashmire-logo-image" src="/assets/cashmire/logo-emblem.png" alt="" /><strong>Cashmire</strong><nav aria-label="Pages disponibles"><a href="/synthese">Synthèse</a><a href="/budgets">Budgets</a></nav></header>
        <div class="access-layout">
          <section class="access-illustration cashmire-hero"><img class="cashmire-hero-media" src="/assets/cashmire/hero-village.png" alt="" /><div><h1>Des budgets bien construits.</h1><p>Chaque dépense trouve sa place.</p></div></section>
          <section class="access-card cashmire-card" aria-label="Accès aux budgets">
            {#if etatSession === 'chargement'}
              <p role="status">Chargement de votre session…</p>
            {:else if etatSession === 'erreur'}
              <h2>Service indisponible</h2><p role="alert">{message}</p><button class="cashmire-primary-action" type="button" onclick={chargerSession}>Réessayer</button>
            {:else}
              <h2>Accéder à mes budgets</h2>
              <p>Connectez-vous pour retrouver vos budgets personnels.</p>
              <form onsubmit={connecter}>
                <label for="email">Adresse e-mail</label><input id="email" type="email" autocomplete="username" bind:value={courriel} required />
                <label for="password">Mot de passe</label><input id="password" type="password" autocomplete="current-password" bind:value={motDePasse} required />
                {#if message}<p class="login-error" role="alert">{message}</p>{/if}
                <button class="cashmire-primary-action" type="submit" disabled={connexionEnCours}>{connexionEnCours ? 'Connexion…' : 'Se connecter'}</button>
              </form>
            {/if}
          </section>
        </div>
      </div>
    </main>
  {/if}
{:else if pageTechnique}
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
  .access-header { display: flex; align-items: center; gap: 8px; padding: 10px 20px; margin-bottom: 16px; }
  .access-header strong { font: 700 27px var(--story-font); }
  .access-header nav { display: flex; gap: 16px; margin-left: auto; }
  .access-header a, .session-bar a { color: var(--ink); font-weight: 700; }
  .access-header a:hover, .session-bar a:hover { color: #9a3028; }
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
  .session-bar { display: flex; justify-content: flex-end; align-items: center; gap: 16px; padding: 8px 24px; color: var(--ink); background: var(--ivory); font: 14px var(--body-font); }
  .session-bar nav { display: flex; gap: 16px; margin-right: auto; }
  .session-bar [aria-current='page'] { text-decoration-thickness: 3px; text-underline-offset: 7px; }
  .session-bar button { min-height: 44px; padding: 8px 12px; color: var(--ink); background: var(--ivory); border: 1px solid var(--border); border-radius: 10px; cursor: pointer; }
  .session-message { padding: 8px 24px; background: #fce5dd; }
  @media (max-width: 767px) {
    .access-header { flex-wrap: wrap; }
    .access-header nav { margin-left: 0; width: 100%; }
    .session-bar { flex-wrap: wrap; padding: 8px 12px; }
    .session-bar nav { width: 100%; }
    .access-layout { grid-template-columns: 1fr; }
    .access-illustration { display: block; padding: 0; }
    .access-illustration > div { width: 100%; padding: 20px; }
    .access-illustration h1 { font-size: 28px; }
  }
</style>
