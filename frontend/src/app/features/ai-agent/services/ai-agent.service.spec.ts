import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AiAgentService } from './ai-agent.service';

const PROPOSAL = {
  type: 'expense',
  summary: 'Gasto de $25.00 en «Empaque».',
  expense: {
    total: 25,
    ivaAmount: 0,
    categoryId: 4,
    categoryName: 'Empaque',
    description: 'Empaques',
    supplierName: null,
    paymentMethod: 'efectivo',
    date: null,
  },
};

describe('AiAgentService', () => {
  let service: AiAgentService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(AiAgentService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('envía el texto y enlaza la respuesta con su propuesta', () => {
    service.send('Gasté $25 en empaques').subscribe();
    const request = http.expectOne({ method: 'POST', url: '/api/ai/messages' });
    expect(request.request.body).toEqual({ text: 'Gasté $25 en empaques' });
    request.flush({ actionId: 12, reply: 'Te propongo registrar…', proposal: PROPOSAL });

    const [user, assistant] = service.messages();
    expect(user.content).toBe('Gasté $25 en empaques');
    expect(assistant.interactionId).toBe('12');
    expect(service.interactions()[0].proposal?.expense?.amount).toBe(25);
  });

  it('sin propuesta solo muestra la respuesta', () => {
    service.send('Registra una venta').subscribe();
    http.expectOne('/api/ai/messages').flush({ actionId: null, reply: 'Solo puedo registrar gastos.', proposal: null });

    expect(service.messages()[1].content).toBe('Solo puedo registrar gastos.');
    expect(service.messages()[1].interactionId).toBeUndefined();
    expect(service.interactions()).toEqual([]);
  });

  it('si el agente no está disponible muestra el mensaje del servidor', () => {
    service.send('Gasté $25').subscribe();
    http.expectOne('/api/ai/messages').flush(
      { error: { code: 'AI_NOT_CONFIGURED', message: 'El agente de IA no está configurado.', details: [] } },
      { status: 503, statusText: 'Service Unavailable' },
    );
    expect(service.messages()[1].content).toBe('El agente de IA no está configurado.');
  });

  it('un mensaje de voz se envía como audio y muestra lo que se entendió', () => {
    const audio = new Blob([new Uint8Array([0x1a, 0x45, 0xdf, 0xa3])], { type: 'audio/webm;codecs=opus' });
    service.sendAudio(audio).subscribe();
    expect(service.messages()[0].content).toBe('🎙️ Mensaje de voz');

    const request = http.expectOne({ method: 'POST', url: '/api/ai/audio' });
    expect(((request.request.body as FormData).get('audio') as File).name).toBe('mensaje.webm');
    request.flush({ actionId: 40, reply: 'Te propongo registrar…', proposal: PROPOSAL, transcript: 'Gasté 25 en fundas' });

    const [user, assistant] = service.messages();
    expect(user.content).toBe('🎙️ «Gasté 25 en fundas»');
    expect(assistant.interactionId).toBe('40');
    expect(service.interactions()[0]).toMatchObject({ inputType: 'voz', instruction: '[Voz] Gasté 25 en fundas' });
  });

  it('el audio de Safari se envía como m4a', () => {
    service.sendAudio(new Blob([new Uint8Array([0])], { type: 'audio/mp4' })).subscribe();
    const request = http.expectOne('/api/ai/audio');
    expect(((request.request.body as FormData).get('audio') as File).name).toBe('mensaje.m4a');
    request.flush({ actionId: null, reply: 'No logré entender el audio.', proposal: null, transcript: '' });
    expect(service.messages()[0].content).toBe('🎙️ Mensaje de voz');
  });

  it('una foto se envía como formulario con su indicación', () => {
    const file = new File([new Uint8Array([0xff, 0xd8, 0xff])], 'ticket.jpg', { type: 'image/jpeg' });
    service.sendImage(file, '  Compra de fundas ').subscribe();

    const request = http.expectOne({ method: 'POST', url: '/api/ai/images' });
    const body = request.request.body as FormData;
    expect((body.get('image') as File).name).toBe('ticket.jpg');
    expect(body.get('text')).toBe('Compra de fundas');
    request.flush({ actionId: 31, reply: 'Te propongo registrar…', proposal: PROPOSAL });

    const [user, assistant] = service.messages();
    expect(user.attachments?.[0]).toMatchObject({ type: 'image', name: 'ticket.jpg' });
    expect(assistant.interactionId).toBe('31');
    expect(service.interactions()[0]).toMatchObject({ inputType: 'imagen', instruction: '[Imagen] Compra de fundas' });
  });

  it('una foto sin indicación no envía el campo de texto', () => {
    const file = new File([new Uint8Array([0xff])], 'guia.png', { type: 'image/png' });
    service.sendImage(file).subscribe();

    const request = http.expectOne('/api/ai/images');
    expect((request.request.body as FormData).has('text')).toBe(false);
    request.flush({ actionId: null, reply: 'La foto está borrosa.', proposal: null });
    expect(service.messages()[0].content).toBe('guia.png');
  });

  it('confirmar actualiza el resultado con el gasto creado', () => {
    service.send('Gasté $25 en empaques').subscribe();
    http.expectOne('/api/ai/messages').flush({ actionId: 12, reply: '…', proposal: PROPOSAL });

    service.confirmProposal('12', { amount: 30 });
    const request = http.expectOne('/api/ai/actions/12/confirm');
    expect(request.request.body).toEqual({ total: 30 });
    request.flush({ actionId: 12, status: 'corregido', expenseId: 9 });

    expect(service.interactions()[0]).toMatchObject({ result: 'corregido', expenseId: 9 });
  });

  it('carga el historial desde el backend', () => {
    service.loadHistory().subscribe();
    http.expectOne((r) => r.url === '/api/ai/actions').flush({
      items: [
        {
          id: 3,
          timestamp: '2026-11-26T10:00:00-05:00',
          userName: 'Ana',
          instruction: 'Compré café',
          reply: '¿Cuánto pagaste?',
          proposal: null,
          status: 'sin_propuesta',
          expenseId: null,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 100,
    });

    expect(service.interactions()[0]).toMatchObject({
      id: '3',
      result: 'sin_propuesta',
      interpretedData: '¿Cuánto pagaste?',
    });
  });

  it('una propuesta de inventario se confirma con la cantidad corregida', () => {
    service.send('Llegaron 20 croissants').subscribe();
    http.expectOne('/api/ai/messages').flush({
      actionId: 22,
      reply: 'Te propongo registrar: Entrada de 20…',
      proposal: {
        type: 'inventory',
        summary: 'Entrada de 20 UNIDAD de Croissant (stock: 160 → 180).',
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
    expect(service.interactions()[0].proposal?.inventory?.resultingStock).toBe(180);

    service.confirmProposal('22', { quantity: 18 });
    const request = http.expectOne('/api/ai/actions/22/confirm');
    expect(request.request.body).toEqual({ quantity: 18 });
    request.flush({ actionId: 22, status: 'corregido', expenseId: null, movementId: 253 });

    expect(service.interactions()[0]).toMatchObject({ result: 'corregido', movementId: 253 });
  });
});
