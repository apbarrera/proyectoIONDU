import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Modal } from './modal';

describe('Modal', () => {
  let component: Modal;
  let fixture: ComponentFixture<Modal>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Modal],
    }).compileComponents();

    fixture = TestBed.createComponent(Modal);
    fixture.componentRef.setInput('open', false);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('cierre por el fondo', () => {
    let closedCount: number;
    let backdrop: HTMLElement;
    let dialog: HTMLElement;

    beforeEach(async () => {
      closedCount = 0;
      component.closed.subscribe(() => closedCount++);
      fixture.componentRef.setInput('open', true);
      await fixture.whenStable();
      backdrop = fixture.nativeElement.querySelector('.modal-backdrop');
      dialog = fixture.nativeElement.querySelector('.modal');
    });

    const press = (target: HTMLElement) => target.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true }));

    it('se cierra con un clic completo sobre el fondo', () => {
      press(backdrop);
      backdrop.click();
      expect(closedCount).toBe(1);
    });

    it('no se cierra si el clic empieza dentro del diálogo y termina en el fondo', () => {
      press(dialog);
      backdrop.click();
      expect(closedCount).toBe(0);
    });

    it('no se cierra al hacer clic dentro del diálogo', () => {
      press(dialog);
      dialog.click();
      expect(closedCount).toBe(0);
    });
  });
});
