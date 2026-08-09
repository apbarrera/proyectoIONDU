import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StatCard } from './stat-card';

describe('StatCard', () => {
  let component: StatCard;
  let fixture: ComponentFixture<StatCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatCard],
    }).compileComponents();

    fixture = TestBed.createComponent(StatCard);
    fixture.componentRef.setInput('label', 'Ingresos');
    fixture.componentRef.setInput('value', '$100.00');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
