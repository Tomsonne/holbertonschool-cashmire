<script lang="ts">
  import { tick } from 'svelte';
  import { champsErreurAuth, messageErreurAuth } from '../authentification';

  type Props = {
    connecter: (email: string, motDePasse: string) => Promise<unknown>;
    surSucces: () => void | Promise<void>;
    titre: string;
    avertissement?: string;
  };

  let { connecter, surSucces, titre, avertissement = '' }: Props = $props();
  let email = $state('');
  let motDePasse = $state('');
  let enCours = $state(false);
  let erreur = $state('');
  let champs = $state<Record<string, string>>({});
  let champEmail = $state<HTMLInputElement>();
  let champMotDePasse = $state<HTMLInputElement>();
  let messageGeneral = $state<HTMLElement>();

  // Focus sur le premier champ en erreur, dans l'ordre du formulaire, sinon sur le message général.
  async function focaliserErreur() {
    await tick();
    if (champs.email) champEmail?.focus();
    else if (champs.mot_de_passe) champMotDePasse?.focus();
    else messageGeneral?.focus();
  }

  // Une erreur ne masque jamais le formulaire : les saisies restent en place.
  async function soumettre(event: SubmitEvent) {
    event.preventDefault();
    if (enCours) return;
    enCours = true;
    erreur = '';
    champs = {};
    try {
      await connecter(email, motDePasse);
    } catch (cause) {
      erreur = messageErreurAuth(cause, 'connexion');
      champs = champsErreurAuth(cause);
      enCours = false;
      await focaliserErreur();
      return;
    }
    motDePasse = '';
    enCours = false;
    await surSucces();
  }
</script>

<h2>{titre}</h2>
<p>Connectez-vous pour retrouver vos budgets personnels.</p>
{#if avertissement}<p class="login-error" role="alert">{avertissement}</p>{/if}
<form onsubmit={soumettre}>
  <label for="connexion-email">Adresse e-mail</label>
  <input id="connexion-email" type="email" autocomplete="username" bind:value={email} bind:this={champEmail} required
    aria-invalid={champs.email ? 'true' : undefined} aria-describedby={champs.email ? 'connexion-email-erreur' : undefined} />
  {#if champs.email}<p id="connexion-email-erreur" class="champ-erreur">{champs.email}</p>{/if}
  <label for="connexion-mot-de-passe">Mot de passe</label>
  <input id="connexion-mot-de-passe" type="password" autocomplete="current-password" maxlength="128" bind:value={motDePasse} bind:this={champMotDePasse} required
    aria-invalid={champs.mot_de_passe ? 'true' : undefined} aria-describedby={champs.mot_de_passe ? 'connexion-mot-de-passe-erreur' : undefined} />
  {#if champs.mot_de_passe}<p id="connexion-mot-de-passe-erreur" class="champ-erreur">{champs.mot_de_passe}</p>{/if}
  {#if erreur}<p class="login-error" role="alert" tabindex="-1" bind:this={messageGeneral}>{erreur}</p>{/if}
  <button class="cashmire-primary-action" type="submit" disabled={enCours}>{enCours ? 'Connexion…' : 'Se connecter'}</button>
</form>
