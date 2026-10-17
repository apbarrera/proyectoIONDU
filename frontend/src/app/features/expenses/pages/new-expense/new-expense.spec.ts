import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewExpense } from './new-expense';

describe('NewExpense', () => {
  let component: NewExpense;
  let fixture: ComponentFixture<NewExpense>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewExpense],
    }).compileComponents();

    fixture = TestBed.createComponent(NewExpense);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
