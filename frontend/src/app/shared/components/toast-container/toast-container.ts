import { Component, inject } from '@angular/core';
import { ToastService } from '../../../core/services/toast.service';
import { Icon } from '../icon/icon';
import { IconName } from '../../icons/icons.generated';

@Component({
  selector: 'app-toast-container',
  imports: [Icon],
  templateUrl: './toast-container.html',
  styleUrl: './toast-container.scss',
})
export class ToastContainer {
  toastService = inject(ToastService);

  iconFor(type: string): IconName {
    switch (type) {
      case 'success':
        return 'check-circle';
      case 'error':
        return 'warning-circle';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  }
}
