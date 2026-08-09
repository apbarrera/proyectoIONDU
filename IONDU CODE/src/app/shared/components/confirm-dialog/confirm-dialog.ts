import { Component, inject } from '@angular/core';
import { Modal } from '../modal/modal';
import { Button } from '../button/button';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';

@Component({
  selector: 'app-confirm-dialog',
  imports: [Modal, Button],
  templateUrl: './confirm-dialog.html',
  styleUrl: './confirm-dialog.scss',
})
export class ConfirmDialog {
  service = inject(ConfirmDialogService);

  resolve(value: boolean): void {
    this.service.resolve(value);
  }
}
