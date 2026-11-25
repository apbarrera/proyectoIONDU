import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { SuppliersApiService, UpdateSupplierInput } from '../../services/suppliers-api.service';
import { Supplier } from '../../models/expense.model';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Icon } from '../../../../shared/components/icon/icon';

/** Validación preliminar de longitud; el backend valida la identificación con las reglas del SRI. */
const IDENTIFICATION_PATTERN = /^(\d{10}|\d{13})$/;
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_PATTERN = /^[0-9+()\s-]*$/;

/** Texto vacío → `null`, para que el backend borre el dato en lugar de guardar un espacio. */
const orNull = (value: string): string | null => value.trim() || null;

@Component({
  selector: 'app-suppliers',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField, Icon],
  templateUrl: './suppliers.html',
  styleUrl: './suppliers.scss',
})
export class Suppliers {
  private api = inject(SuppliersApiService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  readonly trackById = (row: Supplier): string => String(row.id);

  suppliers = signal<Supplier[]>([]);
  loading = signal(true);
  saving = signal(false);

  /** `null`: formulario cerrado; `'new'`: proveedor nuevo; número: id del proveedor que se edita. */
  editing = signal<number | 'new' | null>(null);

  editingSupplier = computed(() => {
    const id = this.editing();
    return typeof id === 'number' ? (this.suppliers().find((s) => s.id === id) ?? null) : null;
  });

  form = this.fb.nonNullable.group({
    identification: ['', [Validators.required, Validators.pattern(IDENTIFICATION_PATTERN)]],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    address: [''],
    phone: ['', [Validators.maxLength(20), Validators.pattern(PHONE_PATTERN)]],
    email: ['', [Validators.maxLength(150), Validators.pattern(EMAIL_PATTERN)]],
  });

  columns: DataTableColumn<Supplier>[] = [
    { key: 'name', header: 'Nombre', cell: (s) => s.name, sortable: true },
    { key: 'identification', header: 'RUC o cédula', cell: (s) => s.identification },
    { key: 'phone', header: 'Teléfono', cell: (s) => s.phone ?? '—' },
    { key: 'email', header: 'Correo', cell: (s) => s.email ?? '—' },
  ];

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.list().subscribe({
      next: (list) => {
        this.suppliers.set(list);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openNew(): void {
    this.form.reset({ identification: '', name: '', address: '', phone: '', email: '' });
    this.editing.set('new');
  }

  openEdit(supplier: Supplier): void {
    this.form.reset({
      identification: supplier.identification,
      name: supplier.name,
      address: supplier.address ?? '',
      phone: supplier.phone ?? '',
      email: supplier.email ?? '',
    });
    this.editing.set(supplier.id);
  }

  close(): void {
    this.editing.set(null);
  }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!control.touched || control.valid) return null;
    if (control.hasError('required')) return 'Este campo es obligatorio.';
    if (control.hasError('pattern')) {
      if (name === 'identification') return 'Debe tener 10 dígitos (cédula) o 13 (RUC).';
      return name === 'email' ? 'Correo no válido.' : 'Teléfono no válido.';
    }
    return 'Valor demasiado largo.';
  }

  /** Crea o actualiza el proveedor. El RUC o la cédula los valida el backend con las reglas del SRI. */
  save(): void {
    if (this.saving()) return;

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    const data = {
      identification: value.identification.trim(),
      name: value.name.trim(),
      address: orNull(value.address),
      phone: orNull(value.phone),
      email: orNull(value.email),
    };

    const current = this.editingSupplier();
    let request$: Observable<Supplier>;

    if (current) {
      const changes: UpdateSupplierInput = {};
      for (const key of Object.keys(data) as (keyof typeof data)[]) {
        if (data[key] !== current[key]) {
          (changes as Record<string, string | null>)[key] = data[key];
        }
      }
      if (!Object.keys(changes).length) {
        this.close();
        return;
      }
      request$ = this.api.update(current.id, changes);
    } else {
      request$ = this.api.create(data);
    }

    this.saving.set(true);
    request$.subscribe({
      next: (saved) => {
        this.saving.set(false);
        this.suppliers.update((list) =>
          current ? list.map((s) => (s.id === saved.id ? saved : s)) : [saved, ...list],
        );
        this.toast.success(current ? 'Proveedor actualizado.' : 'Proveedor registrado.');
        if (saved.identificationWarning) this.toast.warning(saved.identificationWarning);
        this.close();
      },
      // El interceptor ya mostró el motivo del error (por ejemplo, RUC inválido o repetido).
      error: () => this.saving.set(false),
    });
  }
}
