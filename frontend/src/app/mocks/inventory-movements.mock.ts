import { InventoryMovement } from '../features/inventory/models/movement.model';
import { PRODUCT_IDS } from './seed-ids.const';

export const INVENTORY_MOVEMENTS_MOCK: InventoryMovement[] = [
  {
    id: 'mov-001',
    productId: PRODUCT_IDS.HARINA,
    productName: 'Harina de Trigo',
    type: 'entrada',
    quantity: 25,
    resultingStock: 42,
    reference: 'Compra a Molinos del Valle',
    date: '2026-08-05T09:00:00.000Z',
    createdBy: 'María Fernanda Salazar',
  },
  {
    id: 'mov-002',
    productId: PRODUCT_IDS.TORTA_CHOCOLATE,
    productName: 'Torta de Chocolate',
    type: 'produccion_ingreso',
    quantity: 6,
    resultingStock: 12,
    reference: 'Fabricación #PR-014',
    date: '2026-08-06T14:30:00.000Z',
    createdBy: 'Juan Carlos Pérez',
  },
  {
    id: 'mov-003',
    productId: PRODUCT_IDS.CHOCOLATE,
    productName: 'Chocolate en Polvo',
    type: 'produccion_consumo',
    quantity: -1.2,
    resultingStock: 3,
    reference: 'Fabricación #PR-014',
    date: '2026-08-06T14:30:00.000Z',
    createdBy: 'Juan Carlos Pérez',
  },
];
