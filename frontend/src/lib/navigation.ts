// Navigation par rechargement complet. Isolée ici pour être remplacée dans les tests (jsdom ne navigue pas).
export function aller(chemin: string): void {
  window.location.assign(chemin);
}
