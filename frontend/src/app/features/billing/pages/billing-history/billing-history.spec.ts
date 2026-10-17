import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BillingHistory } from './billing-history';

describe('BillingHistory', () => {
  let component: BillingHistory;
  let fixture: ComponentFixture<BillingHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BillingHistory],
    }).compileComponents();

    fixture = TestBed.createComponent(BillingHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
