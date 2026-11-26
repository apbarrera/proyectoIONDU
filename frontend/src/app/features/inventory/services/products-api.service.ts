import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, Observable, expand, map, reduce } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { Product, ProductType } from '../models/product.model';

export interface ProductCategory {
  id: number;
  name: string;
  description: string | null;
}

interface ProductPageDto {
  items: ProductDto[];
  total: number;
  page: number;
  pageSize: number;
}

interface ProductDto {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  categoryId: number;
  categoryName: string;
  type: ProductType;
  unit: string;
  salePrice: number;
  cost: number;
  vatPercentageCode: string;
  appliesVat: boolean;
  currentStock: number;
  minStock: number | null;
  lowStock: boolean;
  active: boolean;
}

export interface CreateProductInput {
  sku: string;
  name: string;
  description?: string | null;
  categoryId: number;
  type: ProductType;
  unit: string;
  salePrice: number | null;
  cost: number;
  currentStock: number;
  minStock: number;
}

export interface UpdateProductInput {
  sku: string;
  name: string;
  description?: string | null;
  categoryId: number;
  type: ProductType;
  unit: string;
  salePrice: number | null;
  cost: number;
  minStock: number;
  active: boolean;
}

@Injectable({ providedIn: 'root' })
export class ProductsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  getCategories(): Observable<ProductCategory[]> {
    return this.http.get<ProductCategory[]>(`${this.baseUrl}/product-categories`);
  }

  createCategory(name: string): Observable<ProductCategory> {
    return this.http.post<ProductCategory>(`${this.baseUrl}/product-categories`, {
      name: name.trim(),
    });
  }

  getProducts(): Observable<Product[]> {
    const getPage = (page: number) =>
      this.http.get<ProductPageDto>(`${this.baseUrl}/products`, {
        params: new HttpParams().set('page', page).set('pageSize', 100),
      });

    return getPage(1).pipe(
      expand((result) =>
        result.page * result.pageSize < result.total
          ? getPage(result.page + 1)
          : EMPTY,
      ),
      reduce((all, result) => [...all, ...result.items], [] as ProductDto[]),
      map((items) => items.map((item) => this.toProduct(item))),
    );
  }

  createProduct(input: CreateProductInput): Observable<Product> {
    const body = {
      sku: input.sku,
      name: input.name,
      description: input.description ?? null,
      categoryId: input.categoryId,
      type: input.type,
      unit: input.unit,
      salePrice: input.salePrice ?? 0,
      cost: input.cost,
      currentStock: input.currentStock,
      minStock: input.minStock,
    };

    return this.http
      .post<ProductDto>(`${this.baseUrl}/products`, body)
      .pipe(map((item) => this.toProduct(item)));
  }

  updateProduct(id: string, input: UpdateProductInput): Observable<Product> {
    const body = {
      sku: input.sku,
      name: input.name,
      description: input.description ?? null,
      categoryId: input.categoryId,
      type: input.type,
      unit: input.unit,
      salePrice: input.salePrice ?? 0,
      cost: input.cost,
      minStock: input.minStock,
      active: input.active,
    };

    return this.http
      .patch<ProductDto>(`${this.baseUrl}/products/${encodeURIComponent(id)}`, body)
      .pipe(map((item) => this.toProduct(item)));
  }

  private toProduct(dto: ProductDto): Product {
    return {
      id: String(dto.id),
      sku: dto.sku,
      name: dto.name,
      description: dto.description,
      category: dto.categoryName,
      categoryId: dto.categoryId,
      type: dto.type,
      unit: dto.unit,
      salePrice: dto.type === 'insumo' ? null : dto.salePrice,
      vatPercentageCode: dto.vatPercentageCode,
      cost: dto.cost,
      currentStock: dto.currentStock,
      minStock: dto.minStock ?? 0,
      active: dto.active,
    };
  }
}
