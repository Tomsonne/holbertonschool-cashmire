import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import Navigation from './Navigation.svelte';

afterEach(() => { cleanup(); vi.restoreAllMocks(); window.history.replaceState({}, '', '/'); });

const alice = { id: 'u-1', email: 'alice@example.test', nom_affichage: 'Alice' };

describe('Navigation', () => {
  it('montre seulement la marque et le lien de connexion à un visiteur', () => {
    render(Navigation, { utilisateur: null, chemin: '/budgets', deconnecter: vi.fn() });
    expect(screen.getByText('Cashmire')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Connexion' })).toHaveAttribute('href', '/budgets');
    expect(screen.queryByRole('link', { name: 'Synthèse' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Budgets' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Se déconnecter' })).not.toBeInTheDocument();
  });

  it('montre les pages, le nom et la déconnexion à un utilisateur connecté', async () => {
    const deconnecter = vi.fn();
    render(Navigation, { utilisateur: alice, chemin: '/synthese', deconnecter });
    expect(screen.getByRole('link', { name: 'Synthèse' })).toHaveAttribute('href', '/synthese');
    expect(screen.getByRole('link', { name: 'Budgets' })).toHaveAttribute('href', '/budgets');
    expect(screen.getByText('Bonjour, Alice')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Connexion' })).not.toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: 'Se déconnecter' }));
    expect(deconnecter).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['/synthese', 'Synthèse', 'Budgets'],
    ['/dashboard', 'Synthèse', 'Budgets'],
    ['/budgets', 'Budgets', 'Synthèse'],
    ['/', 'Budgets', 'Synthèse'],
  ])('marque la page active sur %s', (chemin, active, inactive) => {
    render(Navigation, { utilisateur: alice, chemin, deconnecter: vi.fn() });
    expect(screen.getByRole('link', { name: active })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: inactive })).not.toHaveAttribute('aria-current');
  });
});
