import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { AiChat } from './ai-chat';

describe('AiChat', () => {
  let component: AiChat;
  let fixture: ComponentFixture<AiChat>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AiChat],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AiChat);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
