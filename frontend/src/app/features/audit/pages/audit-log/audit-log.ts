import { Component, inject } from '@angular/core';
import { AuditService } from '../../../../core/services/audit.service';
import { AuditEntry, AuditModule } from '../../../../core/models/audit.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';

const MODULE_LABELS: Record<AuditModule, string> = {
  auth: 'Autenticación',
  ventas: 'Ventas',
  facturacion: 'Facturación',
  gastos: 'Gastos',
  inventario: 'Inventario',
  ia: 'Agente IA',
  configuracion: 'Configuración',
  usuarios: 'Usuarios',
};

@Component({
  selector: 'app-audit-log',
  imports: [PageHeader, DataTable],
  templateUrl: './audit-log.html',
  styleUrl: './audit-log.scss',
})
export class AuditLog {
  auditService = inject(AuditService);

  columns: DataTableColumn<AuditEntry>[] = [
    { key: 'timestamp', header: 'Fecha', cell: (e) => new Date(e.timestamp).toLocaleString('es-EC'), sortable: true },
    { key: 'userName', header: 'Usuario', cell: (e) => e.userName, sortable: true },
    { key: 'module', header: 'Módulo', cell: (e) => MODULE_LABELS[e.module] },
    { key: 'action', header: 'Acción', cell: (e) => e.action },
    { key: 'description', header: 'Descripción', cell: (e) => e.description },
  ];
}
