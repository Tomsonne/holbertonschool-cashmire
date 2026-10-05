<script lang="ts">
  import { onMount } from 'svelte';
  import { getHealth } from './lib/api/health';
  import HealthCard from './lib/components/HealthCard.svelte';

  let state = $state<'loading' | 'ready' | 'failed'>('loading');
  async function checkHealth() {
    state = 'loading';
    try {
      const result = await getHealth();
      state = result.statut === 'ok' && result.base_de_donnees === 'disponible' ? 'ready' : 'failed';
    } catch {
      state = 'failed';
    }
  }
  onMount(() => { void checkHealth(); });
</script>

<main>
  <div class="shell">
    <header><div class="brand-mark" aria-hidden="true">C</div><span>CASHMIRE</span><span class="tag">APERÇU TECHNIQUE</span></header>
    <section class="intro">
      <p class="eyebrow">VOTRE ARGENT, PLUS LISIBLE</p>
      <h1>Bienvenue sur <em>Cashmire.</em></h1>
      <p class="lead">Une base simple pour suivre vos dépenses et garder vos projets financiers en vue.</p>
    </section>
    <HealthCard {state} retry={checkHealth} />
    <footer><span>Une application pédagogique construite avec soin.</span><span>État du système <i></i></span></footer>
  </div>
</main>
