import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import App from './App.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('Cashmire health screen', () => {
  it('announces an API failure and retries on request', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('network error'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ statut: 'ok', base_de_donnees: 'disponible' }), { status: 200 }));
    render(App);
    expect(await screen.findByText('Service momentanément indisponible')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }));
    await waitFor(() => expect(screen.getByText('Tout fonctionne')).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
