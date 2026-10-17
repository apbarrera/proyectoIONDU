import { provideRouter } from '@angular/router';

/** Global providers available to every spec's TestBed — mainly routing, since most
 * pages/components use RouterLink and would otherwise fail with NG0201. */
export default [provideRouter([])];
