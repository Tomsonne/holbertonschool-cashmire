export type HealthStatus = {
  statut: 'ok' | 'degrade';
  base_de_donnees: 'disponible' | 'indisponible';
};

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch('/api/health');
  if (!response.ok) throw new Error(`API indisponible (${response.status})`);
  return response.json() as Promise<HealthStatus>;
}
