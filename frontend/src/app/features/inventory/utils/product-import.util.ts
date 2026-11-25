import { Product, ProductType } from '../models/product.model';

export type ImportFormat = 'csv' | 'xlsx';

export const IMPORT_MAX_ROWS = 1000;
export const IMPORT_MAX_BYTES = 2 * 1024 * 1024;

/** Orden de columnas de la plantilla. Nombre y Categoría son obligatorias. */
export const TEMPLATE_HEADERS = [
  'Código',
  'Nombre',
  'Categoría',
  'Tipo',
  'Unidad',
  'Precio de venta',
  'Costo',
  'Stock actual',
  'Stock mínimo',
] as const;

type ColumnKey = 'sku' | 'name' | 'category' | 'type' | 'unit' | 'salePrice' | 'cost' | 'currentStock' | 'minStock';

/** Encabezados aceptados (sin tildes, mayúsculas ni signos) para cada columna. */
const HEADER_ALIASES: Record<string, ColumnKey> = {
  codigo: 'sku',
  sku: 'sku',
  nombre: 'name',
  producto: 'name',
  categoria: 'category',
  tipo: 'type',
  unidad: 'unit',
  preciodeventa: 'salePrice',
  precioventa: 'salePrice',
  precio: 'salePrice',
  costo: 'cost',
  stockactual: 'currentStock',
  stock: 'currentStock',
  stockminimo: 'minStock',
  minimo: 'minStock',
};

const TEMPLATE_EXAMPLES: (string | number)[][] = [
  ['', 'Café Molido 250g', 'Bebidas', 'Producto', 'unidad', 6.5, 3.2, 18, 6],
  ['IN-050', 'Harina de Trigo', 'Insumos secos', 'Insumo', 'kg', '', 1.1, 42, 15],
];

const INSTRUCTIONS: string[][] = [
  ['Columna', 'Obligatoria', 'Qué poner'],
  ['Código', 'No', 'Déjalo vacío y el sistema lo genera (PS-001 para productos, IN-001 para insumos).'],
  ['Nombre', 'Sí', 'Nombre del producto o insumo.'],
  ['Categoría', 'Sí', 'Cualquier texto. Si no existe, se crea al importar.'],
  ['Tipo', 'No', 'Producto o Insumo. Si lo dejas vacío se toma Producto.'],
  ['Unidad', 'No', 'unidad, kg, L, g… Si lo dejas vacío se toma unidad.'],
  ['Precio de venta', 'No', 'Solo para productos. Los insumos no se venden, se ignora.'],
  ['Costo', 'No', 'Número con punto o coma decimal. Vacío = 0.'],
  ['Stock actual', 'No', 'Existencias que tienes hoy. Vacío = 0.'],
  ['Stock mínimo', 'No', 'Cantidad a partir de la cual se avisa de stock bajo. Vacío = 0.'],
  [],
  ['Antes de importar, borra las dos filas de ejemplo de la hoja "Productos". Máximo 1000 filas por archivo.'],
];

export type ImportedProduct = Omit<Product, 'id'>;

export interface ImportRow {
  /** Número de fila en el archivo (la fila 1 es el encabezado). */
  line: number;
  product: ImportedProduct | null;
  errors: string[];
}

export interface ImportParseResult {
  rows: ImportRow[];
  /** Problemas que impiden leer el archivo completo (columnas faltantes, demasiadas filas…). */
  fileErrors: string[];
}

function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

function cellText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value).trim();
}

/** Devuelve el número, `null` si la celda está vacía o `NaN` si no es un número válido. */
function parseNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : NaN;
  let text = cellText(value).replace(/[$\s]/g, '');
  if (text === '') return null;
  const lastComma = text.lastIndexOf(',');
  const lastDot = text.lastIndexOf('.');
  if (lastComma >= 0 && lastDot >= 0) {
    // El separador que aparece al final es el decimal; el otro agrupa miles.
    text = lastComma > lastDot ? text.replace(/\./g, '').replace(',', '.') : text.replace(/,/g, '');
  } else if (lastComma >= 0) {
    text = text.replace(',', '.');
  }
  return /^-?\d+(\.\d+)?$/.test(text) ? Number(text) : NaN;
}

function parseType(value: unknown): ProductType | null {
  const text = normalize(cellText(value));
  if (['', 'producto', 'productos', 'simple', 'productosimple'].includes(text)) return 'simple';
  if (['insumo', 'insumos'].includes(text)) return 'insumo';
  return null;
}

