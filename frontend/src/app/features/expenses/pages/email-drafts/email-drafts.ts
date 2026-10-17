import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ExpenseInboxService } from '../../services/expense-inbox.service';
import { EmailExpenseDraft } from '../../models/email-draft.model';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../../core/services/confirm-dialog.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';

const CATEGORIES = ['Insumos', 'Servicios', 'Empaques', 'Arriendo', 'Nómina', 'Marketing', 'Otros'];

@Component({
  selector: 'app-email-drafts',
  imports: [ReactiveFormsModule, PageHeader, Button, EmptyState, Modal, FormField],
  templateUrl: './email-drafts.html',
  styleUrl: './email-drafts.scss',
})
export class EmailDrafts {
  inbox = inject(ExpenseInboxService);
  private toast = inject(ToastService);
  private confirmDialog = inject(ConfirmDialogService);
  private fb = inject(FormBuilder);

  categories = CATEGORIES;
  pending = () => this.inbox.drafts().filter((d) => d.status === 'pendiente');

  reviewing = signal<EmailExpenseDraft | null>(null);

  form = this.fb.nonNullable.group({
    providerName: ['', Validators.required],
    providerRuc: ['', Validators.required],
    amount: [0, [Validators.required, Validators.min(0.01)]],
    category: ['Insumos', Validators.required],
  });

  open(draft: EmailExpenseDraft): void {
    this.reviewing.set(draft);
    this.form.reset({
      providerName: draft.parsedProviderName,
      providerRuc: draft.parsedProviderRuc,
      amount: draft.parsedAmount,
      category: draft.parsedCategory,
    });
  }

  close(): void {
    this.reviewing.set(null);
  }

  confirm(): void {
    const draft = this.reviewing();
    if (!draft || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.inbox.confirmDraft(draft.id, this.form.getRawValue()).subscribe(() => {
      this.toast.success('Gasto confirmado desde la factura recibida.');
      this.close();
    });
  }

  discard(draft: EmailExpenseDraft): void {
    this.confirmDialog
      .confirm({
        title: 'Descartar factura detectada',
        message: `¿Descartar la factura de "${draft.parsedProviderName}"? No se creará ningún gasto.`,
        danger: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.inbox.discardDraft(draft.id).subscribe(() => this.toast.info('Factura descartada.'));
      });
  }
}
