import { buildImportRows, buildTemplateCsv, buildTemplateXlsx, parseCsv } from './product-import.util';

const HEADER = ['Código', 'Nombre', 'Categoría', 'Tipo', 'Unidad', 'Precio de venta', 'Costo', 'Stock actual', 'Stock mínimo'];

describe('parseCsv', () => {
  it('detecta punto y coma, comillas y BOM', () => {
    const rows = parseCsv('﻿Nombre;Categoría\r\n"Torta; grande";"Dice ""hola"""\r\n');
    expect(rows).toEqual([
      ['Nombre', 'Categoría'],
      ['Torta; grande', 'Dice "hola"'],
    ]);
  });

  it('lee comas y saltos de línea dentro de comillas', () => {
    expect(parseCsv('a,b\n"x\ny",2')).toEqual([
      ['a', 'b'],
      ['x\ny', '2'],
    ]);
  });
});

describe('buildImportRows', () => {
  it('convierte filas válidas con valores por defecto', () => {
    const { rows, fileErrors } = buildImportRows([HEADER, ['', 'Café', 'Bebidas', '', '', '6,50', '3.2', '18', '']], []);
    expect(fileErrors).toEqual([]);
    expect(rows[0].errors).toEqual([]);
    expect(rows[0].product).toEqual({
      sku: '',
      name: 'Café',
      category: 'Bebidas',
      type: 'simple',
      unit: 'unidad',
      salePrice: 6.5,
      cost: 3.2,
      currentStock: 18,
      minStock: 0,
      active: true,
    });
  });

  it('ignora el precio de los insumos', () => {
    const { rows } = buildImportRows([HEADER, ['', 'Harina', 'Secos', 'Insumo', 'kg', 9, 1, 5, 2]], []);
    expect(rows[0].product?.type).toBe('insumo');
    expect(rows[0].product?.salePrice).toBeNull();
  });

  it('acepta los encabezados en otro orden, sin tildes ni mayúsculas', () => {
    const { rows } = buildImportRows([['CATEGORIA', 'nombre'], ['Bebidas', 'Café']], []);
    expect(rows[0].product).toMatchObject({ name: 'Café', category: 'Bebidas' });
  });

  it('reporta los errores por fila con su número', () => {
    const { rows } = buildImportRows(
      [HEADER, ['', '', 'Bebidas', 'Servicio', '', 'abc', '-1', '', ''], ['', 'Ok', 'Bebidas', '', '', '', '', '', '']],
      [],
    );
    expect(rows[0].product).toBeNull();
    expect(rows[0].line).toBe(2);
    expect(rows[0].errors).toEqual([
      'Falta el nombre.',
      'Tipo no válido: usa Producto o Insumo.',
      'El precio de venta no es un número.',
      'El costo no puede ser negativo.',
    ]);
    expect(rows[1].product).not.toBeNull();
  });

  it('detecta códigos repetidos en el archivo o ya existentes', () => {
    const { rows } = buildImportRows(
      [HEADER, ['PS-001', 'A', 'X', '', '', '', '', '', ''], ['ps-009', 'B', 'X', '', '', '', '', '', ''], ['PS-009', 'C', 'X', '', '', '', '', '', '']],
      ['PS-001'],
    );
    expect(rows.map((r) => r.errors.length)).toEqual([1, 0, 1]);
  });

  it('interpreta miles y decimales con coma o punto', () => {
    const { rows } = buildImportRows([HEADER, ['', 'A', 'X', '', '', '$1.234,50', '1,234.5', '', '']], []);
    expect(rows[0].product).toMatchObject({ salePrice: 1234.5, cost: 1234.5 });
  });

  it('rechaza archivos sin las columnas obligatorias o sin filas', () => {
    expect(buildImportRows([['Nombre']], []).fileErrors[0]).toContain('Categoría');
    expect(buildImportRows([HEADER], []).fileErrors[0]).toContain('no tiene productos');
    expect(buildImportRows([], []).fileErrors).toEqual(['El archivo está vacío.']);
  });

  it('omite las filas completamente vacías', () => {
    const { rows } = buildImportRows([HEADER, [], ['', 'A', 'X'], ['', '', '']], []);
    expect(rows).toHaveLength(1);
    expect(rows[0].line).toBe(3);
  });
});

describe('plantilla', () => {
  it('el CSV de la plantilla se lee de vuelta sin errores', () => {
    const { rows, fileErrors } = buildImportRows(parseCsv(buildTemplateCsv()), []);
    expect(fileErrors).toEqual([]);
    expect(rows).toHaveLength(2);
    expect(rows.every((r) => r.errors.length === 0)).toBe(true);
  });

  it('el Excel de la plantilla se genera como un .xlsx', async () => {
    const blob = await buildTemplateXlsx();
    expect(blob.size).toBeGreaterThan(0);
    const header = new Uint8Array(await blob.arrayBuffer()).slice(0, 2);
    expect(String.fromCharCode(...header)).toBe('PK');
  });
});
