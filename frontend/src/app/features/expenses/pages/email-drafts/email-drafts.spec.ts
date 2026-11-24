import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { EmailDrafts } from './email-drafts';

describe('EmailDrafts', () => {
  let component: EmailDrafts;
  let fixture: ComponentFixture<EmailDrafts>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailDrafts],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(EmailDrafts);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
