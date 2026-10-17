import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PageRequest } from '../../../core/models/pagination.model';
import { Loader } from '../loader/loader';
import { EmptyState } from '../empty-state/empty-state';
import { Icon } from '../icon/icon';
import { BadgeTone, StatusBadge } from '../status-badge/status-badge';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  /** Texto de la celda; también se usa para buscar y ordenar. */
  cell: (row: T) => string;
  /** Si devuelve un valor, la celda se muestra como etiqueta de estado en vez de texto plano. */
  badge?: (row: T) => { label: string; tone: BadgeTone } | null;
  sortable?: boolean;
  align?: 'left' | 'right' | 'center';
}

@Component({
  selector: 'app-data-table',
  imports: [FormsModule, Loader, EmptyState, Icon, StatusBadge],
  templateUrl: './data-table.html',
  styleUrl: './data-table.scss',
})
export class DataTable<T> {
  columns = input.required<DataTableColumn<T>[]>();
  rows = input.required<T[]>();
  loading = input(false);
  pageSize = input(10);
  searchPlaceholder = input('Buscar…');
  emptyTitle = input('No hay registros todavía.');
  trackBy = input<(row: T) => string>((row) => JSON.stringify(row));
  clickableRows = input(false);

  pageChange = output<PageRequest>();
  rowClick = output<T>();

  search = signal('');
  sortField = signal<string | null>(null);
  sortDir = signal<'asc' | 'desc'>('asc');
  page = signal(1);

  filteredRows = computed(() => {
    const term = this.search().trim().toLowerCase();
    let list = this.rows();
    if (term) {
      list = list.filter((row) =>
        this.columns().some((col) => col.cell(row).toLowerCase().includes(term)),
      );
    }
    const field = this.sortField();
    if (field) {
      const col = this.columns().find((c) => c.key === field);
      if (col) {
        const dir = this.sortDir() === 'asc' ? 1 : -1;
        list = [...list].sort((a, b) => col.cell(a).localeCompare(col.cell(b)) * dir);
      }
    }
    return list;
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filteredRows().length / this.pageSize())));

  pagedRows = computed(() => {
    const start = (this.page() - 1) * this.pageSize();
    return this.filteredRows().slice(start, start + this.pageSize());
  });

  onSearch(term: string): void {
    this.search.set(term);
    this.page.set(1);
    this.emitPageRequest();
  }

  toggleSort(col: DataTableColumn<T>): void {
    if (!col.sortable) return;
    if (this.sortField() === col.key) {
      this.sortDir.set(this.sortDir() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortField.set(col.key);
      this.sortDir.set('asc');
    }
    this.emitPageRequest();
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.page.set(page);
    this.emitPageRequest();
  }

  onRowClick(row: T): void {
    if (this.clickableRows()) this.rowClick.emit(row);
  }

  private emitPageRequest(): void {
    this.pageChange.emit({
      page: this.page(),
      pageSize: this.pageSize(),
      search: this.search() || undefined,
      sortField: this.sortField() ?? undefined,
      sortDir: this.sortDir(),
    });
  }
}
