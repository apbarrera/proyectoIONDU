import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PeriodSelector } from './period-selector';

describe('PeriodSelector', () => {
  let component: PeriodSelector;
  let fixture: ComponentFixture<PeriodSelector>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodSelector],
    }).compileComponents();

    fixture = TestBed.createComponent(PeriodSelector);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
