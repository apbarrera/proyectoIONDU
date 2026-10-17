import { Component, inject } from '@angular/core';
import { MovementsService } from '../../services/movements.service';
import { InventoryMovement, MovementType } from '../../models/movement.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';

const TYPE_LABELS: Record<MovementType, string> = {
  entrada: 'Entrada',
  salida: 'Salida',
  ajuste: 'Ajuste',
  venta: 'Venta',
  produccion_consumo: 'Consumo de receta',
  produccion_ingreso: 'Fabricación',
};

@Component({
  selector: 'app-movements',
  imports: [PageHeader, DataTable],
  templateUrl: './movements.html',
  styleUrl: './movements.scss',
})
export class Movements {
  movementsService = inject(MovementsService);

  columns: DataTableColumn<InventoryMovement>[] = [
    { key: 'date', header: 'Fecha', cell: (m) => new Date(m.date).toLocaleString('es-EC'), sortable: true },
    { key: 'productName', header: 'Producto', cell: (m) => m.productName, sortable: true },
    { key: 'type', header: 'Tipo', cell: (m) => TYPE_LABELS[m.type] },
    {
      key: 'quantity',
      header: 'Cantidad',
      cell: (m) => `${m.quantity > 0 ? '+' : ''}${m.quantity}`,
      align: 'right',
    },
    { key: 'resultingStock', header: 'Stock resultante', cell: (m) => `${m.resultingStock}`, align: 'right' },
    { key: 'reference', header: 'Motivo', cell: (m) => m.reference },
    { key: 'createdBy', header: 'Usuario', cell: (m) => m.createdBy },
  ];
}
