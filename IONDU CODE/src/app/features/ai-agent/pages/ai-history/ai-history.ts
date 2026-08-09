import { Component, inject } from '@angular/core';
import { AiAgentService } from '../../services/ai-agent.service';
import { AiInteraction } from '../../models/ai-message.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';

const RESULT_LABELS: Record<AiInteraction['result'], string> = {
  pendiente: 'Pendiente',
  confirmado: 'Confirmado',
  corregido: 'Corregido',
  cancelado: 'Cancelado',
};

@Component({
  selector: 'app-ai-history',
  imports: [PageHeader, DataTable],
  templateUrl: './ai-history.html',
  styleUrl: './ai-history.scss',
})
export class AiHistory {
  aiAgent = inject(AiAgentService);

  columns: DataTableColumn<AiInteraction>[] = [
    { key: 'timestamp', header: 'Fecha', cell: (i) => new Date(i.timestamp).toLocaleString('es-EC'), sortable: true },
    { key: 'userName', header: 'Usuario', cell: (i) => i.userName, sortable: true },
    { key: 'inputType', header: 'Entrada', cell: (i) => i.inputType },
    { key: 'instruction', header: 'Instrucción', cell: (i) => i.instruction },
    { key: 'interpretedData', header: 'Datos interpretados', cell: (i) => i.interpretedData },
    { key: 'result', header: 'Resultado', cell: (i) => RESULT_LABELS[i.result] },
  ];
}
