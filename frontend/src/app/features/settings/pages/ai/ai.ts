import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiConfigService } from '../../../ai-agent/services/ai-config.service';
import { TokenUsageService } from '../../../ai-agent/services/token-usage.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';

@Component({
  selector: 'app-ai',
  imports: [FormsModule, PageHeader, Button, Card],
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

  save(): void {
    this.aiConfig
      .updateConfig({ instructions: this.instructions(), askForMoreInfoWhenUncertain: this.askForMoreInfo() })
      .subscribe(() => this.toast.success('Configuración del agente actualizada.'));
  }
}
