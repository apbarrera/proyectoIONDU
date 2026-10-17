import { Component, OnInit, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DateRange, PERIOD_OPTION_LABELS, PeriodOption, resolveDateRange } from '../../utils/date-range.util';

@Component({
  selector: 'app-period-selector',
  imports: [FormsModule],
  templateUrl: './period-selector.html',
  styleUrl: './period-selector.scss',
})
export class PeriodSelector implements OnInit {
  options: PeriodOption[] = ['hoy', '7dias', 'esteMes', 'mesAnterior', 'personalizado'];
  labels = PERIOD_OPTION_LABELS;

  selected = signal<PeriodOption>('esteMes');
  customFrom = signal(new Date().toISOString().slice(0, 10));
  customTo = signal(new Date().toISOString().slice(0, 10));

  rangeChange = output<DateRange>();

  ngOnInit(): void {
    this.emitRange();
  }

  select(option: PeriodOption): void {
    this.selected.set(option);
    this.emitRange();
  }

  onCustomDateChange(): void {
    if (this.selected() === 'personalizado') this.emitRange();
  }

  private emitRange(): void {
    this.rangeChange.emit(
      resolveDateRange(this.selected(), { from: this.customFrom(), to: this.customTo() }),
    );
  }
}
