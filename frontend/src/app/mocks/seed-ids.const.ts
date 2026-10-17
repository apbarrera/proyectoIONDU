/**
 * Canonical IDs shared across every mock file so cross-domain references stay consistent
 * (e.g. the "Torta de Chocolate" sold in sales.mock.ts is the exact same product referenced
 * by recipes.mock.ts and inventory-movements.mock.ts).
 */
export const TENANT_ID = 'tenant-iondu-demo';

export const USER_IDS = {
  ADMIN: 'user-admin-01',
  OPERATOR: 'user-operator-01',
} as const;

export const PRODUCT_IDS = {
  TORTA_CHOCOLATE: 'prod-torta-chocolate',
  HARINA: 'prod-harina',
  AZUCAR: 'prod-azucar',
  HUEVOS: 'prod-huevos',
  CHOCOLATE: 'prod-chocolate',
  LECHE: 'prod-leche',
  CAJA_EMPAQUE: 'prod-caja-empaque',
  FRASCO_VIDRIO: 'prod-frasco-vidrio',
  CAFE_MOLIDO: 'prod-cafe-molido',
  BROWNIE: 'prod-brownie',
} as const;

export const RECIPE_IDS = {
  TORTA_CHOCOLATE: 'recipe-torta-chocolate',
  BROWNIE: 'recipe-brownie',
} as const;
