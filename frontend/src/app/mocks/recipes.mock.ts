import { Recipe } from '../features/inventory/models/recipe.model';
import { PRODUCT_IDS, RECIPE_IDS } from './seed-ids.const';

export const RECIPES_MOCK: Recipe[] = [
  {
    id: RECIPE_IDS.TORTA_CHOCOLATE,
    productId: PRODUCT_IDS.TORTA_CHOCOLATE,
    name: 'Torta de Chocolate',
    description: 'Torta clásica de chocolate, receta base de la casa.',
    yieldQuantity: 1,
    ingredients: [
      { productId: PRODUCT_IDS.HARINA, quantity: 0.5, unit: 'kg' },
      { productId: PRODUCT_IDS.AZUCAR, quantity: 0.3, unit: 'kg' },
      { productId: PRODUCT_IDS.HUEVOS, quantity: 4, unit: 'unidad' },
      { productId: PRODUCT_IDS.CHOCOLATE, quantity: 0.2, unit: 'kg' },
      { productId: PRODUCT_IDS.LECHE, quantity: 0.25, unit: 'L' },
    ],
    notes: 'Hornear a 180°C durante 40 minutos.',
  },
  {
    id: RECIPE_IDS.BROWNIE,
    productId: PRODUCT_IDS.BROWNIE,
    name: 'Brownie de Chocolate',
    description: 'Brownie húmedo individual.',
    yieldQuantity: 12,
    ingredients: [
      { productId: PRODUCT_IDS.HARINA, quantity: 0.4, unit: 'kg' },
      { productId: PRODUCT_IDS.AZUCAR, quantity: 0.35, unit: 'kg' },
      { productId: PRODUCT_IDS.HUEVOS, quantity: 3, unit: 'unidad' },
      { productId: PRODUCT_IDS.CHOCOLATE, quantity: 0.25, unit: 'kg' },
    ],
    notes: 'Hornear a 175°C durante 25 minutos y cortar en 12 porciones.',
  },
];
