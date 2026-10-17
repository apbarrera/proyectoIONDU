import { Injectable, inject } from '@angular/core';
import { AiProposal } from '../models/ai-message.model';
import { ProductsService } from '../../inventory/services/products.service';
import { generateId } from '../../../core/utils/id.util';

const CATEGORY_KEYWORDS: Record<string, string> = {
  empaque: 'Empaques',
  frasco: 'Empaques',
  caja: 'Empaques',
  insumo: 'Insumos',
  harina: 'Insumos',
  azúcar: 'Insumos',
  azucar: 'Insumos',
  chocolate: 'Insumos',
  luz: 'Servicios',
  electric: 'Servicios',
  agua: 'Servicios',
  internet: 'Servicios',
  arriendo: 'Arriendo',
  renta: 'Arriendo',
};

export interface NluResult {
  interpretedData: string;
  proposal: AiProposal | null;
  clarifyingQuestion: string | null;
}

/** Keyword/regex mock NLU — stands in for a real LLM/NLU provider until one is connected. */
@Injectable({ providedIn: 'root' })
export class AiNluMockService {
  private products = inject(ProductsService);

  interpret(text: string): NluResult {
    const normalized = text.toLowerCase();

    const productMatch = this.products
      .products()
      .find((p) => normalized.includes(p.name.toLowerCase()) || normalized.includes(p.sku.toLowerCase()));

    const quantityMatch = normalized.match(/(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml|unidades?|frascos?|cajas?)?/);
    const amountMatch = normalized.match(/\$\s?(\d+(?:[.,]\d{1,2})?)|(\d+(?:[.,]\d{1,2})?)\s?(?:dólares|dolares|usd)/);

    const isInventoryIntent = /compr|recib|agregar|ingres|reposic/.test(normalized) && productMatch && quantityMatch;
    const isExpenseIntent = /gast|pagu|pagué|factura|compr/.test(normalized) && amountMatch;

    if (isInventoryIntent && productMatch && quantityMatch) {
      const quantity = Number(quantityMatch[1].replace(',', '.'));
      const proposal: AiProposal = {
        id: generateId(),
        type: 'inventory',
        summary: `Aumentar el stock de ${productMatch.name} en ${quantity} ${productMatch.unit}.`,
        inventory: { productId: productMatch.id, productName: productMatch.name, quantityDelta: quantity, unit: productMatch.unit },
      };
      return {
        interpretedData: `Inventario: ${productMatch.name} — +${quantity} ${productMatch.unit}`,
        proposal,
        clarifyingQuestion: null,
      };
    }

    if (isExpenseIntent && amountMatch) {
      const amount = Number((amountMatch[1] ?? amountMatch[2]).replace(',', '.'));
      const categoryEntry = Object.entries(CATEGORY_KEYWORDS).find(([keyword]) => normalized.includes(keyword));
      const category = categoryEntry?.[1] ?? 'Otros';

      const proposal: AiProposal = {
        id: generateId(),
        type: 'expense',
        summary: `Registrar gasto de $${amount.toFixed(2)} en la categoría ${category}.`,
        expense: { category, providerName: 'Proveedor no especificado', amount },
      };
      return {
        interpretedData: `Gasto: ${category} — $${amount.toFixed(2)}`,
        proposal,
        clarifyingQuestion: null,
      };
    }

    return {
      interpretedData: 'No se detectaron cambios de gasto o inventario.',
      proposal: null,
      clarifyingQuestion:
        '¿Podrías indicarme el monto y si se trata de un gasto o de una entrada de inventario? Por ejemplo: "Compré 5 frascos por $12,50".',
    };
  }
}
