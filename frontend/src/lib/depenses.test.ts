import { describe, expect, it } from 'vitest';
import { dateIso, normaliserMontant, validerFormulaire } from './depenses';

describe('normaliserMontant', () => {
  it('complète les décimales et accepte la virgule', () => {
    expect(normaliserMontant('12,5')).toBe('12.50');
    expect(normaliserMontant(' 7 ')).toBe('7.00');
  });

  it('refuse zéro, trop de décimales et le texte', () => {
    expect(normaliserMontant('0')).toBeNull();
    expect(normaliserMontant('12.345')).toBeNull();
    expect(normaliserMontant('abc')).toBeNull();
  });
});

describe('validerFormulaire', () => {
  const valide = {
    montant: '12,50',
    libelle: 'Courses',
    date_depense: dateIso(new Date()),
    categorie_id: 'cat-1',
  };

  it('ne renvoie aucune erreur pour un formulaire correct', () => {
    expect(validerFormulaire(valide)).toEqual({});
  });

  it('signale chaque champ invalide', () => {
    const erreurs = validerFormulaire({ montant: '0', libelle: '   ', date_depense: '', categorie_id: '' });
    expect(Object.keys(erreurs).sort()).toEqual(['categorie_id', 'date_depense', 'libelle', 'montant']);
  });

  it('refuse une date trop lointaine dans le futur', () => {
    const erreurs = validerFormulaire({ ...valide, date_depense: '2999-01-01' });
    expect(erreurs.date_depense).toBeDefined();
  });
});