/** Lee texto CSV (comas, punto y coma o tabulaciones; comillas dobles; BOM) a una tabla. */
export function parseCsv(input: string): string[][] {
  const text = input.replace(/^﻿/, '');
  const firstLine = text.split(/\r?\n/, 1)[0] ?? '';
  const delimiter = [';', '\t', ','].reduce(
    (best, d) => (firstLine.split(d).length > firstLine.split(best).length ? d : best),
    ',',
  );

  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i++;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === delimiter) {
      row.push(field);
      field = '';
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else {
      field += char;
    }
  }
  if (field !== '' || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

/**
 * Valida una tabla (la primera fila es el encabezado) y la convierte en productos.
 * `existingSkus` son los códigos que ya existen, para detectar repetidos.
 */
export function buildImportRows(table: unknown[][], existingSkus: Iterable<string>): ImportParseResult {
  const fileErrors: string[] = [];
  const rows: ImportRow[] = [];

  if (table.length === 0) return { rows, fileErrors: ['El archivo está vacío.'] };

  const columns = new Map<ColumnKey, number>();
  table[0].forEach((header, index) => {
    const key = HEADER_ALIASES[normalize(cellText(header))];
    if (key && !columns.has(key)) columns.set(key, index);
  });
  for (const [key, label] of [['name', 'Nombre'], ['category', 'Categoría']] as const) {
    if (!columns.has(key)) fileErrors.push(`Falta la columna "${label}". Descarga la plantilla para ver el formato.`);
  }
  if (fileErrors.length > 0) return { rows, fileErrors };

  const dataRows = table.slice(1).map((cells, index) => ({ cells, line: index + 2 }));
  const filled = dataRows.filter(({ cells }) => cells.some((c) => cellText(c) !== ''));
  if (filled.length === 0) return { rows, fileErrors: ['El archivo no tiene productos debajo del encabezado.'] };
  if (filled.length > IMPORT_MAX_ROWS) {
    return { rows, fileErrors: [`El archivo tiene ${filled.length} filas; el máximo es ${IMPORT_MAX_ROWS}.`] };
  }

  const seenSkus = new Set<string>();
  for (const sku of existingSkus) seenSkus.add(sku.toLowerCase());

  const get = (cells: unknown[], key: ColumnKey): unknown => {
    const index = columns.get(key);
    return index === undefined ? undefined : cells[index];
  };

  for (const { cells, line } of filled) {
    const errors: string[] = [];

    const name = cellText(get(cells, 'name'));
    const category = cellText(get(cells, 'category'));
    if (!name) errors.push('Falta el nombre.');
    if (!category) errors.push('Falta la categoría.');

    const type = parseType(get(cells, 'type'));
    if (!type) errors.push('Tipo no válido: usa Producto o Insumo.');

    const numbers: Record<'salePrice' | 'cost' | 'currentStock' | 'minStock', number | null> = {
      salePrice: null,
      cost: null,
      currentStock: null,
      minStock: null,
    };
    const labels = { salePrice: 'precio de venta', cost: 'costo', currentStock: 'stock actual', minStock: 'stock mínimo' };
    for (const key of Object.keys(numbers) as (keyof typeof numbers)[]) {
      const value = parseNumber(get(cells, key));
      if (value !== null && Number.isNaN(value)) errors.push(`El ${labels[key]} no es un número.`);
      else if (value !== null && value < 0) errors.push(`El ${labels[key]} no puede ser negativo.`);
      else numbers[key] = value;
    }

    const sku = cellText(get(cells, 'sku'));
    if (sku) {
      if (seenSkus.has(sku.toLowerCase())) errors.push(`El código ${sku} ya existe o está repetido.`);
      else seenSkus.add(sku.toLowerCase());
    }

    rows.push({
      line,
      errors,
      product:
        errors.length > 0 || !type
          ? null
          : {
              sku,
              name,
              category,
              type,
              unit: cellText(get(cells, 'unit')) || 'unidad',
              salePrice: type === 'insumo' ? null : (numbers.salePrice ?? 0),
              cost: numbers.cost ?? 0,
              currentStock: numbers.currentStock ?? 0,
              minStock: numbers.minStock ?? 0,
              active: true,
            },
    });
  }
  return { rows, fileErrors };
}

export async function readImportFile(file: File, format: ImportFormat, existingSkus: Iterable<string>): Promise<ImportParseResult> {
  if (file.size > IMPORT_MAX_BYTES) {
    return { rows: [], fileErrors: ['El archivo pesa más de 2 MB. Divídelo en partes más pequeñas.'] };
  }
  try {
    if (format === 'csv') {
      return buildImportRows(parseCsv(await file.text()), existingSkus);
    }
    const { readSheet } = await import('read-excel-file/universal');
    return buildImportRows(await readSheet(file), existingSkus);
  } catch {
    const kind = format === 'csv' ? 'CSV' : 'Excel (.xlsx)';
    return { rows: [], fileErrors: [`No se pudo leer el archivo. Comprueba que sea un ${kind} válido.`] };
  }
}

/** CSV con punto y coma y BOM: es lo que Excel en español abre en columnas separadas. */
export function buildTemplateCsv(): string {
  const quote = (value: string | number) => {
    const text = String(value);
    return /[;"\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [TEMPLATE_HEADERS as readonly string[], ...TEMPLATE_EXAMPLES].map((row) => row.map(quote).join(';'));
  return '﻿' + lines.join('\r\n') + '\r\n';
}

export async function buildTemplateXlsx(): Promise<Blob> {
  const { default: writeXlsxFile } = await import('write-excel-file/universal');
  const header = TEMPLATE_HEADERS.map((value) => ({ value, fontWeight: 'bold' as const }));
  const instructions = INSTRUCTIONS.map((row, index) =>
    index === 0 ? row.map((value) => ({ value, fontWeight: 'bold' as const })) : row,
  );
  return writeXlsxFile(
    [
      {
        sheet: 'Productos',
        data: [header, ...TEMPLATE_EXAMPLES.map((row) => row.map((v) => (v === '' ? null : v)))],
        columns: [{ width: 12 }, { width: 28 }, { width: 18 }, { width: 12 }, { width: 10 }, { width: 16 }, { width: 10 }, { width: 14 }, { width: 14 }],
        stickyRowsCount: 1,
      },
      { sheet: 'Instrucciones', data: instructions, columns: [{ width: 18 }, { width: 12 }, { width: 80 }] },
    ],
  ).toBlob();
}
