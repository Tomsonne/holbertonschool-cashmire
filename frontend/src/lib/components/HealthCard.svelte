<script lang="ts">
  let { state, retry }: { state: 'loading' | 'ready' | 'failed'; retry: () => void } = $props();
</script>

<section class="status-card" aria-live="polite">
  {#if state === 'loading'}
    <span class="indicator loading" aria-hidden="true"></span>
    <div><h2>Vérification en cours</h2><p>Nous vérifions la connexion à Cashmire.</p></div>
  {:else if state === 'ready'}
    <span class="indicator ready" aria-hidden="true"></span>
    <div><h2>Tout fonctionne</h2><p>L’API et la base de données sont disponibles.</p></div>
  {:else}
    <span class="indicator failed" aria-hidden="true"></span>
    <div class="status-copy"><h2>Service momentanément indisponible</h2><p>Impossible de joindre la base de données ou l’API. Réessayez dans un instant.</p></div>
    <button onclick={retry}>Réessayer</button>
  {/if}
</section>
