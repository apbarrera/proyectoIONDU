
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { CustomersApiService } from '../../services/customers-api.service';
import {
  Customer,
  IdentificationType,
  UpdateCustomerInput,
} from '../../models/customer.model';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { Icon } from '../../../../shared/components/icon/icon';

const TYPE_LABELS: Record<IdentificationType, string> = {
  cedula: 'Cédula',
  ruc: 'RUC',
  pasaporte: 'Pasaporte',
  exterior: 'Identificación del exterior',
};

const IDENTIFICATION_TYPES: { value: IdentificationType; label: string }[] = [
  { value: 'cedula', label: 'Cédula' },
  { value: 'ruc', label: 'RUC' },
  { value: 'pasaporte', label: 'Pasaporte' },
  { value: 'exterior', label: 'Exterior' },
];

/** Mismas reglas de formato que el backend (`app/schemas/cliente.py`). */
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_PATTERN = /^[0-9+()\s-]*$/;

/** Texto vacío → `null`, para que el backend borre el dato en lugar de guardar un espacio. */
const orNull = (value: string): string | null => value.trim() || null;

@Component({
  selector: 'app-customers',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField, Icon],
  templateUrl: './customers.html',
  styleUrl: './customers.scss',
})
export class Customers {
  private api = inject(CustomersApiService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  readonly trackById = (row: Customer): string => String(row.id);
  readonly identificationTypes = IDENTIFICATION_TYPES;

  customers = signal<Customer[]>([]);
  loading = signal(true);
  saving = signal(false);

  /** `null`: formulario cerrado; `'new'`: cliente nuevo; número: id del cliente que se edita. */
  editing = signal<number | 'new' | null>(null);

  editingCustomer = computed(() => {
    const id = this.editing();
    return typeof id === 'number'
      ? (this.customers().find((c) => c.id === id) ?? null)
      : null;
  });

  form = this.fb.nonNullable.group({
    identificationType: ['cedula' as IdentificationType, Validators.required],
    identification: ['', [Validators.required, Validators.maxLength(20)]],
    name: ['', [Validators.required, Validators.maxLength(255)]],
    address: [''],
    phone: ['', [Validators.maxLength(20), Validators.pattern(PHONE_PATTERN)]],
    email: ['', [Validators.maxLength(150), Validators.pattern(EMAIL_PATTERN)]],
  });

  columns: DataTableColumn<Customer>[] = [
    { key: 'name', header: 'Nombre', cell: (c) => c.name, sortable: true },
    {
      key: 'identification',
      header: 'Identificación',
      cell: (c) => `${TYPE_LABELS[c.identificationType]} ${c.identification}`,
    },
    { key: 'phone', header: 'Teléfono', cell: (c) => c.phone ?? '—' },
    { key: 'email', header: 'Correo', cell: (c) => c.email ?? '—' },
  ];

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.list().subscribe({
      next: (list) => {
        this.customers.set(list);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openNew(): void {
    this.form.reset({
      identificationType: 'cedula',
      identification: '',
      name: '',
      address: '',
      phone: '',
      email: '',
    });
    this.editing.set('new');
  }

  openEdit(customer: Customer): void {
    this.form.reset({
      identificationType: customer.identificationType,
      identification: customer.identification,
      name: customer.name,
      address: customer.address ?? '',
      phone: customer.phone ?? '',
      email: customer.email ?? '',
    });
    this.editing.set(customer.id);
  }

  close(): void {
    this.editing.set(null);
  }

  fieldError(name: keyof typeof this.form.controls): string | null {
    const control = this.form.controls[name];
    if (!control.touched || control.valid) return null;
    if (control.hasError('required')) return 'Este campo es obligatorio.';
    if (control.hasError('pattern')) {
      return name === 'email' ? 'Correo no válido.' : 'Teléfono no válido.';
    }
    return 'Valor demasiado largo.';
  }

  /** Crea o actualiza el cliente. La cédula o el RUC los valida el backend con las reglas del SRI. */
  save(): void {
    if (this.saving()) return;

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    const data = {
      identificationType: value.identificationType,
      identification: value.identification.trim(),
      name: value.name.trim(),
      address: orNull(value.address),
      phone: orNull(value.phone),
      email: orNull(value.email),
    };

    const current = this.editingCustomer();
    let request$: Observable<Customer>;

    if (current) {
      const changes: UpdateCustomerInput = {};

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
        this.customers.update((list) =>
          current
            ? list.map((c) => (c.id === saved.id ? saved : c))
            : [saved, ...list],
        );

        this.toast.success(current ? 'Cliente actualizado.' : 'Cliente registrado.');

        if (saved.identificationWarning) {
          this.toast.warning(saved.identificationWarning);
        }

        this.close();
      },
      // El interceptor ya mostró el motivo del error (por ejemplo, cédula inválida o repetida).
      error: () => this.saving.set(false),
    });
  }
}
