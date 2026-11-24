import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { NewExpense } from './new-expense';

describe('NewExpense', () => {
  let component: NewExpense;
  let fixture: ComponentFixture<NewExpense>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewExpense],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(NewExpense);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
