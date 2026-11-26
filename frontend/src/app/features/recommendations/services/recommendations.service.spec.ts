import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { RecommendationsService } from './recommendations.service';

describe('RecommendationsService (IA)', () => {
  let service: RecommendationsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(RecommendationsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('pide el análisis con IA solo a demanda y no repite mientras espera', () => {
    service.generateWithAi();
    service.generateWithAi(); // ignorado: ya hay uno en curso
    expect(service.aiLoading()).toBe(true);

    http.expectOne({ method: 'POST', url: '/api/recommendations/ai' }).flush({
      analysis: 'Vendiste más que el mes anterior.',
      recommendations: [
        {
          title: 'Repón azúcar',
          description: 'Quedan 2 kg.',
          category: 'Inventario',
          priority: 'alta',
          dataUsed: ['Productos con stock bajo'],
        },
      ],
      generatedAt: '2026-11-26T09:00:00-05:00',
      model: 'qwen2.5:7b',
    });

    expect(service.aiLoading()).toBe(false);
    expect(service.aiAnalysis()?.recommendations[0].title).toBe('Repón azúcar');
  });

  it('si falla (p. ej., límite de tokens) deja de cargar', () => {
    service.generateWithAi();
    http
      .expectOne('/api/recommendations/ai')
      .flush({ error: { code: 'AI_TOKEN_LIMIT_REACHED' } }, { status: 429, statusText: 'Too Many Requests' });
    expect(service.aiLoading()).toBe(false);
    expect(service.aiAnalysis()).toBeNull();
  });
});
