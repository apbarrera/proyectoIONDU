import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ToastService } from '../../../../core/services/toast.service';
import { Product, ProductType } from '../../models/product.model';
import {
  ProductCategory,
  ProductsApiService,
} from '../../services/products-api.service';
import { Products } from './products';

describe('Products', () => {
  let component: Products;
  let fixture: ComponentFixture<Products>;
  let toast: ToastService;

  const categories: ProductCategory[] = [
    { id: 3, name: 'General', description: null },
    { id: 4, name: 'Bebidas', description: null },
  ];

  const producto = (overrides: Partial<Product> = {}): Product => ({
    id: '12',
    sku: 'TEST-001',
    name: 'Producto de prueba',
    description: null,
    category: 'General',
    categoryId: 3,
    type: 'venta',
    unit: 'UNIDAD',
    salePrice: 12.5,
    cost: 5,
    currentStock: 10,
    minStock: 2,
    active: true,
    ...overrides,
  });

  const apiMock = {
    getCategories: vi.fn(),
    getProducts: vi.fn(),
    createCategory: vi.fn(),
    createProduct: vi.fn(),
    updateProduct: vi.fn(),
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    apiMock.getCategories.mockReturnValue(of(categories));
    apiMock.getProducts.mockReturnValue(of([producto()]));
    apiMock.createCategory.mockReturnValue(
      of({ id: 5, name: 'Nueva', description: null }),
    );
    apiMock.createProduct.mockImplementation((input) =>
      of(producto({
        id: '20',
        sku: input.sku,
        name: input.name,
        description: input.description ?? null,
        categoryId: input.categoryId,
        type: input.type,
        salePrice: input.type === 'insumo' ? null : input.salePrice,
        currentStock: input.currentStock,
        active: true,
      })),
    );
    apiMock.updateProduct.mockImplementation((id, input) =>
      of(producto({
        id,
        sku: input.sku,
        name: input.name,
        description: input.description ?? null,
        categoryId: input.categoryId,
        type: input.type,
        salePrice: input.type === 'insumo' ? null : input.salePrice,
        minStock: input.minStock,
        active: input.active,
      })),
    );

    await TestBed.configureTestingModule({
      imports: [Products],
      providers: [
        { provide: ProductsApiService, useValue: apiMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Products);
    component = fixture.componentInstance;
    toast = TestBed.inject(ToastService);
    vi.spyOn(toast, 'success');

    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  function completarFormulario(type: ProductType): void {
    component.openCreate();
    component.form.patchValue({
      sku: 'TEST-001',
      name: 'Producto de prueba',
      description: 'Descripción de prueba',
      categoryId: 3,
      type,
      unit: 'UNIDAD',
      salePrice: 12.5,
      cost: 5,
      currentStock: 10,
      minStock: 2,
    });
  }

  it('crea el componente y carga productos y categorías', () => {
    expect(component).toBeTruthy();
    expect(apiMock.getProducts).toHaveBeenCalled();
    expect(apiMock.getCategories).toHaveBeenCalled();
    expect(component.products()).toHaveLength(1);
    expect(component.categories()).toEqual(categories);
    expect(component.loading()).toBe(false);
  });

  it('usa venta como tipo predeterminado al crear un producto', () => {
    component.openCreate();

    expect(component.form.controls.type.value).toBe('venta');
  });

  it('filtra los productos del tipo ambos', () => {
    component.products.set([
      producto({ id: '1', type: 'venta' }),
      producto({ id: '2', type: 'ambos' }),
      producto({ id: '3', type: 'insumo', salePrice: null }),
    ]);

    component.typeFilter.set('ambos');

    expect(component.filteredProducts()).toHaveLength(1);
    expect(component.filteredProducts()[0].type).toBe('ambos');
  });

  it('crea un insumo enviando precio de venta cero y stock inicial', () => {
    completarFormulario('insumo');
    component.save();

    expect(apiMock.createProduct).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'insumo',
        salePrice: null,
        categoryId: 3,
        currentStock: 10,
        description: 'Descripción de prueba',
      }),
    );
    expect(apiMock.updateProduct).not.toHaveBeenCalled();
  });

  it('conserva el precio de venta para un producto ambos', () => {
    completarFormulario('ambos');
    component.save();

    expect(apiMock.createProduct).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'ambos',
        salePrice: 12.5,
      }),
    );
  });

  it('edita sin enviar el stock actual y conserva el estado activo', () => {
    const existente = producto({
      id: '45',
      currentStock: 27,
      active: false,
    });

    component.openEdit(existente);
    component.form.patchValue({
      name: 'Producto editado',
      active: false,
      currentStock: 99,
    });

    component.save();

    expect(apiMock.updateProduct).toHaveBeenCalledWith(
      '45',
      expect.objectContaining({
        name: 'Producto editado',
        active: false,
        categoryId: 3,
      }),
    );

    const payload = apiMock.updateProduct.mock.calls[0][1];
    expect(payload).not.toHaveProperty('currentStock');
  });

  it('crea una categoría y la selecciona en el formulario', () => {
    component.openCreate();
    component.toggleCategoryForm();
    component.categoryForm.controls.name.setValue('Nueva');

    component.createCategory();

    expect(apiMock.createCategory).toHaveBeenCalledWith('Nueva');
    expect(component.categories().some((item) => item.id === 5)).toBe(true);
    expect(component.form.controls.categoryId.value).toBe(5);
    expect(component.categoryFormOpen()).toBe(false);
  });

  it('no permite guardar un producto sin categoría válida', () => {
    completarFormulario('venta');
    component.form.controls.categoryId.setValue(0);

    component.save();

    expect(apiMock.createProduct).not.toHaveBeenCalled();
  });
});