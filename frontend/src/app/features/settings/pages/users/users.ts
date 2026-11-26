import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
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

/** Contraseña temporal que se muestra una sola vez al Administrador. */
interface TemporaryCredentials {
  fullName: string;
  email: string;
  password: string;
}

@Component({
  selector: 'app-users',
  imports: [ReactiveFormsModule, PageHeader, Button, DataTable, Modal, FormField],
  templateUrl: './users.html',
  styleUrl: './users.scss',
})
export class Users implements OnInit {
  userDirectory = inject(UserDirectoryService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private confirmDialog = inject(ConfirmDialogService);
  private fb = inject(FormBuilder);

  formOpen = signal(false);
  editingId = signal<string | null>(null);
  saving = signal(false);
  credentials = signal<TemporaryCredentials | null>(null);

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

  ngOnInit(): void {
    this.userDirectory.load().subscribe();
  }

  isCurrentUser(id: string): boolean {
    return this.auth.currentUser()?.id === id;
  }

  openCreate(): void {
    this.editingId.set(null);
    this.form.reset({ fullName: '', email: '', role: 'operator' });
    this.form.controls.email.enable();
    this.form.controls.role.enable();
    this.formOpen.set(true);
  }

  openEdit(user: User): void {
    this.editingId.set(user.id);
    this.form.reset({ fullName: user.fullName, email: user.email, role: user.role });
    this.form.controls.email.disable();
    // Nadie puede cambiar su propio rol (el backend también lo impide).
    if (this.isCurrentUser(user.id)) this.form.controls.role.disable();
    else this.form.controls.role.enable();
    this.formOpen.set(true);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const id = this.editingId();
    this.saving.set(true);

    if (id) {
      this.userDirectory
        .updateUser(id, { fullName: raw.fullName, role: raw.role })
        .pipe(finalize(() => this.saving.set(false)))
        .subscribe(() => {
          this.toast.success('Usuario actualizado.');
          this.#log('Actualizó usuario', `actualizó el usuario ${raw.fullName}`);
          this.formOpen.set(false);
        });
      return;
    }

    this.userDirectory
      .createUser({ fullName: raw.fullName, email: raw.email, role: raw.role })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe(({ user, temporaryPassword }) => {
        this.#log('Creó usuario', `creó el usuario ${user.fullName}`);
        this.formOpen.set(false);
        if (temporaryPassword) {
          this.credentials.set({
            fullName: user.fullName,
            email: user.email,
            password: temporaryPassword,
          });
        } else {
          // El correo ya tenía cuenta (por otra empresa): entra con su contraseña de siempre.
          this.toast.success(`${user.fullName} ya tenía cuenta: ahora también accede a esta empresa.`);
        }
      });
  }

  toggleActive(user: User): void {
    this.confirmDialog
      .confirm({
        title: user.active ? 'Desactivar usuario' : 'Activar usuario',
        message: user.active
          ? `${user.fullName} ya no podrá entrar a esta empresa. ¿Continuar?`
          : `¿Activar a ${user.fullName}?`,
        danger: user.active,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.userDirectory.setActive(user.id, !user.active).subscribe(() => {
          this.toast.success(`Usuario ${user.active ? 'desactivado' : 'activado'}.`);
          this.formOpen.set(false);
        });
      });
  }

  resetPassword(user: User): void {
    this.confirmDialog
      .confirm({
        title: 'Restablecer contraseña',
        message: `Se generará una contraseña temporal para ${user.fullName} y se cerrarán sus sesiones abiertas. ¿Continuar?`,
        confirmLabel: 'Restablecer',
        danger: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.userDirectory.resetPassword(user.id).subscribe((password) => {
          this.#log('Restableció contraseña', `restableció la contraseña de ${user.fullName}`);
          this.formOpen.set(false);
          this.credentials.set({ fullName: user.fullName, email: user.email, password });
        });
      });
  }

  async copyPassword(): Promise<void> {
    const password = this.credentials()?.password;
    if (!password) return;
    try {
      await navigator.clipboard.writeText(password);
      this.toast.success('Contraseña copiada.');
    } catch {
      this.toast.error('No se pudo copiar. Selecciónala y cópiala a mano.');
    }
  }

  closeCredentials(): void {
    this.credentials.set(null);
  }

  close(): void {
    this.formOpen.set(false);
  }

  #log(action: string, detail: string): void {
    const actingUser = this.auth.currentUser();
    this.audit.log({
      userId: actingUser?.id ?? '',
      userName: actingUser?.fullName ?? 'Usuario',
      module: 'usuarios',
      action,
      description: `${actingUser?.fullName ?? 'Un usuario'} ${detail}.`,
    });
  }
}
