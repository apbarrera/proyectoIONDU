import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { environment } from '../../../../environments/environment';
import {
  CreateProductInput,
  ProductCategory,
  ProductsApiService,
  UpdateProductInput,
} from './products-api.service';

describe('ProductsApiService', () => {
  let service: ProductsApiService;
  let httpMock: HttpTestingController;
  const baseUrl = environment.apiUrl;

  const productoDto = (overrides: Record<string, unknown> = {}) => ({
    id: 12,
    sku: 'CAF-250',
    name: 'Cafe molido',
    description: null,
    categoryId: 3,
    categoryName: 'Bebidas',
    type: 'venta',
    unit: 'UNIDAD',
    salePrice: 4.5,
    cost: 2.8,
    vatPercentageCode: '4',
    appliesVat: true,
    currentStock: 18,
    minStock: 5,
    lowStock: false,
    active: true,
    ...overrides,
  });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ProductsApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(ProductsApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('consulta las categorias de la empresa', () => {
    const categorias: ProductCategory[] = [
      { id: 3, name: 'Bebidas', description: null },
    ];

    let resultado: ProductCategory[] | undefined;
    service.getCategories().subscribe((items) => (resultado = items));

    const request = httpMock.expectOne(`${baseUrl}/product-categories`);
    expect(request.request.method).toBe('GET');
    request.flush(categorias);

    expect(resultado).toEqual(categorias);
  });

  it('crea una categoria eliminando espacios externos del nombre', () => {
    let resultado: ProductCategory | undefined;

    service.createCategory('  Bebidas  ').subscribe((item) => (resultado = item));

    const request = httpMock.expectOne(`${baseUrl}/product-categories`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ name: 'Bebidas' });

    request.flush({ id: 3, name: 'Bebidas', description: null });

    expect(resultado?.id).toBe(3);
  });

  it('consulta el catalogo y convierte la respuesta al modelo frontend', () => {
    let resultado: unknown;

    service.getProducts().subscribe((items) => (resultado = items));

    const request = httpMock.expectOne(
      (req) =>
        req.url === `${baseUrl}/products` &&
        req.params.get('page') === '1' &&
        req.params.get('pageSize') === '100',
    );

    expect(request.request.method).toBe('GET');
    request.flush({
      items: [productoDto()],
      total: 1,
      page: 1,
      pageSize: 100,
    });

    expect(resultado).toEqual([
      {
        id: '12',
        sku: 'CAF-250',
        name: 'Cafe molido',
        description: null,
        category: 'Bebidas',
        categoryId: 3,
        type: 'venta',
        unit: 'UNIDAD',
        salePrice: 4.5,
        cost: 2.8,
        currentStock: 18,
        minStock: 5,
        active: true,
      },
    ]);
  });

  it('recupera las paginas siguientes cuando el catalogo supera 100 productos', () => {
    let cantidad = 0;

    service.getProducts().subscribe((items) => (cantidad = items.length));

    const primera = httpMock.expectOne(
      (req) =>
        req.url === `${baseUrl}/products` &&
        req.params.get('page') === '1',
    );

    primera.flush({
      items: Array.from({ length: 100 }, (_, index) =>
        productoDto({ id: index + 1 }),
      ),
      total: 101,
      page: 1,
      pageSize: 100,
    });

    const segunda = httpMock.expectOne(
      (req) =>
        req.url === `${baseUrl}/products` &&
        req.params.get('page') === '2',
    );

    segunda.flush({
      items: [productoDto({ id: 101 })],
      total: 101,
      page: 2,
      pageSize: 100,
    });

    expect(cantidad).toBe(101);
  });

  it('envia precio cero al crear un insumo cuyo precio frontend es null', () => {
    const input: CreateProductInput = {
      sku: 'INS-001',
      name: 'Harina',
      description: null,
      categoryId: 3,
      type: 'insumo',
      unit: 'KG',
      salePrice: null,
      cost: 2.5,
      currentStock: 10,
      minStock: 2,
    };

    let resultado: { salePrice: number | null } | undefined;

    service.createProduct(input).subscribe((item) => {
      resultado = { salePrice: item.salePrice };
    });

    const request = httpMock.expectOne(`${baseUrl}/products`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      sku: 'INS-001',
      name: 'Harina',
      description: null,
      categoryId: 3,
      type: 'insumo',
      unit: 'KG',
      salePrice: 0,
      cost: 2.5,
      currentStock: 10,
      minStock: 2,
    });

    request.flush(
      productoDto({
        id: 20,
        sku: 'INS-001',
        name: 'Harina',
        type: 'insumo',
        unit: 'KG',
        salePrice: 0,
        cost: 2.5,
        currentStock: 10,
        minStock: 2,
      }),
    );

    expect(resultado?.salePrice).toBeNull();
  });

  it('actualiza un producto sin enviar currentStock', () => {
    const input: UpdateProductInput = {
      sku: 'CAF-250',
      name: 'Cafe actualizado',
      description: null,
      categoryId: 3,
      type: 'venta',
      unit: 'UNIDAD',
      salePrice: 5,
      cost: 2.8,
      minStock: 4,
      active: true,
    };

    let resultado: unknown;

    service.updateProduct('12', input).subscribe((item) => (resultado = item));

    const request = httpMock.expectOne(`${baseUrl}/products/12`);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({
      sku: 'CAF-250',
      name: 'Cafe actualizado',
      description: null,
      categoryId: 3,
      type: 'venta',
      unit: 'UNIDAD',
      salePrice: 5,
      cost: 2.8,
      minStock: 4,
      active: true,
    });
    expect(request.request.body).not.toHaveProperty('currentStock');

    request.flush(productoDto({ name: 'Cafe actualizado', salePrice: 5 }));

    expect(resultado).toBeTruthy();
  });
});
