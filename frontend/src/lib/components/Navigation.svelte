<script lang="ts">
  import type { Utilisateur } from '../api/budgets';
  import { CHEMIN_CONNEXION, CHEMIN_INSCRIPTION, routes, trouverRoute } from '../routes';

  type Props = {
    utilisateur: Utilisateur | null;
    chemin: string;
    deconnecter: () => void;
  };

  let { utilisateur, chemin, deconnecter }: Props = $props();
  const liens = routes.filter(route => route.navigation);
  let active = $derived(trouverRoute(chemin));
</script>

<header class="navigation">
  <span class="marque"><img class="cashmire-logo-image" src="/assets/cashmire/logo-emblem.png" alt="" /><strong>Cashmire</strong></span>
  {#if utilisateur}
    <nav aria-label="Pages disponibles">
      {#each liens as lien (lien.chemin)}
        <a href={lien.chemin} aria-current={active === lien ? 'page' : undefined}>{lien.libelle}</a>
      {/each}
    </nav>
    <span>Bonjour, {utilisateur.nom_affichage}</span>
    <button type="button" onclick={deconnecter}>Se déconnecter</button>
  {:else}
    <div class="acces">
      <a href={CHEMIN_CONNEXION} aria-current={active?.chemin === CHEMIN_CONNEXION ? 'page' : undefined}>Connexion</a>
      <a href={CHEMIN_INSCRIPTION} aria-current={active?.chemin === CHEMIN_INSCRIPTION ? 'page' : undefined}>Créer un compte</a>
    </div>
  {/if}
</header>

<style>
  .navigation { display: flex; align-items: center; gap: 16px; padding: 8px 24px; color: var(--ink); background: var(--ivory); border-bottom: 1px solid var(--border); font: 14px var(--body-font); }
  .marque { display: flex; align-items: center; gap: 8px; }
  .marque strong { font: 700 27px var(--story-font); }
  nav { display: flex; gap: 16px; margin-right: auto; }
  .acces { display: flex; gap: 16px; margin-left: auto; }
  a { color: var(--ink); font-weight: 700; }
  a:hover { color: #9a3028; }
  [aria-current='page'] { text-decoration-thickness: 3px; text-underline-offset: 7px; }
  button { min-height: 44px; padding: 8px 12px; color: var(--ink); background: var(--ivory); border: 1px solid var(--border); border-radius: 10px; font: inherit; cursor: pointer; }
  button:hover { color: var(--ink); background: #e5efe0; }
  :focus-visible { outline: 3px solid #754a0b; outline-offset: 3px; }
  @media (max-width: 767px) {
    .navigation { flex-wrap: wrap; padding: 8px 12px; }
    nav { order: 1; width: 100%; }
  }
</style>
