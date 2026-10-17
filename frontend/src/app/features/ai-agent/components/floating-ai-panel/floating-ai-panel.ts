import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AiAgentService } from '../../services/ai-agent.service';
import { ProposalCard } from '../proposal-card/proposal-card';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-floating-ai-panel',
  imports: [FormsModule, RouterLink, ProposalCard, Icon],
  templateUrl: './floating-ai-panel.html',
  styleUrl: './floating-ai-panel.scss',
})
export class FloatingAiPanel {
  aiAgent = inject(AiAgentService);

  open = signal(false);
  draft = signal('');
  sending = signal(false);
  messageInteractions = signal<Record<string, string>>({});

  toggle(): void {
    this.open.update((v) => !v);
  }

  interactionFor(messageId: string) {
    const interactionId = this.messageInteractions()[messageId];
    return this.aiAgent.interactions().find((i) => i.id === interactionId) ?? null;
  }

  send(): void {
    const text = this.draft().trim();
    if (!text || this.sending()) return;

    this.sending.set(true);
    this.draft.set('');
    this.aiAgent.send(text).subscribe((msg) => {
      const latestInteraction = this.aiAgent.interactions()[0];
      this.messageInteractions.update((m) => ({ ...m, [msg.id]: latestInteraction.id }));
      this.sending.set(false);
    });
  }
}
