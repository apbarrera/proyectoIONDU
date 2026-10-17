import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SalesHistory } from './sales-history';

describe('SalesHistory', () => {
  let component: SalesHistory;
  let fixture: ComponentFixture<SalesHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SalesHistory],
    }).compileComponents();

    fixture = TestBed.createComponent(SalesHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
