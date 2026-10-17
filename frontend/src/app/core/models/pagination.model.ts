export interface PageRequest {
  page: number;
  pageSize: number;
  search?: string;
  sortField?: string;
  sortDir?: 'asc' | 'desc';
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
