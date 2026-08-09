import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RecommendationsPage } from './recommendations-page';

describe('RecommendationsPage', () => {
  let component: RecommendationsPage;
  let fixture: ComponentFixture<RecommendationsPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RecommendationsPage],
    }).compileComponents();

    fixture = TestBed.createComponent(RecommendationsPage);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
