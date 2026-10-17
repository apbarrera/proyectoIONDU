import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Adjustments } from './adjustments';

describe('Adjustments', () => {
  let component: Adjustments;
  let fixture: ComponentFixture<Adjustments>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Adjustments],
    }).compileComponents();

    fixture = TestBed.createComponent(Adjustments);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
