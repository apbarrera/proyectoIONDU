import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiConfigService } from '../../../ai-agent/services/ai-config.service';
import { TokenUsageService, monthLabel } from '../../../ai-agent/services/token-usage.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-ai',
  imports: [FormsModule, PageHeader, Button, Card, Icon],
  templateUrl: './ai.html',
  styleUrl: './ai.scss',
})
export class Ai {
  aiConfig = inject(AiConfigService);
  tokenUsage = inject(TokenUsageService);
  auth = inject(AuthService);
  private toast = inject(ToastService);

  instructions = signal(this.aiConfig.config().instructions);
  askForMoreInfo = signal(this.aiConfig.config().askForMoreInfoWhenUncertain);

  readonly monthLabel = monthLabel;
  usage = this.tokenUsage.usage;
  usageError = signal(false);
  /** Límite que escribe el Administrador; vacío = sin límite. */
  limitDraft = signal<number | null>(null);
  savingLimit = signal(false);
  limitInvalid = computed(() => {
    const value = this.limitDraft();
    return value != null && (!Number.isInteger(value) || value < 0);
  });
  /** Barra del historial: cada mes relativo al mayor consumo. */
  maxMonthly = computed(() => Math.max(1, ...(this.usage()?.history ?? []).map((m) => m.used)));

  constructor() {
    if (!this.auth.isAdmin()) return;
    this.tokenUsage.load().subscribe({
      next: (usage) => this.limitDraft.set(usage.monthlyLimit),
      error: () => this.usageError.set(true),
    });
  }

  saveLimit(): void {
    if (this.limitInvalid() || this.savingLimit()) return;
    this.savingLimit.set(true);
    this.tokenUsage.setLimit(this.limitDraft()).subscribe({
      next: (usage) => {
        this.savingLimit.set(false);
        this.limitDraft.set(usage.monthlyLimit);
        this.toast.success(
          usage.monthlyLimit == null ? 'El agente de IA ya no tiene límite mensual.' : 'Límite mensual actualizado.',
        );
      },
      error: () => this.savingLimit.set(false),
    });
  }

  onLimitInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.limitDraft.set(value === '' ? null : Number(value));
  }

  save(): void {
    this.aiConfig
      .updateConfig({ instructions: this.instructions(), askForMoreInfoWhenUncertain: this.askForMoreInfo() })
      .subscribe(() => this.toast.success('Configuración del agente actualizada.'));
  }
}
