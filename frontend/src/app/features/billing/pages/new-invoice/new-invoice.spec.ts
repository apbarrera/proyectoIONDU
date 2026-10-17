import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewInvoice } from './new-invoice';

describe('NewInvoice', () => {
  let component: NewInvoice;
  let fixture: ComponentFixture<NewInvoice>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewInvoice],
    }).compileComponents();

    fixture = TestBed.createComponent(NewInvoice);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
