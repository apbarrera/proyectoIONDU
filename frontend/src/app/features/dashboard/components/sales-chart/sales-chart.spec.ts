import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SalesChart } from './sales-chart';

describe('SalesChart', () => {
  let component: SalesChart;
  let fixture: ComponentFixture<SalesChart>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SalesChart],
    }).compileComponents();

    fixture = TestBed.createComponent(SalesChart);
    fixture.componentRef.setInput('series', []);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
