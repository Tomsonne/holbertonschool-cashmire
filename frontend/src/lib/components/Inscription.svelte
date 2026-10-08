<script lang="ts">
  import { tick } from 'svelte';
  import { champsErreurAuth, messageErreurAuth } from '../authentification';
  import { CHEMIN_CONNEXION } from '../routes';

  type Props = {
    inscrire: (email: string, motDePasse: string, nomAffichage: string) => Promise<unknown>;
  };

  let { inscrire }: Props = $props();
  let email = $state('');
  let motDePasse = $state('');
  let nomAffichage = $state('');
  let enCours = $state(false);
  let cree = $state(false);
  let erreur = $state('');
  let champs = $state<Record<string, string>>({});
  let champEmail = $state<HTMLInputElement>();
  let champMotDePasse = $state<HTMLInputElement>();
  let champNom = $state<HTMLInputElement>();
  let messageGeneral = $state<HTMLElement>();
  let messageSucces = $state<HTMLElement>();

  // Relie un champ à son aide permanente et, le cas échéant, à son message d'erreur.
  function description(cle: string, id: string, aide?: string): string | undefined {
    return [aide, champs[cle] ? `${id}-erreur` : undefined].filter(Boolean).join(' ') || undefined;
  }

  // Focus sur le premier champ en erreur, dans l'ordre du formulaire, sinon sur le message général.
  async function focaliserErreur() {
    await tick();
    if (champs.email) champEmail?.focus();
    else if (champs.mot_de_passe) champMotDePasse?.focus();
    else if (champs.nom_affichage) champNom?.focus();
    else messageGeneral?.focus();
  }

  // L'inscription ne connecte pas : après un 201, on invite à passer par la page de connexion.
  async function soumettre(event: SubmitEvent) {
    event.preventDefault();
    if (enCours) return;
    enCours = true;
    erreur = '';
    champs = {};
    try {
      await inscrire(email, motDePasse, nomAffichage);
    } catch (cause) {
      erreur = messageErreurAuth(cause, 'inscription');
      champs = champsErreurAuth(cause);
      enCours = false;
      await focaliserErreur();
      return;
    }
    motDePasse = '';
    enCours = false;
    cree = true;
    await tick();
    messageSucces?.focus();
  }
</script>

<h2>Créer un compte</h2>
{#if cree}
  <p role="status" tabindex="-1" bind:this={messageSucces}>Compte créé. Vous pouvez maintenant vous connecter.</p>
  <a class="cashmire-primary-action" href={CHEMIN_CONNEXION}>Se connecter</a>
{:else}
  <p>Créez votre compte pour suivre vos budgets et vos dépenses.</p>
  <form onsubmit={soumettre}>
    <label for="inscription-email">Adresse e-mail</label>
    <input id="inscription-email" type="email" autocomplete="username" bind:value={email} bind:this={champEmail} required
      aria-invalid={champs.email ? 'true' : undefined} aria-describedby={description('email', 'inscription-email')} />
    {#if champs.email}<p id="inscription-email-erreur" class="champ-erreur">{champs.email}</p>{/if}
    <label for="inscription-mot-de-passe">Mot de passe</label>
    <input id="inscription-mot-de-passe" type="password" autocomplete="new-password" minlength="10" maxlength="128" bind:value={motDePasse} bind:this={champMotDePasse} required
      aria-invalid={champs.mot_de_passe ? 'true' : undefined} aria-describedby={description('mot_de_passe', 'inscription-mot-de-passe', 'inscription-mot-de-passe-aide')} />
    <p id="inscription-mot-de-passe-aide" class="aide">Entre 10 et 128 caractères.</p>
    {#if champs.mot_de_passe}<p id="inscription-mot-de-passe-erreur" class="champ-erreur">{champs.mot_de_passe}</p>{/if}
    <label for="inscription-nom">Nom d’affichage</label>
    <input id="inscription-nom" type="text" autocomplete="name" maxlength="100" bind:value={nomAffichage} bind:this={champNom} required
      aria-invalid={champs.nom_affichage ? 'true' : undefined} aria-describedby={description('nom_affichage', 'inscription-nom')} />
    {#if champs.nom_affichage}<p id="inscription-nom-erreur" class="champ-erreur">{champs.nom_affichage}</p>{/if}
    {#if erreur}<p class="login-error" role="alert" tabindex="-1" bind:this={messageGeneral}>{erreur}</p>{/if}
    <button class="cashmire-primary-action" type="submit" disabled={enCours}>{enCours ? 'Création du compte…' : 'Créer mon compte'}</button>
  </form>
{/if}
