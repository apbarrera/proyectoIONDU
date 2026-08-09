import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Recipes } from './recipes';

describe('Recipes', () => {
  let component: Recipes;
  let fixture: ComponentFixture<Recipes>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Recipes],
    }).compileComponents();

    fixture = TestBed.createComponent(Recipes);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
