import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ProposalCard } from './proposal-card';
import { AiInteraction } from '../../models/ai-message.model';

const INTERACTION: AiInteraction = {
  id: '12',
  userId: 'user-test',
  userName: 'Usuario de prueba',
  timestamp: new Date(0).toISOString(),
  inputType: 'texto',
  instruction: 'Gasté $25 en empaques',
  interpretedData: 'Gasto de $25.00 en «Empaque».',
  proposal: {
    id: '12',
    type: 'expense',
    summary: 'Gasto de $25.00 en «Empaque».',
    expense: {
      amount: 25,
      ivaAmount: 0,
      categoryId: 4,
      category: 'Empaque',
      description: 'Empaques',
      providerName: null,
      paymentMethod: 'efectivo',
      date: null,
    },
  },
  result: 'pendiente',
};

describe('ProposalCard', () => {
  let component: ProposalCard;
  let fixture: ComponentFixture<ProposalCard>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProposalCard],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ProposalCard);
    fixture.componentRef.setInput('interaction', INTERACTION);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    await fixture.whenStable();
  });

  afterEach(() => http.verify());

  it('confirmar sin corregir envía un cuerpo vacío', () => {
    component.confirm();
    const request = http.expectOne('/api/ai/actions/12/confirm');
    expect(request.request.body).toEqual({});
    request.flush({ actionId: 12, status: 'confirmado', expenseId: 7 });
  });

  it('corregir envía solo lo que cambió', () => {
    component.startEdit();
    http.expectOne('/api/expense-categories').flush([{ id: 4, name: 'Empaque', description: null, predefined: true }]);
    component.editedAmount.set(30);

    component.confirm();

    const request = http.expectOne('/api/ai/actions/12/confirm');
    expect(request.request.body).toEqual({ total: 30 });
    request.flush({ actionId: 12, status: 'corregido', expenseId: 7 });
  });

  it('cancelar avisa al backend', () => {
    component.cancel();
    http.expectOne({ method: 'POST', url: '/api/ai/actions/12/cancel' }).flush(null);
  });

  it('en inventario corrige la cantidad', () => {
    fixture.componentRef.setInput('interaction', {
      ...INTERACTION,
      id: '22',
      proposal: {
        id: '22',
        type: 'inventory',
        summary: 'Entrada de 20 UNIDAD de Croissant.',
        inventory: {
          productId: 3,
          productName: 'Croissant',
          type: 'entrada',
          quantity: 20,
          unit: 'UNIDAD',
          currentStock: 160,
          resultingStock: 180,
          reason: 'Llegó pedido',
        },
      },
    });
    component.startEdit();
    component.editedQuantity.set(18);

    component.confirm();

    const request = http.expectOne('/api/ai/actions/22/confirm');
    expect(request.request.body).toEqual({ quantity: 18 });
    request.flush({ actionId: 22, status: 'corregido', expenseId: null, movementId: 1 });
  });
});
