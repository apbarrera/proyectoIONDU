import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { AiHistory } from './ai-history';

describe('AiHistory', () => {
  let component: AiHistory;
  let fixture: ComponentFixture<AiHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiHistory],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AiHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
