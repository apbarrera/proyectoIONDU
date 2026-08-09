import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PageHeader } from './page-header';

describe('PageHeader', () => {
  let component: PageHeader;
  let fixture: ComponentFixture<PageHeader>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PageHeader],
    }).compileComponents();

    fixture = TestBed.createComponent(PageHeader);
    fixture.componentRef.setInput('title', 'Título');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
