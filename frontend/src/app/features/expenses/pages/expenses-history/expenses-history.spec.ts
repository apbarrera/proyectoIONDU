import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { ExpensesHistory } from './expenses-history';

describe('ExpensesHistory', () => {
  let component: ExpensesHistory;
  let fixture: ComponentFixture<ExpensesHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpensesHistory],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ExpensesHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
