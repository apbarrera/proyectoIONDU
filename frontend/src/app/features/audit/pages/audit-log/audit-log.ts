import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuditService } from '../../../../core/services/audit.service';
import { AuditEntry, AuditModule } from '../../../../core/models/audit.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Button } from '../../../../shared/components/button/button';
import { FormField } from '../../../../shared/components/form-field/form-field';

export const MODULE_LABELS: Record<AuditModule, string> = {
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
  imports: [ReactiveFormsModule, PageHeader, DataTable, Button, FormField],
  templateUrl: './audit-log.html',
  styleUrl: './audit-log.scss',
})
export class AuditLog implements OnInit {
  auditService = inject(AuditService);
  private fb = inject(FormBuilder);

  loading = signal(false);
  modules = Object.entries(MODULE_LABELS) as [AuditModule, string][];

  filters = this.fb.nonNullable.group({
    module: '' as AuditModule | '',
    from: '',
    to: '',
  });

  columns: DataTableColumn<AuditEntry>[] = [
    { key: 'timestamp', header: 'Fecha', cell: (e) => new Date(e.timestamp).toLocaleString('es-EC'), sortable: true },
    { key: 'userName', header: 'Usuario', cell: (e) => e.userName, sortable: true },
    { key: 'module', header: 'Módulo', cell: (e) => MODULE_LABELS[e.module] },
    { key: 'action', header: 'Acción', cell: (e) => e.action },
    { key: 'description', header: 'Descripción', cell: (e) => e.description },
  ];

  ngOnInit(): void {
    this.search();
  }

  search(): void {
    const { module, from, to } = this.filters.getRawValue();
    this.loading.set(true);
    this.auditService
      .load({ module: module || null, from: from || null, to: to || null })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe();
  }

  clearFilters(): void {
    this.filters.reset({ module: '', from: '', to: '' });
    this.search();
  }

  loadMore(): void {
    this.loading.set(true);
    this.auditService
      .loadMore()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe();
  }
}
