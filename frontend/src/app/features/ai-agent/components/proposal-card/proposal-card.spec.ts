import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProposalCard } from './proposal-card';
import { AiInteraction } from '../../models/ai-message.model';

const MOCK_INTERACTION: AiInteraction = {
  id: 'ai-int-test',
  userId: 'user-test',
  userName: 'Usuario de prueba',
  timestamp: new Date(0).toISOString(),
  inputType: 'texto',
  instruction: 'Compré 5 frascos por $12,50.',
  interpretedData: 'Gasto: Empaques — $12.50',
  proposal: null,
  result: 'pendiente',
};

describe('ProposalCard', () => {
  let component: ProposalCard;
  let fixture: ComponentFixture<ProposalCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProposalCard],
    }).compileComponents();

    fixture = TestBed.createComponent(ProposalCard);
    fixture.componentRef.setInput('interaction', MOCK_INTERACTION);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
