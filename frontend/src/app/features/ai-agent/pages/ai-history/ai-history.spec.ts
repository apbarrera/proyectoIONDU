import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AiHistory } from './ai-history';

describe('AiHistory', () => {
  let component: AiHistory;
  let fixture: ComponentFixture<AiHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiHistory],
    }).compileComponents();

    fixture = TestBed.createComponent(AiHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
