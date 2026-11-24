import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { Ai } from './ai';

describe('Ai', () => {
  let component: Ai;
  let fixture: ComponentFixture<Ai>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Ai],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(Ai);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
