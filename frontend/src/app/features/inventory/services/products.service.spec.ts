import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { ProductsService } from './products.service';
import { Product } from '../models/product.model';

const base: Omit<Product, 'id'> = {
  sku: '',
  name: 'Producto de prueba',
  category: 'Bebidas',
  type: 'simple',
  unit: 'unidad',
  salePrice: 1,
  cost: 1,
  currentStock: 0,
  minStock: 0,
  active: true,
};

describe('ProductsService', () => {
  let service: ProductsService;

  beforeEach(() => {
    service = TestBed.inject(ProductsService);
  });

  it('propone el siguiente código según el tipo', () => {
    expect(service.nextSku('simple', ['PS-001', 'PS-009', 'IN-050'])).toBe('PS-010');
    expect(service.nextSku('insumo', ['PS-001', 'IN-050'])).toBe('IN-051');
    expect(service.nextSku('insumo', [])).toBe('IN-001');
  });

  it('genera el código cuando se crea un producto sin él', async () => {
    const expected = service.nextSku('simple');
    const created = await firstValueFrom(service.createProduct(base));
    expect(created.sku).toBe(expected);
    expect(service.getProduct(created.id)?.sku).toBe(expected);
  });

  it('respeta el código escrito a mano', async () => {
    const created = await firstValueFrom(service.createProduct({ ...base, sku: 'MI-COD' }));
    expect(created.sku).toBe('MI-COD');
  });

  it('numera seguidos los productos de una carga masiva y los deja en el orden del archivo', async () => {
    const nextSimple = Number(service.nextSku('simple').split('-')[1]);
    const nextSupply = Number(service.nextSku('insumo').split('-')[1]);
    const created = await firstValueFrom(
      service.createMany([
        { ...base, name: 'A' },
        { ...base, name: 'B' },
        { ...base, name: 'C', type: 'insumo', salePrice: null },
      ]),
    );
    const pad = (n: number) => String(n).padStart(3, '0');
    expect(created.map((p) => p.sku)).toEqual([
      `PS-${pad(nextSimple)}`,
      `PS-${pad(nextSimple + 1)}`,
      `IN-${pad(nextSupply)}`,
    ]);
    expect(service.products().slice(0, 3).map((p) => p.name)).toEqual(['A', 'B', 'C']);
  });

  it('ofrece las categorías existentes sin repetir ni distinguir mayúsculas', async () => {
    await firstValueFrom(service.createProduct({ ...base, category: 'bebidas' }));
    await firstValueFrom(service.createProduct({ ...base, category: 'Categoría nueva' }));
    const categories = service.categories();
    expect(categories.filter((c) => c.toLowerCase() === 'bebidas')).toHaveLength(1);
    expect(categories).toContain('Categoría nueva');
  });
});
