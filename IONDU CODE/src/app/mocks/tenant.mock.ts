import { Tenant } from '../core/models/tenant.model';
import { TENANT_ID } from './seed-ids.const';

export const TENANT_MOCK: Tenant = {
  id: TENANT_ID,
  businessName: 'Dulce Ecuador S.A.S.',
  tradeName: 'Dulce Ecuador Pastelería',
  ruc: '1792345678001',
  economicActivity: 'Elaboración y venta de productos de panadería y pastelería',
  address: 'Av. Amazonas N34-451 y Av. Atahualpa, Quito, Ecuador',
  phone: '+593 2 255 1234',
  email: 'contacto@dulceecuador.demo',
  ivaRate: 0.15,
  logoUrl: null,
  electronicSignature: {
    configured: true,
    fileName: 'firma_dulce_ecuador.p12',
    expiresAt: '2027-03-15',
  },
};
