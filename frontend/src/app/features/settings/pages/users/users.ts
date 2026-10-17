import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { UserDirectoryService } from '../../../../core/services/user-directory.service';
import { AuditService } from '../../../../core/services/audit.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../../core/services/confirm-dialog.service';
import { User, UserRole } from '../../../../core/models/user.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { DataTable, DataTableColumn } from '../../../../shared/components/data-table/data-table';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';

@Component({
  selector: 'app-users',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField],
  templateUrl: './users.html',
  styleUrl: './users.scss',
})
export class Users {
  userDirectory = inject(UserDirectoryService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private confirmDialog = inject(ConfirmDialogService);
  private fb = inject(FormBuilder);

  formOpen = signal(false);
  editingId = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    fullName: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    role: ['operator' as UserRole, Validators.required],
  });

  columns: DataTableColumn<User>[] = [
    { key: 'fullName', header: 'Nombre', cell: (u) => u.fullName, sortable: true },
    { key: 'email', header: 'Correo', cell: (u) => u.email, sortable: true },
    { key: 'role', header: 'Rol', cell: (u) => (u.role === 'admin' ? 'Administrador' : 'Usuario operativo') },
    { key: 'status', header: 'Estado', cell: (u) => (u.active ? 'Activo' : 'Inactivo') },
  ];

  openCreate(): void {
    this.editingId.set(null);
    this.form.reset({ fullName: '', email: '', role: 'operator' });
    this.formOpen.set(true);
  }

  openEdit(user: User): void {
    this.editingId.set(user.id);
    this.form.reset({ fullName: user.fullName, email: user.email, role: user.role });
    this.formOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const id = this.editingId();
    const actingUser = this.auth.currentUser();

    const request = id
      ? this.userDirectory.updateUser(id, { fullName: raw.fullName, role: raw.role })
      : this.userDirectory.createUser({ fullName: raw.fullName, email: raw.email, role: raw.role });

    request.subscribe(() => {
      this.toast.success(id ? 'Usuario actualizado.' : 'Usuario creado.');
      this.audit.log({
        userId: actingUser?.id ?? '',
        userName: actingUser?.fullName ?? 'Usuario',
        module: 'usuarios',
        action: id ? 'Actualizó usuario' : 'Creó usuario',
        description: `${actingUser?.fullName} ${id ? 'actualizó' : 'creó'} el usuario ${raw.fullName}.`,
      });
      this.formOpen.set(false);
    });
  }

  toggleActive(user: User): void {
    this.confirmDialog
      .confirm({
        title: user.active ? 'Desactivar usuario' : 'Activar usuario',
        message: `¿${user.active ? 'Desactivar' : 'Activar'} a ${user.fullName}?`,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.userDirectory.setActive(user.id, !user.active).subscribe(() => {
          this.toast.success(`Usuario ${user.active ? 'desactivado' : 'activado'}.`);
        });
      });
  }

  close(): void {
    this.formOpen.set(false);
  }
}
