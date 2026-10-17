import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NavItem } from './nav-items.const';
import { SIDEBAR_COLLAPSED, SIDEBAR_DEFAULT, SIDEBAR_MAX, SIDEBAR_MIN, Sidebar } from './sidebar';

const key = (name: string) => new KeyboardEvent('keydown', { key: name });

describe('Sidebar', () => {
  let component: Sidebar;
  let fixture: ComponentFixture<Sidebar>;

  beforeEach(async () => {
    localStorage.removeItem('iondu-sidebar');
    await TestBed.configureTestingModule({
      imports: [Sidebar],
    }).compileComponents();

    fixture = TestBed.createComponent(Sidebar);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('arranca expandido con el ancho por defecto', () => {
    expect(component.collapsed()).toBe(false);
    expect(component.hostWidth()).toBe(SIDEBAR_DEFAULT);
  });

  it('al contraerse ocupa solo el ancho de la columna de íconos', () => {
    component.toggleCollapsed();
    expect(component.collapsed()).toBe(true);
    expect(component.hostWidth()).toBe(SIDEBAR_COLLAPSED);
  });

  it('el teclado ajusta el ancho sin salirse de los límites', () => {
    component.onResizeKey(key('Home'));
    expect(component.width()).toBe(SIDEBAR_MIN);
    component.onResizeKey(key('ArrowLeft'));
    expect(component.width()).toBe(SIDEBAR_MIN);

    component.onResizeKey(key('End'));
    expect(component.width()).toBe(SIDEBAR_MAX);
    component.onResizeKey(key('ArrowRight'));
    expect(component.width()).toBe(SIDEBAR_MAX);

    component.onResizeKey(key('Enter'));
    expect(component.width()).toBe(SIDEBAR_DEFAULT);
  });

  it('recuerda el estado entre sesiones', async () => {
    component.toggleCollapsed();
    component.onResizeKey(key('End'));
    fixture.detectChanges();
    await fixture.whenStable();

    const saved = JSON.parse(localStorage.getItem('iondu-sidebar') ?? '{}');
    expect(saved).toEqual({ collapsed: true, width: SIDEBAR_MAX, open: [] });
  });

  it('permite dejar varios grupos abiertos a la vez y cerrarlos por separado', () => {
    const facturacion = { link: '/billing' } as NavItem;
    const gastos = { link: '/expenses' } as NavItem;

    component.toggleGroup(facturacion);
    component.toggleGroup(gastos);
    expect(component.isOpen(facturacion)).toBe(true);
    expect(component.isOpen(gastos)).toBe(true);

    component.toggleGroup(facturacion);
    expect(component.isOpen(facturacion)).toBe(false);
    expect(component.isOpen(gastos)).toBe(true);
  });
});
