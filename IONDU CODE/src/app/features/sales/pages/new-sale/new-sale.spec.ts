import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewSale } from './new-sale';

describe('NewSale', () => {
  let component: NewSale;
  let fixture: ComponentFixture<NewSale>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewSale],
    }).compileComponents();

    fixture = TestBed.createComponent(NewSale);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
