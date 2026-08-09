import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiAgentService } from '../../services/ai-agent.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { ProposalCard } from '../../components/proposal-card/proposal-card';

@Component({
  selector: 'app-ai-chat',
  imports: [FormsModule, PageHeader, Button, ProposalCard],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat {
  aiAgent = inject(AiAgentService);

  draft = signal('');
  sending = signal(false);
  recording = signal(false);
  messageInteractions = signal<Record<string, string>>({});

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

  uploadImage(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);

    this.sending.set(true);
    this.aiAgent
      .send('Analicé la imagen adjunta y detecté una posible factura de proveedor.', 'imagen', [
        { type: 'image', url, name: file.name },
      ])
      .subscribe((msg) => {
        const latestInteraction = this.aiAgent.interactions()[0];
        this.messageInteractions.update((m) => ({ ...m, [msg.id]: latestInteraction.id }));
        this.sending.set(false);
      });
  }

  toggleRecording(): void {
    if (this.recording()) return;
    this.recording.set(true);
    setTimeout(() => {
      this.recording.set(false);
      this.draft.set('Compré 5 frascos de vidrio para empaque por $12,50.');
    }, 1800);
  }
}
