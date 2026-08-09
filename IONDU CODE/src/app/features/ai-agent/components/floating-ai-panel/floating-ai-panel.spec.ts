import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FloatingAiPanel } from './floating-ai-panel';

describe('FloatingAiPanel', () => {
  let component: FloatingAiPanel;
  let fixture: ComponentFixture<FloatingAiPanel>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FloatingAiPanel],
    }).compileComponents();

    fixture = TestBed.createComponent(FloatingAiPanel);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
