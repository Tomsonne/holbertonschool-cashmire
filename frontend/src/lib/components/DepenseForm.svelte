<script lang="ts">
  import type { Categorie, ErreurApi } from '../budgets';
  import type { Depense } from '../dashboard';
  import type { DepenseFormulaire } from '../depenses';
  import { dateIso, messageErreurDepense, normaliserMontant, validerFormulaire } from '../depenses';

  type Props = {
    categories: Categorie[];
    depense?: Depense | null;
    enregistrer: (donnees: DepenseFormulaire) => Promise<void>;
    annuler?: () => void;
  };

  let { categories, depense = null, enregistrer, annuler }: Props = $props();
  const uid = $props.id();

  // On ne lit `depense` qu'une fois, volontairement : c'est la valeur de départ du formulaire.
  // svelte-ignore state_referenced_locally
  const depart = {
    montant: depense?.montant ?? '',
    libelle: depense?.libelle ?? '',
    dateDepense: depense?.date_depense ?? dateIso(new Date()),
    categorieId: depense?.categorie.id ?? '',
  };
  let montant = $state(depart.montant);
  let libelle = $state(depart.libelle);
  let dateDepense = $state(depart.dateDepense);
  let categorieId = $state(depart.categorieId);
  let champs = $state<Record<string, string>>({});
  let erreur = $state('');
  let attente = $state(false);

  async function soumettre(event: SubmitEvent) {
    event.preventDefault();
    erreur = '';
    const erreursLocales = validerFormulaire({
      montant, libelle, date_depense: dateDepense, categorie_id: categorieId,
    });
    champs = { ...erreursLocales };
    if (Object.keys(erreursLocales).length > 0) return;

    attente = true;
    try {
      await enregistrer({
        montant: normaliserMontant(montant) ?? '',
        libelle: libelle.trim(),
        date_depense: dateDepense,
        categorie_id: categorieId,
      });
      if (!depense) {
        montant = ''; libelle = ''; categorieId = ''; dateDepense = dateIso(new Date());
      }
    } catch (cause) {
      erreur = messageErreurDepense(cause);
      champs = (cause as ErreurApi)?.champs ?? {};
    } finally {
      attente = false;
    }
  }
</script>

<form onsubmit={soumettre} novalidate>
  {#if erreur}<p class="notice error" role="alert">{erreur}</p>{/if}

  <label for={`${uid}-libelle`}>Libellé</label>
  <input id={`${uid}-libelle`} type="text" maxlength="200" bind:value={libelle} disabled={attente}
    aria-invalid={Boolean(champs.libelle)} aria-describedby={champs.libelle ? `${uid}-libelle-erreur` : undefined} />
  {#if champs.libelle}<p class="field-error" id={`${uid}-libelle-erreur`}>{champs.libelle}</p>{/if}

  <label for={`${uid}-montant`}>Montant (€)</label>
  <input id={`${uid}-montant`} type="text" inputmode="decimal" placeholder="12,50" bind:value={montant} disabled={attente}
    aria-invalid={Boolean(champs.montant)} aria-describedby={champs.montant ? `${uid}-montant-erreur` : undefined} />
  {#if champs.montant}<p class="field-error" id={`${uid}-montant-erreur`}>{champs.montant}</p>{/if}

  <label for={`${uid}-date`}>Date</label>
  <input id={`${uid}-date`} type="date" bind:value={dateDepense} disabled={attente}
    aria-invalid={Boolean(champs.date_depense)} aria-describedby={champs.date_depense ? `${uid}-date-erreur` : undefined} />
  {#if champs.date_depense}<p class="field-error" id={`${uid}-date-erreur`}>{champs.date_depense}</p>{/if}

  <label for={`${uid}-categorie`}>Catégorie</label>
  <select id={`${uid}-categorie`} bind:value={categorieId} disabled={attente}
    aria-invalid={Boolean(champs.categorie_id)} aria-describedby={champs.categorie_id ? `${uid}-categorie-erreur` : undefined}>
    <option value="">Choisir une catégorie</option>
    {#each categories as categorie (categorie.id)}<option value={categorie.id}>{categorie.nom}</option>{/each}
  </select>
  {#if champs.categorie_id}<p class="field-error" id={`${uid}-categorie-erreur`}>{champs.categorie_id}</p>{/if}

  <div class="actions">
    <button class="cashmire-primary-action" type="submit" disabled={attente}>
      {attente ? 'Enregistrement…' : depense ? 'Enregistrer' : 'Ajouter la dépense'}
    </button>
    {#if annuler}<button class="cashmire-secondary-action" type="button" onclick={annuler} disabled={attente}>Annuler</button>{/if}
  </div>
</form>

<style>
  label { display: block; margin: 12px 0 4px; font-weight: 700; }
  input, select {
    box-sizing: border-box;
    width: 100%;
    min-height: 44px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: #fff;
    color: var(--ink);
    font: inherit;
  }
  input[aria-invalid='true'], select[aria-invalid='true'] { border-color: #922514; }
  :focus-visible { outline: 3px solid #754a0b; outline-offset: 3px; }
  button:disabled { opacity: .55; cursor: not-allowed; }
  /* style.css colore tout bouton survolé en vert foncé : on garde le texte lisible. */
  button.cashmire-secondary-action:hover:not(:disabled) { color: var(--ink); background: #e5efe0; }
  .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
  .field-error { margin: 4px 0 0; color: #922514; }
  .notice { margin: 0 0 8px; padding: 12px; border-radius: 12px; }
  .error { background: #fce5dd; color: #922514; }
</style>
