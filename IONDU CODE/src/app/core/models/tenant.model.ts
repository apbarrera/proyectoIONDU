export interface Tenant {
  id: string;
  businessName: string;
  tradeName: string;
  ruc: string;
  economicActivity: string;
  address: string;
  phone: string;
  email: string;
  ivaRate: number;
  logoUrl: string | null;
  electronicSignature: {
    configured: boolean;
    fileName: string | null;
    expiresAt: string | null;
  };
}
