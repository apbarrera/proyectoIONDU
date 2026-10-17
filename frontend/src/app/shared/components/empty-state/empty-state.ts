import { Component, input } from '@angular/core';
import { Icon } from '../icon/icon';
import { IconName } from '../../icons/icons.generated';

@Component({
  selector: 'app-empty-state',
  imports: [Icon],
  templateUrl: './empty-state.html',
  styleUrl: './empty-state.scss',
})
export class EmptyState {
  icon = input<IconName>('mailbox');
  title = input.required<string>();
  description = input<string>();
}
