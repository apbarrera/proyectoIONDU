import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { AiConfig } from '../models/ai-config.model';
import { simulateRequest } from '../../../core/services/mock-http.util';

const DEFAULT_CONFIG: AiConfig = {
  instructions:
    'Eres el asistente de IONDU. Ayuda a registrar gastos y movimientos de inventario a partir de mensajes de texto, imágenes o voz. Sé breve y claro.',
  allowedActions: ['Proponer registro de gastos', 'Proponer ajustes de inventario', 'Responder preguntas sobre el negocio'],
  forbiddenActions: ['Modificar datos sin confirmación humana', 'Eliminar registros', 'Acceder a información de otras empresas'],
  askForMoreInfoWhenUncertain: true,
  monthlyTokenLimit: 100000,
};

/** Cosmetic-only configuration — does not connect to any real AI provider. */
@Injectable({ providedIn: 'root' })
export class AiConfigService {
  #config = signal<AiConfig>(DEFAULT_CONFIG);
  readonly config = this.#config.asReadonly();

  updateConfig(changes: Partial<AiConfig>): Observable<AiConfig> {
    this.#config.update((current) => ({ ...current, ...changes }));
    return simulateRequest(this.#config());
  }
}
